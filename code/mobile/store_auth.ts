import type { AxiosError } from 'axios';
import { router } from 'expo-router';
import {
  isAuthApiError,
  isAuthSessionMissingError,
  type Session,
} from '@supabase/supabase-js';
import { create } from 'zustand';

import { TERMS_VERSION } from '@/constants/legal';
import { getSupabase, LargeSecureStoreAdapter } from '@/utils/supabase';
import { lastSignInMethod, track } from '@/utils/events';

const SESSION_KEY = 'zelbi_session';
// Last-known /auth/me, so a cold start with no network can still route from a
// real profile instead of a null user.
const USER_KEY = 'zelbi_user';

// Revalidation refreshes ahead of time when the access token has this little
// life left, rather than spending a request on a certain 401.
const EXPIRY_MARGIN_S = 90;
const REVALIDATE_RETRY_MS = [3_000, 10_000, 30_000];
const ME_TIMEOUT_MS = 8_000;
const PUSH_CLEAR_CAP_MS = 3_000;

export type AuthSessionSlice = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
};

/** Mirrors GET /auth/me (backend/app/routers/auth.py — MeResponse). */
export type MeUser = {
  id: string;
  email: string;
  email_verified?: boolean;
  email_previously_deleted?: boolean;
  phone: string | null;
  display_name: string;
  avatar_url: string | null;
  trust_score: number;
  eco_score: number;
  trust_level: string;
  eco_level?: string | null;
  completed_giveaways: number;
  completed_pickups: number;
  no_show_count: number;
  location_lat: number | null;
  location_lng: number | null;
  neighborhood: string | null;
  is_suspended: boolean;
  has_payment_method?: boolean;
  marketing_email_opted_in?: boolean;
  created_at: string;
  bio: string | null;
  notify_push_enabled?: boolean;
  notify_messages?: boolean;
  notify_your_listings?: boolean;
  notify_saved_items?: boolean;
  notify_nearby_items?: boolean;
  notify_similar_listings?: boolean;
  notify_recommendations?: boolean;
  notify_account_updates?: boolean;
  terms_version_accepted: string | null;
  terms_accepted_at: string | null;
  age_attested_at: string | null;
  age_attestation_method: string | null;
  profile_completed_at: string | null;
  giveaway_credit_needs_device_check?: boolean;
};

export type RefreshResult = 'ok' | 'refused' | 'unreachable';

/**
 * A refusal is only an answer from the auth server that names this session
 * dead: a 400/401/403 AuthApiError, or session_not_found. Everything else —
 * AuthRetryableFetchError (offline, our 8 s abort, 502/503/504), AuthUnknownError
 * (a captive portal or proxy page), a 429 or 5xx AuthApiError, any non-auth
 * throw — is "could not ask", and must never cost the user their session.
 */
export function classifyAuthError(e: unknown): 'refused' | 'unreachable' {
  if (isAuthSessionMissingError(e)) return 'refused';
  if (isAuthApiError(e) && [400, 401, 403].includes(e.status)) return 'refused';
  return 'unreachable';
}

const REFRESH_CAP_MS = 10_000;

// Single-flight: parallel 401s share one refresh, so a refresh token that one
// caller has just rotated is never presented a second time by another.
let refreshInFlight: Promise<RefreshResult> | null = null;

type AuthState = {
  session: AuthSessionSlice | null;
  user: MeUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isSuspendedFromApi: boolean;
  suspensionDetail: string | null;
  isCountryBlockedFromApi: boolean;
  signInWelcome: 'returning' | 'deleted_new' | null;
  signInCeremonyActive: boolean;

  login: (session: Session, user: MeUser) => Promise<void>;
  /** Persist session and set store token so axios can call GET /auth/me after verifyOtp. */
  primeSessionForApi: (session: Session) => Promise<void>;
  logout: () => Promise<void>;
  /**
   * 'refused' means the server explicitly rejected the refresh token — the only
   * outcome that may end the session. 'unreachable' means no answer was had
   * (offline, timeout, 5xx, 429, garbage body); the stored session is kept.
   */
  refreshSession: () => Promise<RefreshResult>;
  /** Local only: reads SecureStore, never the network. Releases the splash. */
  restoreSession: () => Promise<void>;
  /** Background check of the restored session. Never blocks UI; never throws. */
  revalidateSession: () => Promise<void>;
  setUser: (user: MeUser) => void;
  clearSuspensionFlag: () => void;
  setSuspensionFrom403: (detail: string) => void;
  setCountryBlockedFrom403: () => void;
  beginSignInCeremony: () => void;
  /** Records completeSignIn's welcome classification for the ceremony's host screen to read. */
  resolveSignInCeremony: (kind: 'returning' | 'deleted_new' | null) => void;
  endSignInCeremony: () => void;
};

/** The one place "is onboarding done" is decided — every caller must import this. */
export function needsProfileCompletion(u: MeUser | null): boolean {
  return u != null && u.profile_completed_at == null;
}

function sessionToSlice(session: Session): AuthSessionSlice {
  return {
    access_token: session.access_token,
    refresh_token: session.refresh_token!,
    expires_at: session.expires_at!,
  };
}

async function persistSession(slice: AuthSessionSlice | null): Promise<void> {
  if (!slice) {
    await LargeSecureStoreAdapter.removeItem(SESSION_KEY);
    return;
  }
  await LargeSecureStoreAdapter.setItem(SESSION_KEY, JSON.stringify(slice));
  if (__DEV__) {
    const written = JSON.stringify(slice);
    const bytes = new TextEncoder().encode(written).length;
    const readback = await LargeSecureStoreAdapter.getItem(SESSION_KEY);
    if (readback !== written) {
      console.error(
        `[auth][persist] ROUND-TRIP MISMATCH: wrote ${bytes}B, read back ` +
        `${readback ? new TextEncoder().encode(readback).length : 0}B — session persistence is corrupt`
      );
      try {
        let diffIndex = -1;
        const readbackStr = readback ?? '';
        const maxLen = Math.max(written.length, readbackStr.length);
        for (let i = 0; i < maxLen; i++) {
          if (written[i] !== readbackStr[i]) {
            diffIndex = i;
            break;
          }
        }
        let fieldsLine = 'readback did not parse as JSON — skipping field comparison';
        try {
          const writtenParsed = JSON.parse(written);
          const readbackParsed = JSON.parse(readbackStr);
          const fields: (keyof AuthSessionSlice)[] = ['access_token', 'refresh_token', 'expires_at'];
          const equality = fields.map(
            (field) => `${field}=${writtenParsed[field] === readbackParsed[field]}`
          );
          fieldsLine = `field equality: ${equality.join(', ')}`;
        } catch {
          fieldsLine = 'readback did not parse as JSON — skipping field comparison';
        }
        console.error(
          `[auth][persist][probe] diffIndex=${diffIndex}, writtenLength=${written.length}, ` +
          `readbackLength=${readbackStr.length}, ${fieldsLine}`
        );
      } catch {}
    } else if (bytes > 2048) {
      console.error(
        `[auth][persist] OVERSIZE: session slice ${bytes}B exceeds the 2048B SecureStore limit — ` +
        `this store path is not chunked and will truncate`
      );
    }
  }
}

function parseSlice(raw: string | null): AuthSessionSlice | null {
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as Partial<AuthSessionSlice> | null;
    if (
      p &&
      typeof p.access_token === 'string' &&
      typeof p.refresh_token === 'string' &&
      typeof p.expires_at === 'number'
    ) {
      return p as AuthSessionSlice;
    }
  } catch {}
  return null;
}

// User writes are chained so two quick setUser calls can never interleave
// their chunk writes, and skipped when nothing changed so the 60 s heartbeat
// does not rewrite SecureStore on every tick.
let userWriteChain: Promise<void> = Promise.resolve();
let lastUserJson: string | null = null;

function persistUser(user: MeUser | null): Promise<void> {
  const json = user ? JSON.stringify(user) : null;
  if (json !== null && json === lastUserJson) return userWriteChain;
  lastUserJson = json;
  userWriteChain = userWriteChain
    .then(() =>
      json === null
        ? LargeSecureStoreAdapter.removeItem(USER_KEY)
        : LargeSecureStoreAdapter.setItem(USER_KEY, json),
    )
    .catch(() => {});
  return userWriteChain;
}

async function readCachedUser(): Promise<MeUser | null> {
  try {
    const raw = await LargeSecureStoreAdapter.getItem(USER_KEY);
    if (!raw) return null;
    const u = JSON.parse(raw) as MeUser | null;
    if (u && typeof u.id === 'string') {
      lastUserJson = raw;
      return u;
    }
  } catch {}
  return null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isSuspendedFromApi: false,
  suspensionDetail: null,
  isCountryBlockedFromApi: false,
  signInWelcome: null,
  signInCeremonyActive: false,

  setUser: (user) => {
    set({ user });
    void persistUser(user);
  },

  clearSuspensionFlag: () =>
    set({ isSuspendedFromApi: false, suspensionDetail: null, isCountryBlockedFromApi: false }),

  setSuspensionFrom403: (detail) =>
    set({ isSuspendedFromApi: true, suspensionDetail: detail }),

  setCountryBlockedFrom403: () => set({ isCountryBlockedFromApi: true }),

  beginSignInCeremony: () => set({ signInCeremonyActive: true }),

  resolveSignInCeremony: (kind) => set({ signInWelcome: kind }),

  // Clears signInWelcome here, not in a separate action — the flag has
  // exactly one consumer window (between begin and end), so nothing outside
  // that window should ever read a stale classification from a previous
  // ceremony.
  endSignInCeremony: () => set({ signInCeremonyActive: false, signInWelcome: null }),

  login: async (session, user) => {
    const slice = sessionToSlice(session);
    await persistSession(slice);
    set({
      session: slice,
      user,
      isAuthenticated: true,
      isSuspendedFromApi: false,
      suspensionDetail: null,
      isCountryBlockedFromApi: false,
    });
    void persistUser(user);
    // Fire-and-forget: push token registration has no bearing on sign-in
    // completing and nothing downstream reads its result, so it must not sit
    // on the critical path completeSignIn's caller is awaiting (the sign-in
    // welcome's rise starts the moment that path resolves).
    void import('@/utils/pushToken')
      .then(({ registerPushTokenIfPossible }) => registerPushTokenIfPossible())
      .catch(() => {});
  },

  primeSessionForApi: async (session) => {
    const slice = sessionToSlice(session);
    await persistSession(slice);
    set({
      session: slice,
    });
  },

  logout: async () => {
    // ORDER IS THE WHOLE POINT: clearing the push token is an AUTHENTICATED
    // call, so it has to run while the session still exists. It used to run
    // after signOut and the store teardown below, which meant it went out with
    // no credentials, was refused, and had its failure swallowed — leaving the
    // token on the signed-out account, so that account's pushes kept landing on
    // this device. Never move this below signOut.
    // It is capped so an unreachable server cannot hold the sign-out hostage;
    // the request itself already carries the token and keeps going.
    try {
      const { registerPushTokenIfPossible } = await import('@/utils/pushToken');
      await Promise.race([
        registerPushTokenIfPossible(null),
        new Promise<void>((resolve) => setTimeout(resolve, PUSH_CLEAR_CAP_MS)),
      ]);
    } catch {}
    cancelRevalidationRetry();
    // Nothing below the push clear may stop the local teardown: signOut is
    // bounded by the auth fetch timeout, and its errors are not our business.
    // When the server call fails, auth-js returns early and keeps its own
    // stored session — and its ticker would keep refreshing it — so drop that
    // copy locally too.
    try {
      const { error } = await getSupabase().auth.signOut();
      if (error) await getSupabase().auth.signOut({ scope: 'local' });
    } catch {}
    try {
      await Promise.all([persistSession(null), persistUser(null)]);
    } catch {}
    set({
      session: null,
      user: null,
      isAuthenticated: false,
      isSuspendedFromApi: false,
      suspensionDetail: null,
      isCountryBlockedFromApi: false,
    });
    router.replace('/');
  },

  refreshSession: () => {
    if (refreshInFlight) return refreshInFlight;

    // zelbi_session is the source of truth: pass its refresh token explicitly
    // rather than letting supabase-js read its own sb-* key, which may be
    // stale or already wiped.
    const refreshToken = get().session?.refresh_token;
    if (!refreshToken) return Promise.resolve<RefreshResult>('refused');

    // The attempt persists its own success, so a refresh that lands after the
    // cap below still saves the rotated token instead of losing it.
    const attempt = (async (): Promise<RefreshResult> => {
      try {
        const supabase = getSupabase();
        const { data, error } = await supabase.auth.refreshSession({
          refresh_token: refreshToken,
        });
        if (error) return classifyAuthError(error);
        if (!data.session) return 'unreachable';
        const slice = sessionToSlice(data.session);
        await persistSession(slice);
        set({ session: slice, isAuthenticated: true });
        return 'ok';
      } catch (e) {
        return classifyAuthError(e);
      }
    })();

    let capTimer: ReturnType<typeof setTimeout> | undefined;
    const cap = new Promise<RefreshResult>((resolve) => {
      capTimer = setTimeout(() => resolve('unreachable'), REFRESH_CAP_MS);
    });

    refreshInFlight = Promise.race([attempt, cap]).finally(() => {
      clearTimeout(capTimer);
      refreshInFlight = null;
    });
    return refreshInFlight;
  },

  // INVARIANT: nothing awaited here may touch the network. This function is
  // what releases the splash, and it used to run setSession and /auth/me
  // first — so a dead connection either hung the splash or, when those calls
  // failed, deleted a perfectly good session. Checking the session with the
  // server is revalidateSession's job, in the background.
  restoreSession: async () => {
    set({ isLoading: true });
    let restored = false;
    try {
      const slice = parseSlice(await LargeSecureStoreAdapter.getItem(SESSION_KEY));
      if (!slice) {
        // Missing or unreadable is not a refusal: leave whatever is stored in
        // place. A later login overwrites it.
        set({ isLoading: false, isAuthenticated: false });
        return;
      }
      const cachedUser = await readCachedUser();
      set({
        // A token rotation that landed while this read was in flight is newer
        // than what was on disk when the read began.
        session: get().session ?? slice,
        user: cachedUser ?? null,
        isAuthenticated: true,
        isLoading: false,
      });
      restored = true;
    } catch {
      set({ isLoading: false, isAuthenticated: false });
    } finally {
      if (get().isLoading) set({ isLoading: false });
    }
    if (restored) void get().revalidateSession();
  },

  revalidateSession: () => startRevalidation(false),
}));

let revalidateInFlight: Promise<void> | null = null;
let revalidateRetryTimer: ReturnType<typeof setTimeout> | null = null;
let revalidateRetryIndex = 0;

function cancelRevalidationRetry(): void {
  if (revalidateRetryTimer != null) {
    clearTimeout(revalidateRetryTimer);
    revalidateRetryTimer = null;
  }
  revalidateRetryIndex = 0;
}

/** 3 s, 10 s, 30 s, then stop — the heartbeat and foreground events take over. */
function scheduleRevalidationRetry(): void {
  if (revalidateRetryTimer != null) return;
  if (revalidateRetryIndex >= REVALIDATE_RETRY_MS.length) {
    revalidateRetryIndex = 0;
    return;
  }
  const delay = REVALIDATE_RETRY_MS[revalidateRetryIndex++];
  revalidateRetryTimer = setTimeout(() => {
    revalidateRetryTimer = null;
    void startRevalidation(true);
  }, delay);
}

function startRevalidation(fromRetry: boolean): Promise<void> {
  // A fresh trigger (launch, foreground) restarts the retry schedule.
  if (!fromRetry) cancelRevalidationRetry();
  if (revalidateInFlight) return revalidateInFlight;
  revalidateInFlight = revalidateOnce()
    .catch(() => {})
    .finally(() => {
      revalidateInFlight = null;
    });
  return revalidateInFlight;
}

async function revalidateOnce(): Promise<void> {
  const store = useAuthStore.getState();
  if (!store.isAuthenticated || !store.session) return;

  if (store.session.expires_at - Date.now() / 1000 <= EXPIRY_MARGIN_S) {
    const result = await store.refreshSession();
    if (result === 'refused') {
      await useAuthStore.getState().logout();
      return;
    }
    if (result === 'unreachable') {
      scheduleRevalidationRetry();
      return;
    }
  }

  try {
    const { api } = await import('@/utils/api');
    const me = await api.get<MeUser>('/auth/me', { timeout: ME_TIMEOUT_MS });
    // The session may have ended while the request was out.
    if (!useAuthStore.getState().isAuthenticated) return;
    revalidateRetryIndex = 0;
    useAuthStore.getState().setUser(me.data);
    void import('@/utils/pushToken')
      .then(({ registerPushTokenIfPossible }) => registerPushTokenIfPossible())
      .catch(() => {});
  } catch (e) {
    // A 401 has already been through the interceptor, which owns every refusal
    // decision; if it signed the user out there is nothing left to retry.
    if (!useAuthStore.getState().isAuthenticated) return;
    const res = (e as AxiosError).response;
    const reason = res?.headers?.['x-zelbi-reason'];
    if (res?.status === 403 && reason === 'account_deleted') {
      await useAuthStore.getState().logout();
      return;
    }
    // Suspension and country refusals are already flagged by the interceptor;
    // asking again changes nothing.
    if (res?.status === 403 && reason) return;
    scheduleRevalidationRetry();
  }
}

// supabase-js rotates the refresh token on its own ticker and after our own
// refreshSession calls. Without this, zelbi_session kept the old refresh
// token, and a relaunch presented a token the server had already consumed.
// Deferred with setTimeout because auth-js warns that awaiting inside this
// callback can deadlock it. SIGNED_OUT is deliberately ignored: supabase-js
// emits it on its own non-retryable errors (a proxy page, a 5xx body), which
// are not refusals — only this store decides when a session ends.
try {
  getSupabase().auth.onAuthStateChange((event, s) => {
    if (event !== 'TOKEN_REFRESHED' || !s) return;
    const slice = sessionToSlice(s);
    setTimeout(() => {
      const state = useAuthStore.getState();
      // After a local logout nothing may write a session back.
      if (!state.isLoading && !state.session) return;
      void persistSession(slice).catch(() => {});
      useAuthStore.setState({ session: slice });
    }, 0);
  });
} catch (e) {
  // Missing Supabase env must not crash the import graph; sign-in reports it.
  console.error('[auth] could not subscribe to auth state changes', e);
}

/**
 * Shared post-sign-in work for every sign-in path (Apple native, OAuth,
 * email/phone OTP): prime the session so authenticated calls can go out,
 * fetch the user, record terms + 18+ attestation if the current version
 * hasn't been accepted yet, then complete login. A failed accept-terms call
 * never blocks sign-in — a user locked out of the app because a consent
 * write failed is worse than a consent recorded one sign-in late.
 */
export async function completeSignIn(session: Session): Promise<MeUser> {
  track('signin_completed', { method: lastSignInMethod() });
  await useAuthStore.getState().primeSessionForApi(session);
  const { api } = await import('@/utils/api');
  const me = await api.get<MeUser>('/auth/me');
  let user = me.data;
  // Only a brand-new account (never accepted anything) is auto-accepted here —
  // it agrees on the welcome screen. A returning account on an older version
  // keeps that version; the terms-updated screen (app/terms-updated.tsx) is
  // what asks it to accept the current one.
  if (user.terms_version_accepted == null) {
    try {
      const accepted = await api.post<MeUser>('/users/me/accept-terms', {
        version: TERMS_VERSION,
        age_attestation_method: 'self_attested',
      });
      user = accepted.data;
    } catch (e) {
      console.error('[auth] accept-terms failed, continuing with /auth/me user', e);
    }
  }
  // The classification is resolved BEFORE login on purpose: login flips
  // isAuthenticated, which fires the auth redirect, and if signInWelcome is
  // not already set by then the redirect effect (still suspended by the
  // ceremony flag) has nothing to read once it resumes.
  const kind = user.profile_completed_at
    ? ('returning' as const)
    : user.email_previously_deleted
      ? ('deleted_new' as const)
      : null;
  useAuthStore.getState().resolveSignInCeremony(kind);

  await useAuthStore.getState().login(session, user);
  // A sign-in with no welcome (brand-new signup) has no host screen driving
  // the ceremony to a close, so end it here; the redirect resumes and routes
  // to onboarding as before. When a welcome IS pending, the host screen ends
  // the ceremony itself once the welcome sequence hands off to the dissolve.
  if (!kind) {
    useAuthStore.getState().endSignInCeremony();
  }
  return user;
}

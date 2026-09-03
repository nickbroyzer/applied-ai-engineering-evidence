import { router } from 'expo-router';
import type { Session } from '@supabase/supabase-js';
import { create } from 'zustand';

import { TERMS_VERSION } from '@/constants/legal';
import { getSupabase, LargeSecureStoreAdapter } from '@/utils/supabase';

const SESSION_KEY = 'zelbi_session';

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
};

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
  refreshSession: () => Promise<boolean>;
  restoreSession: () => Promise<void>;
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

  setUser: (user) => set({ user }),

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
    try {
      const { registerPushTokenIfPossible } = await import('@/utils/pushToken');
      await registerPushTokenIfPossible(null);
    } catch {}
    const supabase = getSupabase();
    await supabase.auth.signOut();
    await persistSession(null);
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

  refreshSession: async () => {
    const supabase = getSupabase();
    const { data, error } = await supabase.auth.refreshSession();
    if (error || !data.session) {
      return false;
    }
    const slice = sessionToSlice(data.session);
    await persistSession(slice);
    set({ session: slice, isAuthenticated: true });
    return true;
  },

  restoreSession: async () => {
    set({ isLoading: true });
    try {
      const raw = await LargeSecureStoreAdapter.getItem(SESSION_KEY);
      if (!raw) {
        set({
          isLoading: false,
          isAuthenticated: false,
          session: null,
          user: null,
        });
        return;
      }
      const parsed = JSON.parse(raw) as AuthSessionSlice;
      const supabase = getSupabase();
      const { data, error } = await supabase.auth.setSession({
        access_token: parsed.access_token,
        refresh_token: parsed.refresh_token,
      });
      if (error || !data.session) {
        await persistSession(null);
        set({
          isLoading: false,
          isAuthenticated: false,
          session: null,
          user: null,
        });
        return;
      }
      const slice = sessionToSlice(data.session);
      await persistSession(slice);
      set({
        session: slice,
        isAuthenticated: true,
      });
      const { api } = await import('@/utils/api');
      const me = await api.get<MeUser>('/auth/me');
      set({
        user: me.data,
        isLoading: false,
      });
      try {
        const { registerPushTokenIfPossible } = await import('@/utils/pushToken');
        await registerPushTokenIfPossible();
      } catch {}
    } catch {
      await persistSession(null);
      set({
        isLoading: false,
        isAuthenticated: false,
        session: null,
        user: null,
      });
    }
  },
}));

/**
 * Shared post-sign-in work for every sign-in path (Apple native, OAuth,
 * email/phone OTP): prime the session so authenticated calls can go out,
 * fetch the user, record terms + 18+ attestation if the current version
 * hasn't been accepted yet, then complete login. A failed accept-terms call
 * never blocks sign-in — a user locked out of the app because a consent
 * write failed is worse than a consent recorded one sign-in late.
 */
export async function completeSignIn(session: Session): Promise<MeUser> {
  await useAuthStore.getState().primeSessionForApi(session);
  const { api } = await import('@/utils/api');
  const me = await api.get<MeUser>('/auth/me');
  let user = me.data;
  if (user.terms_version_accepted !== TERMS_VERSION) {
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

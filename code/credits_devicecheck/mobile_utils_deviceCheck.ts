import { Platform } from 'react-native';

import { generateToken, isSupported } from '@/modules/zelbi-device-check';
import { useAuthStore, type MeUser } from '@/store/auth';
import { api } from '@/utils/api';

// D542 (4): a giveaway credit cannot be spent until the giver's iPhone passes Apple
// DeviceCheck. The app runs the check on sign-in and on each return to the foreground, and
// only when /auth/me says one is needed. The token is single-use and is never logged.

export type DeviceCheckResult =
  | 'unsupported'
  | 'not_needed'
  | 'passed'
  | 'refused'
  | 'unavailable'
  | 'error';

const ME_TIMEOUT_MS = 8_000;
const SERVER_RESULTS: readonly DeviceCheckResult[] = ['not_needed', 'passed', 'refused', 'unavailable'];

// One check at a time: sign-in and a foreground return can land together.
let inFlight: Promise<DeviceCheckResult> | null = null;

async function fetchMeIntoStore(): Promise<MeUser | null> {
  const me = await api.get<MeUser>('/auth/me', { timeout: ME_TIMEOUT_MS });
  // The session may have ended while the request was out.
  if (!useAuthStore.getState().isAuthenticated) return null;
  useAuthStore.getState().setUser(me.data);
  return me.data;
}

async function runCheck(): Promise<DeviceCheckResult> {
  if (Platform.OS !== 'ios' || !isSupported()) return 'unsupported';
  // Signed out: an unauthenticated /auth/me would go through the 401 path for nothing.
  if (!useAuthStore.getState().isAuthenticated) return 'not_needed';

  const me = await fetchMeIntoStore();
  if (me == null || me.giveaway_credit_needs_device_check !== true) return 'not_needed';

  const device_token = await generateToken();
  const res = await api.post<{ result: string }>('/users/me/device-check', { device_token });
  try {
    await fetchMeIntoStore();
  } catch {
    // The server has already answered; the heartbeat picks up the new user.
  }
  const result = res.data.result as DeviceCheckResult;
  return SERVER_RESULTS.includes(result) ? result : 'error';
}

/** Runs the check if /auth/me says one is needed. Memoized per flight; never throws. */
export function ensureDeviceCheck(): Promise<DeviceCheckResult> {
  if (inFlight) return inFlight;
  inFlight = runCheck()
    .catch((): DeviceCheckResult => 'error')
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}

/** Resolves when a check in flight settles, or after ms. Starts nothing; never throws. */
export function waitForDeviceCheck(ms: number): Promise<void> {
  const current = inFlight;
  if (current == null) return Promise.resolve();
  return new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, ms);
    void current.then(() => {
      clearTimeout(timer);
      resolve();
    });
  });
}

/** D543 (6): development walks only. Clears this iPhone's bit and the caller's stamps. */
export async function resetDeviceCheck(): Promise<'reset' | 'error'> {
  try {
    if (Platform.OS !== 'ios' || !isSupported()) return 'error';
    const device_token = await generateToken();
    const res = await api.post<{ result: string }>('/users/me/device-check/reset', { device_token });
    try {
      await fetchMeIntoStore();
    } catch {}
    return res.data.result === 'reset' ? 'reset' : 'error';
  } catch {
    return 'error';
  }
}

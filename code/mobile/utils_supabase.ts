import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';

const CHUNK_LIMIT = 1800; // bytes per SecureStore value, safely under the 2048 soft limit

function chunkByBytes(value: string): string[] {
  const enc = new TextEncoder();
  const chunks: string[] = [];
  let current = '';
  let currentBytes = 0;
  for (const ch of value) {
    const chBytes = enc.encode(ch).length;
    if (currentBytes + chBytes > CHUNK_LIMIT) {
      chunks.push(current);
      current = ch;
      currentBytes = chBytes;
    } else {
      current += ch;
      currentBytes += chBytes;
    }
  }
  if (current.length > 0) chunks.push(current);
  return chunks;
}

export const LargeSecureStoreAdapter = {
  getItem: async (key: string): Promise<string | null> => {
    const countRaw = await SecureStore.getItemAsync(`${key}.__n`);
    if (countRaw == null) {
      // legacy / migration read: a value written by the old single-key adapter
      return SecureStore.getItemAsync(key);
    }
    const n = parseInt(countRaw, 10);
    if (!Number.isFinite(n) || n <= 0) return null;
    let out = '';
    for (let i = 0; i < n; i++) {
      const part = await SecureStore.getItemAsync(`${key}.${i}`);
      if (part == null) return null; // incomplete -> treat as no session
      out += part;
    }
    return out;
  },
  setItem: async (key: string, value: string): Promise<void> => {
    const chunks = chunkByBytes(value);
    const prevRaw = await SecureStore.getItemAsync(`${key}.__n`);
    const prev = prevRaw ? parseInt(prevRaw, 10) : 0;
    for (let i = chunks.length; i < prev; i++) {
      await SecureStore.deleteItemAsync(`${key}.${i}`);
    }
    for (let i = 0; i < chunks.length; i++) {
      await SecureStore.setItemAsync(`${key}.${i}`, chunks[i]);
    }
    await SecureStore.setItemAsync(`${key}.__n`, String(chunks.length));
    await SecureStore.deleteItemAsync(key); // drop the legacy single-key blob
  },
  removeItem: async (key: string): Promise<void> => {
    const countRaw = await SecureStore.getItemAsync(`${key}.__n`);
    const n = countRaw ? parseInt(countRaw, 10) : 0;
    for (let i = 0; i < n; i++) {
      await SecureStore.deleteItemAsync(`${key}.${i}`);
    }
    await SecureStore.deleteItemAsync(`${key}.__n`);
    await SecureStore.deleteItemAsync(key);
  },
};

let client: SupabaseClient | null = null;
let oauthClient: SupabaseClient | null = null;

function readEnv(): { url: string; anon: string } {
  const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
  const anon = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) {
    throw new Error(
      'Missing EXPO_PUBLIC_SUPABASE_URL or EXPO_PUBLIC_SUPABASE_ANON_KEY',
    );
  }
  return { url, anon };
}

/**
 * Primary client. No PKCE: email 6-digit OTP and session refresh both break
 * under the PKCE flow on this runtime, which has no WebCrypto — the code
 * challenge degrades to plain and refreshes are rejected, which sends the
 * 401 interceptor into logout and bounces the user back to the login screen.
 * Session 231 removed flowType for this reason; commit 201ff6a reinstated it
 * as an unremarked one-line change while adding OAuth. Do not add it back
 * here — the browser OAuth path has its own client below.
 */
export function getSupabase(): SupabaseClient {
  if (client) {
    return client;
  }
  const { url, anon } = readEnv();
  client = createClient(url, anon, {
    auth: {
      detectSessionInUrl: false,
      storage: LargeSecureStoreAdapter,
      autoRefreshToken: true,
      persistSession: true,
    },
  });
  return client;
}

/**
 * Browser-redirect OAuth client only (Google, and Apple on non-iOS).
 * exchangeCodeForSession requires the PKCE flow and the code verifier that
 * signInWithOAuth stored, so both calls must run on THIS client. It uses a
 * separate storageKey so its tokens can never overwrite the primary
 * client's session. Never use this for email login or session refresh.
 */
export function getOAuthSupabase(): SupabaseClient {
  if (oauthClient) {
    return oauthClient;
  }
  const { url, anon } = readEnv();
  oauthClient = createClient(url, anon, {
    auth: {
      detectSessionInUrl: false,
      storage: LargeSecureStoreAdapter,
      storageKey: 'zelbi-oauth-auth-token',
      autoRefreshToken: false,
      persistSession: true,
      flowType: 'pkce',
    },
  });
  return oauthClient;
}

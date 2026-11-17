# `code/mobile/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Load the claim the notification names (case study 03)

`mobile/app/handoff/[claimId].tsx`, lines 1272–1296, at `4772472b`. Cited by: 06-case-studies/03.

```tsx
      setFetchError(null);
      loadFailedOnNetworkRef.current = false;
      let retryTimer: ReturnType<typeof setTimeout> | undefined;
      // LOAD THE CLAIM WE WERE GIVEN, not the newest one on this listing.
      // getClaimByListing returns the most recent claim on the listing whatever its
      // status, and cancelling a claim returns the SAME listing row to active — so
      // after cancel, relist and re-claim, an old notification for this listing
      // resolved to a stranger's claim, or 403'd. claimId comes from the route and
      // is the claim the notification actually referred to. The listing lookup stays
      // as the fallback for entry points that carry no claim id.
      // A load that fails on the network (no response at all) is tried again every
      // CLAIM_LOAD_RETRY_MS, up to CLAIM_LOAD_RETRIES times, under the skeleton (D635): on the
      // build 19 walk the picker opened this screen at the door, the load failed once with a
      // network error and the screen sat on its error with no arrival check until a manual retry.
      // The arrival check below runs as soon as the claim and listing are in state.
      const load = (retriesLeft: number) => {
        Promise.all([
          claimId
            ? getClaimById(claimId).catch(() => getClaimByListing(listingId))
            : getClaimByListing(listingId),
          getListing(listingId),
          fetchThread(listingId, { limit: 30, newest: true }).catch(() => null),
        ])
          .then(([c, l, t]) => {
            if (!mounted) return;
```

## Single-flight refresh and logout

`mobile/store/auth.ts`, lines 118–127, at `4772472b`. Cited by: 04-troubleshooting/02-two-cause-auth-reset.md.

```ts
const REFRESH_CAP_MS = 10_000;

// Single-flight: parallel 401s share one refresh, so a refresh token that one
// caller has just rotated is never presented a second time by another.
let refreshInFlight: Promise<RefreshResult> | null = null;

// Single-flight: a 401 that lands while logout is already tearing down (the
// heartbeat, a telemetry flush) shares that teardown instead of running
// signOut and the login-screen transition a second time (Session 484).
let logoutInFlight: Promise<void> | null = null;
```

## Two Supabase clients: no PKCE on the primary

`mobile/utils/supabase.ts`, lines 186–222, at `4772472b`. Cited by: 04-troubleshooting/02-two-cause-auth-reset.md.

```ts
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
    global: { fetch: authFetchWithTimeout },
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
```

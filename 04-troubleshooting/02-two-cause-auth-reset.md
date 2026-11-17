# A login screen that reset itself, from two independent causes

**Commit:** `5d02d80c1dbb976c83fd37e33fccc65c392d5adc` · 2026-07-30
**Message, verbatim:** `fix(mobile): stop badge polls logging the user out, split PKCE onto an OAuth-only Supabase client`
**Decisions:** [`D276`](../03-decisions/ops/D276.md), [`D277`](../03-decisions/ops/D277.md)
**Code:** [`../code/mobile/EXCERPTS.md`](../code/mobile/EXCERPTS.md), [`../code/mobile/EXCERPTS.md`](../code/mobile/EXCERPTS.md)

## Symptom

Users were being returned to the login screen mid-session, intermittently. It
did not reproduce on demand, and it did not correlate cleanly with anything —
not with a screen, not with an action, not with elapsed time.

## Diagnosis

The reason it would not reduce to a single reproduction is that it was **two
unrelated bugs producing one symptom**. That is the thing worth carrying out of
this: an intermittent failure that resists a clean repro is often not one flaky
cause but two deterministic ones interleaving.

**Cause one — PKCE in a runtime without WebCrypto.** The primary auth client was
configured for the PKCE flow. The React Native runtime has no WebCrypto, so the
code verifier could not be handled the way PKCE requires, and the session
degraded. This affected the primary client, which every ordinary request used.

**Cause two — background polls ending the session.** The unread-count and
notification-badge pollers ran on a timer. When one of them received a 401, it
travelled the shared error path, and that path called logout. So a single
transient 401 on a *background* request — a request the user never made and
could not see — signed the user out of the foreground app.

Cause two is what made it look random: the trigger was a timer, not a user
action. Tracing when the polling behaviour had been introduced was done with
`git log -S` over the calling code, searching for when the string appeared
rather than reading the history forward.

## Fix

Two changes, one per cause, filed as two decisions so neither could later be
"simplified" back:

**D276 — the primary Supabase client must never use the PKCE flow.** PKCE was
split onto a separate client used *only* for the OAuth browser handoff, where
the browser supplies what the RN runtime lacks. The primary client no longer
touches it.

**D277 — background and badge polls must never be able to end a session.** The
pollers are gated on a restored session and are cut out of the logout path. A
401 on a background poll can no longer sign anyone out.

The diff touched four files — the app layout that owns the pollers, the shared
request helper carrying the 401 path, the OAuth helper, and the Supabase client
setup.

## Why the rule is phrased as a prohibition

Both decisions are written as "must never," not as "should." A permission is
re-litigated by the next person who finds it inconvenient; a prohibition with a
recorded cause is not. D277 in particular protects a property that is invisible
in normal operation — nobody notices background polls *failing to* log them out.

## Test

The suite covers the auth store and the request helper. The 401-does-not-logout
property is enforced structurally: the poller paths no longer reach logout at
all, so there is no runtime condition to test around. The PKCE half was verified
on device — a runtime-capability failure cannot be reproduced in a test process
that has WebCrypto.

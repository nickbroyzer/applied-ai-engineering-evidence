# Admin API and ops console

The operator side of Zelbi: the routes an admin uses to run claims, disputes,
rule flags, the money path and account actions, and the Sentry watcher that
feeds production errors into the same console.

Code and tests: [`../code/admin_ops/`](../code/admin_ops/). Line numbers are at
Zelbi `8875721`; counts and their commands are in
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md).

## The routes

**28 routes** in the four admin routers (`admin.py`, `admin_actions.py`,
`admin_reads.py`, `admin_writes.py`). Counting every route across the backend
that depends on the admin check gives **43**; the difference is the watcher,
user-event, growth-source and CX-knowledge routes that live in other routers.
The admin check is one dependency, `require_admin` (`routers_admin.py:29-35`),
which reads a boolean column on the user. There is no email allowlist.

| Area | Routes | Where |
|---|---|---|
| Claims | list, detail | `routers_admin_reads.py:199, 230` |
| Disputes | list; respond, resolve, message | `routers_admin_reads.py:552`; `routers_admin.py:144, 174, 308` |
| Rule flags | rule definitions, flag list; confirm, false-positive, escalate | `routers_admin_reads.py:615, 632`; `routers_admin_writes.py:63, 108, 128` |
| Money path | per-claim live Stripe view; resync, sweep one claim; run the post-window sweeper | `routers_admin_reads.py:691`; `routers_admin_writes.py:290, 331`; `routers_admin.py:112` |
| Accounts | suspend, lift, timeout | `routers_admin_actions.py:63, 95, 127` |
| Listings | list, detail; mark as test, deactivate | `routers_admin_reads.py:374, 412`; `routers_admin_writes.py:205, 228` |
| Notes, health, jobs | notes create/list; health; expire listings, send pickup and expiry reminders | `routers_admin_writes.py:164, 184`; `routers_admin_reads.py:755`; `routers_admin.py:93, 102, 132` |

## Emailed notices

Seven of those routes tell the affected user by email: suspend, lift and
timeout (`routers_admin_actions.py:85, 117, 148`), confirming a rule flag
(`routers_admin_writes.py:91`), deactivating a listing (:250), deciding a
dispute (`routers_admin.py:280`) and messaging a dispute's parties (:353).

All of them go through one module, `standing_notices.py`: `record_action`
writes the action row with `notice_sent = False`, and `send_branded` / `notify`
send the branded email and flip the flag only on success (`standing_notices.py:13-107`).
A failed send is logged and leaves the flag false; the admin action itself still
stands. So "was the user told?" is a column, not a guess.

The automatic standing actions — a strike timeout, a dispute suspension or
warning — write the same rows from `strike_service.py`, so the console shows
manual and automatic actions in one history.

## Disputes: refund before the ruling

Resolving a dispute in the picker's favour refunds the captured fee **before
anything is committed** (`routers_admin.py:218-233`,
[`D324`](../03-decisions/money/D324.md)). A failed refund rolls back and returns
502 "Refund failed; dispute not resolved. Retry is safe." — the refund call is
idempotent per claim — so a dispute can never read "resolved for you" while the
money stayed put. The trust event, the email and the possible suspension follow
in that order (:234-300).

Disputes start by email to support, not in the app
([`D533`](../03-decisions/money/D533.md), 2026-09-24: no app screen ever called
the filing route). The unused filing route itself was deleted on 2026-10-03 in
a dead-code pass (commit `b6ced95`), so nothing in the backend now creates a
dispute row. The resolve, respond and message routes are unchanged and remain
the operator's tools for a dispute once one is recorded.

## The Sentry watcher

Production errors reach the console through a Sentry webhook
(`routers_watcher.py:174-209`):

1. **Signature first.** A missing `sentry-hook-signature` header is a 400.
2. **Fail closed when unconfigured.** An empty webhook secret logs and returns
   400 "Webhook not configured" — an unset secret never means "accept
   everything".
3. **HMAC-SHA256 over the raw body**, compared with `hmac.compare_digest`
   (constant time). A mismatch is a 400.
4. Only `issue` and `event_alert` resources are stored; anything else is
   acknowledged and ignored. Rows are upserted so two deliveries of the same
   event cannot race into duplicates.

The console reads events from `GET /admin/watcher/events`, and a
**Server-Sent Events** endpoint, `GET /admin/watcher/stream`
(`routers_watcher.py:348-360`), pushes new rows to an open connection. Because
browser `EventSource` cannot set headers, the stream also accepts the token as
`?access_token=` (:300-311).

## The console itself

A single HTML file with no framework, deployed to Cloudflare Pages. It is
**described, not published**: it embeds the production API host and the auth
project's public identifiers, and seed data with real names. Nothing about the
backend's guarantees depends on it — every rule above is enforced server-side.

## Tests

122 `def test_` functions (124 collected) across `test_admin_*.py` (nine files)
and `test_watcher.py`, all passing in the recorded run.

## Honest limits

- **The "live" stream polls.** The SSE endpoint re-queries the database every
  2 seconds and sends a keepalive every 15 (`routers_watcher.py:38-39, 329-345`).
  It is near-real-time, not push from the webhook.
- **Nothing consumes the stream yet.** The console fetches health once at sign-in;
  neither it nor the mobile app opens the watcher stream or event list. The
  stream's only tests are the 401 cases.
- **No replay protection on the webhook.** The signature is checked; the
  delivery timestamp is not, so a captured valid delivery could be replayed. The
  upsert makes a replay a no-op for an existing event.
- **The stream accepts its token in the query string**, which can end up in
  access logs. Scoped to admin accounts, but noted.
- **No test for the refund-failure 502 path**, and no non-admin 403 test on the
  resolve route specifically (list and message have one —
  `test_admin_disputes.py:244, 372`).
- **Stale comments.** `routers_admin.py:223` and `stripe_service.py:851` still say
  "D-entry pending" for the refund ruling, which is D324.

- **No code path creates a dispute row today** (see above); the dispute routes
  are tested against rows the tests insert.

## What is never claimed

That the console is published, that the event stream is push-based, that
disputes can be filed in the app today, or that admin access is anything more
than one boolean column checked by one dependency.

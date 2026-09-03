# Backend lessons — things learned by breaking them

This file is not documentation. It is a running record of corrections, one
line per failure already paid for, appended when something went wrong in a way
that was not a behavioural rule and not a locked decision. Its own header says
what it is for: *read at session start.*

The reason it exists is that without it the same toolchain failure gets
re-derived every few weeks by whoever is next in the file. The reason it is
worth showing is that most of these are not things anyone would guess.

Selected from `zelbi.ai/backend/lessons.md` (102 lines, 93 dated entries) at commit `3413d028`. Each bullet is **verbatim**; `L<n>` is its line number in the
source file. Nothing was reworded.

- `L9` — 2026-05-09 — Tests authored in a Claude Code worktree do not surface in the main-repo working tree; verify by copying the file across or running pytest from the worktree path, and always check full-suite collection count, not just targeted-suite pass count.
- `L41` — 2026-06-29 — Railway cron service runs the service's Custom Start Command; it must point at a committed runner module (e.g. python -m app.jobs.run_daily_jobs) or the deploy fails — empty command falls back to the web-server CMD and runs no job.
- `L42` — 2026-06-30 — Tests exercising any claim-cancel path must stub Stripe (monkeypatch stripe.PaymentIntent.retrieve / stripe.Refund.create as test_claims.py does) or the cancel path raises "Stripe is not configured" before assertions run.
- `L43` — 2026-06-30 — Tests writing claims.pickup_scheduled_at must bind NAIVE UTC; an aware datetime becomes timestamptz and Postgres localizes it to the session TimeZone on assignment to the naive column, shifting the stored instant and breaking grace-window logic.
- `L48` — 2026-07-09 — Stripe's hold expiry lives at payment_method_details.card.capture_before on the charge, never at the top level of the charge object.
- `L49` — 2026-07-09 — A Stripe hold expiry cannot be read at PaymentIntent creation — no charge exists yet. It is readable only once the amount_capturable_updated webhook fires.
- `L51` — 2026-07-09 — A Stripe webhook handler must set stripe.api_key itself before calling into stripe_service; importing the module does not set it, and the helper's bare except swallows the auth failure into a silent None.
- `L52` — 2026-07-09 — The Stripe webhook dispatcher coerces the event payload to a plain dict, so helpers reading it must use a shape-agnostic field accessor, never getattr.
- `L53` — 2026-07-09 — Column(DateTime) is naive; Pydantic serializes it with no UTC marker and JavaScript's Date parses an unmarked ISO string as local time. Use the UtcDateTime type in backend/app/schemas/datetimes.py on every response-model datetime.
- `L54` — 2026-07-12 — Before building a "new" message/content check, grep for an existing scam_detection/content-scanning engine first and extend it in place; a parallel module duplicates the block path and response shape.
- `L55` — 2026-07-12 — iOS auto-substitutes a curly apostrophe (U+2019) for the straight one in typed contractions; server-side content regexes must accept both ['’], since a Python test with a straight-quote string literal passes while the device string slips through.
- `L56` — 2026-07-14 — Railway config lives only in the dashboard: no scheduler exists in-repo, so any job not wired into a scheduled runner module never runs in production (listing expiry sat unscheduled until Session 344).
- `L57` — 2026-07-15 — Local curl against authed endpoints is impossible: verification is ES256 via Supabase JWKS and the only mint script is deprecated HS256; endpoint verification goes through the pytest auth_client dependency-override fixture in tests/conftest.py.
- `L59` — 2026-07-27 — A scheduled job that queries a bounded time window must run at least as often as that window is wide, or it silently matches nothing and reports success; the T-1h pickup reminder searched a 10-minute band on a daily cron and had effectively never fired.
- `L60` — 2026-07-27 — send_push with digest=True writes an inbox row and returns before both the push attempt and the idempotency-guard write, so digest-lane notifications never reach a phone and have no repeat protection at any cadence.
- `L61` — 2026-07-27 — Stripe resource_missing on a cancel has two causes with opposite consequences — an id that was never real, or a real id under a different API account — so it is only safe to forgive when the id itself cannot match Stripe's pi_ + 24-alphanumeric shape.
- `L62` — 2026-07-27 — Gating a giver endpoint on "pickup_mode is None" made mode a one-way door and locked the giver out of changing their own arrangement. Gate on claim status, not on a field the first successful call sets.
- `L63` — 2026-07-29 — sort without a pinned locale reorders paths containing underscores and parentheses between runs; pin LC_ALL=C in any script that diffs sorted output.
- `L64` — 2026-07-29 — An endpoint returning a plain dict has no response model, so naive datetimes ship without a timezone marker and the client reads them as local time; recent timestamps land in the future and collapse to "just now". Stamp UTC at the boundary or give the endpoint a response model.
- `L65` — 2026-07-29 — A listing created before a uvicorn restart carries the old code's behaviour; two listings posted the same day got different expiry windows for this reason. Always confirm process start time against the last edit before treating a result as evidence.
- `L67` — 2026-07-30 — resolve_notification_target checks the notice tuple before anything else, so a type listed there can never reach a later branch no matter where that branch is inserted; check tuple membership before adding a new kind.
- `L68` — 2026-07-30 — Supabase data API returns HTTP 200 with an empty array when RLS is enabled with no policies; a status-code-only curl cannot distinguish sealed from exposed — always read the response body (row count) when testing table access.
- `L69` — 2026-07-30 — The Sentry Python SDK turns any error-level log record into an issue by default, so a codebase that logs handled failures at error level reports normal operation as alerts; pass LoggingIntegration(event_level=None) to keep log records as breadcrumbs only.
- `L70` — 2026-07-30 — A job runner that catches every exception and logs it gives the Sentry SDK nothing to notice, because nothing propagates; wiring the SDK into such a runner does nothing without an explicit capture_exception call inside each except block.
- `L71` — 2026-07-30 — A short-lived process must flush the Sentry queue before exit or its events are lost; sentry_sdk.flush() belongs in the runner's finally block, and a cron container is exactly this case.
- `L72` — 2026-07-30 — Once SENTRY_DSN is in .env.local, a local pytest run reports its own errors to Sentry; guard init on "pytest" in sys.modules or the test suite burns the event quota and fills the feed.
- `L73` — 2026-07-30 — Sentry's SDK prints nothing about event acceptance unless debug=True; a send that 404s looks identical to a successful one in normal output, so verify a DSN with debug on or by reading the Sentry UI, never by the absence of an error line.
- `L74` — 2026-07-30 — FastAPI caches a dependency per request, so a router-level dependency that itself depends on get_current_user does not cause a second JWT verification or a second DB lookup — verified against 0.104.1.
- `L77` — 2026-08-02 — A grep for "tz_offset/timezone_offset" cannot find a timezone stored as an IANA NAME — users.timezone existed all along; search for the concept's storage forms, not one representation.
- `L79` — 2026-08-05 — us_bank_account cannot do manual capture: Stripe rejects capture_method=manual for that payment method type outright, so no bank-debit method can serve the authorize-then-capture claim-fee model.
- `L81` — 2026-08-10 — A pending_payment claim never moves its listing off active; the partial unique index on claims is what blocks a second picker, so cancelling the claim is what frees the item.
- `L84` — 2026-08-11 — Raw-SQL UPDATEs in tests bypass the identity map and SessionLocal has expire_on_commit=False: follow every raw UPDATE with db_session.expire_all() or the loaded object keeps stale values (the authorized_claim fixture already models this).
- `L85` — 2026-08-12 — A rate limit attached at APIRouter mount applies to every route on that router, reads included; a 30/hour ceiling sized for claim creation locked a real user out of reading his own receipts within twenty minutes of ordinary use. Scope write ceilings to the write route, never the router.
- `L86` — 2026-08-12 — An empty list in the app is a status code, not a mystery: /claims/my-closed returning 429 rendered as "Nothing here yet" over the user's own data, and two wrong theories (corrupt seed rows, expired token) were chased before the backend log naming rate_limit_exceeded was read.
- `L87` — 2026-08-13 — Production connects through Supabase's transaction-mode pooler on port 6543, where connections are shared between callers between statements; psycopg v3's automatic server-side prepared statements collide there (DuplicatePreparedStatement on _pg3_0). The engine sets connect_args={"prepare_threshold": None} in app/database.py. Local and session-mode (5432) never show this, so it cannot be reproduced locally.
- `L88` — 2026-08-20 — A stale uvicorn bound to 0.0.0.0 outranks a fresh one bound to 127.0.0.1 for anything reaching the Mac over the LAN: the phone kept being served by a process started four days earlier while a newly started backend sat on localhost. Check `lsof -nP -iTCP:8000 -sTCP:LISTEN` and `ps -eo pid,lstart` together — the bind address matters as much as the PID age.
- `L90` — 2026-08-28 — No Python typechecker exists in this repo (no mypy/pyright installed or configured); "run the typecheck" on backend edits means nothing — ast parse or the test suite are the only checks.
- `L91` — 2026-08-29 — Claude Code reported two str_replace edits as applied when only one had landed; commit 2a31a5a shipped an unchanged line as a result. Read changed lines from disk before every git add, or gate the commit on grep in the same command.
- `L97` — 2026-09-01 — In a Postgres data-modifying CTE, the outer SELECT reads the pre-UPDATE snapshot, so a count in the same statement as the UPDATE reports the old number; re-read in a separate statement.
- `L98` — 2026-09-01 — Emptying a column to remove a value destroys the value; 26 seed rows' photo URLs were unrecoverable because they were inserted by hand with no script behind them. Read where a value can be restored from before overwriting it.
- `L99` — 2026-09-02 — There is no signup route on this backend: signup happens inside Supabase and our server first sees a user on GET /auth/me, so any "at signup" gate lives in get_current_user; adding `request: Request` there also means threading it through get_current_user_detached and get_current_user_optional or those paths TypeError.
- `L100` — 2026-09-02 — In a `&&` chain, `grep -c` returning 0 exits 1 and silently kills every command after it; put diagnostic greps last or wrap with `|| true`.

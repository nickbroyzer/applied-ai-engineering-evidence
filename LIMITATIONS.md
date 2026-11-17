# Limitations

What this repository does not prove, what the product does not do, and where a
figure did not survive re-derivation.

## What "verified" means here

Every number in these documents traces to one of three things: a command and its
output in [`verification/repo-metrics-2026-11-17.md`](verification/repo-metrics-2026-11-17.md),
the verbatim run in [`verification/pytest-summary-2026-11-17.txt`](verification/pytest-summary-2026-11-17.txt)
and the CI run in [`verification/ci-run-2026-11-17.md`](verification/ci-run-2026-11-17.md)
(or the recorded runs in [`runnable/knowledge-eval/README.md`](runnable/knowledge-eval/README.md)),
or a Fact-ID in the project's private fact pack (cited so it can be resolved on
request). Nothing is quoted from memory.

"Verified" here means **re-derived on 2026-11-17 at Zelbi commit `4772472b`**.
It does not mean continuously true, monitored, or true at any other commit. The
October files (`*-2026-10-03.*`) and September files (`*-2026-09-03.*`) are
kept unchanged as the records of `8875721` and `3413d028`.

## Figures that did not reproduce, or changed method

The entries below were written at `8875721`, and their figures are as of that
commit. Current values for each are in
[`verification/repo-metrics-2026-11-17.md`](verification/repo-metrics-2026-11-17.md).

**"No retries" on the vision call (found 2026-11-17).** Earlier versions of this
file and of the AI-boundary page said the vision call has no retries. It never
had a retry policy of its own, but its client is built with the Anthropic SDK's
defaults, and the SDK retries twice by default (`DEFAULT_MAX_RETRIES = 2` in the
pinned `anthropic==0.97.0`). The statement is corrected below.

**Block enforcement call sites.** An earlier résumé draft said user blocking was
"enforced at sixteen call sites." The résumé states no count. Re-derived:

```
$ cd backend && grep -rn "is_blocked(\|block_exists_expr(\|NEARBY_BLOCK_FILTER_SQL" app --include="*.py" \
    | grep -v "app/services/block_service.py"
```

Fifteen lines, one of which is an import, leaving **14 helper call sites**
(listings 3, claims 7, messages 2, the post-window sweeper 2). The nearby and map
feeds carry the filter as **4 inlined SQL subqueries** the grep cannot see. In
September the same command gave 13. Sixteen has never reproduced by any method.

**Decisions: 406 → 564, and a method correction.** The September "406 distinct
decisions" reproduces exactly at `3413d028`, but only by a regex that misses
list-item and struck-through entries; the inclusive count at that commit was
435. This repository now uses the inclusive count, 564 at `8875721`. Both
commands are in the metrics file.

**Sessions.** "437 numbered sessions" was the highest session number in the
internal docs at `3413d028`, not a count of sessions (358 distinct numbers are
referenced). This repository now says "sessions numbered through 473".

**Vision tests: 21 → 10.** Eleven tests covered an image-readability endpoint
with no mobile caller, deleted as dead code on 2026-10-03.

Counts that differ by method rather than being wrong, each stated with its
method:

- **Backend tests:** 1,217 `def test_` functions; **1,265 collected and passed**.
- **Knowledge tests:** 109 `def test_` or 114 collected.
- **Payment tests:** 92 in the six files published in September, 118 across nine
  files (96 / 122 collected).
- **Admin routes:** 28 in the four admin routers; 43 behind the admin check
  across all routers.
- **Jobs:** 2 cron runners driving 8 job modules.

## Product limitations

**Stage.** Live on the App Store (iPhone) since 2026-11-04, in active
development. Real use is still small: see the README's status line.

**CI is new.** A workflow (`.github/workflows/tests.yml`) has run the backend
suite and the three mobile Node test files on every push to `master` since
`4772472b`, the commit this refresh is measured at; one run is recorded in
[`verification/ci-run-2026-11-17.md`](verification/ci-run-2026-11-17.md). Before
that commit the suite ran by hand, so "every change was test-gated" is still
false and is never claimed. The workflow's typecheck step is allowed to fail.

**Almost no automated mobile tests, and no web tests.** The mobile app has three
Node test files for pure-logic modules (the arrival rule, the foreground poll
and the foreground update: 133 tests, run on CI). There are no screen,
component or web tests. Mobile surfaces are verified by recorded device walks —
each screen and flow walked on a physical device with the result logged in the
decision log and backlog (see 05-process/verification-gates.md). The 2,565
figure is always written as "2,565 **backend** tests". (At `3413d028` the
mobile tree still held the Expo template's single `StyledText-test.js`; it was
deleted as dead code.)

**Concurrency.** The double-capture guards are read-then-write in Python with no
row lock on the capture path, and there is no simultaneous-double-capture test.
Row locks exist in other places — the DeviceCheck credit check, referral-code
redemption, the arrival stamp, lock-screen card rows and support-agent runs
(8 call sites; the command is in the metrics file).

**Arrival.** Client-reported: either the phone's own arrival check or a manual
"I'm here" tap. The endpoint accepts no coordinates, only which of the two it
was. Not a server-verified geofence.

**Row-level security.** Enabled as unversioned Supabase dashboard state; zero RLS
statements across 74 migrations. Live-checked once, 2026-08-11. Claimed only as
"Supabase Auth with row-level security enabled."

**Location privacy.** An unset fuzz secret warns rather than failing, so a
misconfigured deployment degrades to an unkeyed scheme. Rotation is a manual
recorded procedure, performed once. There is no server-side EXIF strip and no
regression guard; a single dated live check on 2026-08-11 found one stored photo
carrying no GPS or camera identifiers.

**Help search (hybrid retrieval).** Seven tests now exercise the embedding path
with the embedding provider stubbed (`tests/test_knowledge_hybrid_path.py`):
rank fusion, the similarity floor, the fallback to text on an embedding
failure, and the daily ceiling. No test calls the real provider. The recorded
evals are text-only, and eval runs store `embedding_model=None` regardless of
mode. The 24-question before-and-after run behind case study 07 was not saved
as a file; its figures come from the decision log. The daily ceiling counts logged questions, not embedding
calls — a conservative bound that ignores ingestion and eval calls and is not
atomic. Embeddings are a float-array column ranked in Python: no pgvector, no
vector index. With a key configured, every typed question is sent to Voyage AI.
See [`02-architecture/hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md).

**Knowledge evals.** 22/22 with 0 leak failures describes the isolated runs
recorded here, at `8875721`, on text-only retrieval. Not "across all runs."
The standalone eval scripts bind to an ambient database URL and write run rows;
they were not run against a production database. "22-case leak-probe set"
means the 22-case golden set, of which 10 cases are adversarial leak probes and
12 are answers that must not leak.

**AI path.** The vision call has no retry policy of its own (the SDK's two
default retries apply), no circuit breaker, no model routing, no token
accounting, no prompt versioning, no structured-output API, no tool use and no
streaming. 28 tests; the fence-tolerant parse has no dedicated test. The support
agent is the other model call: it uses tool use, records tokens and cost for
every model and tool call, turns the SDK's retries off and runs under a daily
spending cap. Its 275 tests run against a fake model; no automated test calls
the real one.

**Admin and ops.** The watcher's "live" event stream is Server-Sent Events
backed by a 2-second database poll, and no client opens it yet; its only tests
are the 401 cases. The Sentry webhook verifies an HMAC signature but not the
delivery timestamp, so a captured delivery could be replayed (the upsert makes
that a no-op for an existing event). The stream accepts its token in the query
string. No code path creates a dispute row today — disputes start by email —
and the refund-failure path of dispute resolution has no test. See
[`02-architecture/admin-and-ops.md`](02-architecture/admin-and-ops.md).

**Authorization coverage.** No test proves a non-admin receives 403 on the
dispute-*resolve* route specifically; the dispute list and message routes have
one.

**Private photos.** A signed URL is a bearer URL for up to 24 hours. Signing
fails open to the stored, unsigned address — which no longer loads, so nothing
leaks, but the code does not fail closed. Since the 2026-10-13 security pass
(`da50596f`, D588), client-supplied photo addresses on the listing,
completion-photo and message-image paths must be the caller's own upload. See
[`01-product-logic/private-photo-access.md`](01-product-logic/private-photo-access.md).

**Credits.** Only giveaway and invite credits wait for Apple DeviceCheck;
referral credits do not, and D544's one-iPhone-per-referred-friend rule is not
built. DeviceCheck is iOS-only and per device, not per person.
See [`01-product-logic/device-check-credits.md`](01-product-logic/device-check-credits.md).

**Message guard.** Detection is built; enforcement is partial. Rule 4 (repeated
no-shows) is marked not active, and duplicate-photo detection is a stub.

**Trust model.** A separate trust-word raw counter (`no_show_count`) has no
writer and does not heal — dead code. Giver-side no-show scoring is now built
(D580): a missed pickup confirmed through the support agent writes a
`giver_no_show` trust event against the giver, a 40-point deduction
(`complaint_actions.py:121`, `trust_service.py`).

**Legal.** Re-checked against the backlog at `4772472b`. On 2026-10-01
(Session 471) I ruled that the legal pages get no attorney review; the earlier
attorney-review gate had entered the requirements without a recorded ruling.
In its place, the five pages were rewritten against the code with nine
decisions of mine (among them the liability limit, now "the greater of $100" or
twelve months' fees). That pass is recorded as verify-open, not done. The
operating entity, Zelbi Inc., and a notice address are on all five pages. All
five still carry a `noindex` marker in the repository. The country gate is built; a GeoLite2 download with a
weekly refresh was added on 2026-10-03 (`f42e951`), and whether production has
its data source configured is runtime state this repository does not verify.

**Backlog.** The September figure ("roughly twenty priority-zero items open")
was not re-derived and is not repeated.

## Authorship

**Sole human code author.** Git records one author across the full 2,484-commit
history. Commits carry AI-assistant co-author trailers: this was built with AI
coding assistants under my direction, and architecture, decisions, review and
release authority stayed with me. "Sole developer" unqualified is not the claim;
neither is any suggestion the assistants were incidental.

## Limitations of this repository as evidence

- **It is curated.** 61 of 639 decision records, selected by me by theme. The
  selection and its reasons are in [`MANIFEST.md`](MANIFEST.md) for review.
- **Sanitised.** The scam-detection patterns, the real policy corpus and
  account identifiers are withheld. Every removal is itemised in
  [`MANIFEST.md`](MANIFEST.md) with file and line range. The trust and strike
  constants, withheld in September, are now published; MANIFEST §1.2 says why.
- **The source repositories are private.** Only the extracted
  [`runnable/knowledge-eval/`](runnable/knowledge-eval/) package can be executed
  by a reviewer, and it runs the text-only half of Help retrieval.
  [`code/`](code/) holds short excerpts only, not runnable source: under
  my show-the-work-not-the-recipe rule, full source files of the core
  systems are no longer published (MANIFEST §6).
- **Some claims rest on the private record, cited not shown.** Where a write-up
  cites a decision that is not published (D539, D543, D545, D549), the
  number is given so it can be produced on request.
- **Two upstream source documents could not be read** for the September build —
  the Phase 1 survey and the Phase 2 verification report. The test results and
  repository metrics were re-run from scratch instead, then and now.

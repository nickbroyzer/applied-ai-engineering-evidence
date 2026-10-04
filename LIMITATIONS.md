# Limitations

What this repository does not prove, what the product does not do, and where a
figure did not survive re-derivation.

## What "verified" means here

Every number in these documents traces to one of three things: a command and its
output in [`verification/repo-metrics-2026-10-03.md`](verification/repo-metrics-2026-10-03.md),
the verbatim run in [`verification/pytest-summary-2026-10-03.txt`](verification/pytest-summary-2026-10-03.txt)
(or the recorded runs in [`runnable/knowledge-eval/README.md`](runnable/knowledge-eval/README.md)),
or a Fact-ID in the project's private fact pack (cited so it can be resolved on
request). Nothing is quoted from memory.

"Verified" here means **re-derived on 2026-10-03 at Zelbi commit `8875721`**.
It does not mean continuously true, monitored, or true at any other commit. The
September files (`*-2026-09-03.*`) are kept unchanged as the record of
`3413d028`.

## Figures that did not reproduce, or changed method

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

**Stage.** Pre-launch, in active development.

**No CI.** No workflow in the repository at this commit; the suite runs
manually. "Every change was test-gated" is false and is never claimed.

**No automated mobile or web tests.** All 1,265 automated tests are backend.
Mobile surfaces are verified by recorded device walks — each screen and flow
walked on a physical device with the result logged in the decision log and
backlog (see 05-process/verification-gates.md). The figure is always written as
"1,265 **backend** tests". (At `3413d028` the mobile tree still held the Expo
template's single `StyledText-test.js`; it was deleted as dead code.)

**Concurrency.** The double-capture guards are read-then-write in Python with no
row lock on the capture path, and there is no simultaneous-double-capture test.
Row locks now exist in two other places — the DeviceCheck credit check and
referral-code redemption.

**Arrival.** Client-reported. The endpoint accepts no coordinates. Not a
server-verified geofence.

**Row-level security.** Enabled as unversioned Supabase dashboard state; zero RLS
statements across 61 migrations. Live-checked once, 2026-08-11. Claimed only as
"Supabase Auth with row-level security enabled."

**Location privacy.** An unset fuzz secret warns rather than failing, so a
misconfigured deployment degrades to an unkeyed scheme. Rotation is a manual
recorded procedure, performed once. There is no server-side EXIF strip and no
regression guard; a single dated live check on 2026-08-11 found one stored photo
carrying no GPS or camera identifiers.

**Help search (hybrid retrieval).** No test exercises the embedding call, rank
fusion, the daily ceiling or its alerts; the knowledge tests assume no key. The
recorded evals are text-only, and eval runs store `embedding_model=None`
regardless of mode. The daily ceiling counts logged questions, not embedding
calls — a conservative bound that ignores ingestion and eval calls and is not
atomic. Embeddings are a float-array column ranked in Python: no pgvector, no
vector index. With a key configured, every typed question is sent to Voyage AI.
See [`02-architecture/hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md).

**Knowledge evals.** 22/22 with 0 leak failures describes the isolated runs
recorded here, at this commit, on text-only retrieval. Not "across all runs."
The standalone eval scripts bind to an ambient database URL and write run rows;
they were not run against a production database. "22-case leak-probe set"
means the 22-case golden set, of which 10 cases are adversarial leak probes and
12 are answers that must not leak.

**AI path.** No retries, no circuit breaker, no model routing, no token
accounting, no prompt versioning, no structured-output API, no tool use, no
streaming. Ten tests; the fence-tolerant parse has no dedicated test.

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
leaks, but the code does not fail closed. Client-supplied photo keys on the
completion-photo and message-image paths are not ownership-checked. See
[`01-product-logic/private-photo-access.md`](01-product-logic/private-photo-access.md).

**Credits.** Only giveaway and invite credits wait for Apple DeviceCheck;
referral credits do not. DeviceCheck is iOS-only and per device, not per person.
See [`01-product-logic/device-check-credits.md`](01-product-logic/device-check-credits.md).

**Message guard.** Detection is built; enforcement is partial. Rule 4 (repeated
no-shows) is marked not active, and duplicate-photo detection is a stub.

**Trust model.** A separate trust-word raw counter (`no_show_count`) has no
writer and does not heal — dead code. Giver-side no-show scoring is approved but
unbuilt, because no event records a giver no-show.

**Legal.** As recorded on 2026-09-03 and **not re-checked** for this refresh:
counsel review outstanding, operating entity unnamed, legal pages carrying
placeholder limitations. The country gate is built; a GeoLite2 download with a
weekly refresh was added on 2026-10-03 (`f42e951`), and whether production has
its data source configured is runtime state this repository does not verify.

**Backlog.** The September figure ("roughly twenty priority-zero items open")
was not re-derived and is not repeated.

## Authorship

**Sole human code author.** Git records one author across the full 2,122-commit
history. Commits carry AI-assistant co-author trailers: this was built with AI
coding assistants under my direction, and architecture, decisions, review and
release authority stayed with me. "Sole developer" unqualified is not the claim;
neither is any suggestion the assistants were incidental.

## Limitations of this repository as evidence

- **It is curated.** 48 of 564 decision records, selected by me by theme. The
  selection and its reasons are in [`MANIFEST.md`](MANIFEST.md) for review.
- **Sanitised.** The scam-detection patterns, the real policy corpus and
  account identifiers are withheld. Every removal is itemised in
  [`MANIFEST.md`](MANIFEST.md) with file and line range. The trust and strike
  constants, withheld in September, are now published; MANIFEST §1.2 says why.
- **The source repositories are private.** Only the extracted
  [`runnable/knowledge-eval/`](runnable/knowledge-eval/) package can be executed
  by a reviewer, and it runs the text-only half of Help retrieval. Everything
  else in [`code/`](code/) is read-only evidence and is not runnable as
  extracted.
- **Some claims rest on the private record, cited not shown.** Where a write-up
  cites a decision that is not published (D537, D539, D543, D545, D549), the
  number is given so it can be produced on request.
- **Two upstream source documents could not be read** for the September build —
  the Phase 1 survey and the Phase 2 verification report. The test results and
  repository metrics were re-run from scratch instead, then and now.

# Limitations

What this repository does not prove, what the product does not do, and the one
place where a résumé figure did not survive re-derivation.

## What "verified" means here

Every number in these documents traces to one of three things: a command and its
output in [`verification/repo-metrics-2026-09-03.md`](verification/repo-metrics-2026-09-03.md),
the verbatim run in [`verification/pytest-summary-2026-09-03.txt`](verification/pytest-summary-2026-09-03.txt),
or a Fact-ID in the project's private fact pack (cited so it can be resolved on
request). Nothing is quoted from memory.

"Verified" here means **re-derived on 2026-09-03 at commit `3413d028`**. It does
not mean continuously true, monitored, or true at any other commit.

## One figure that did not reproduce — flagged for review

An earlier résumé draft stated that user blocking was **"enforced at sixteen call sites."** The current résumé states no count.

Re-deriving it at the same commit, this is what I get:

```
$ grep -rn "is_blocked(\|block_exists_expr(\|NEARBY_BLOCK_FILTER_SQL" app --include="*.py" \
    | grep -v "app/services/block_service.py"
```

Fourteen lines, one of which is an import, leaving **13 enforcement call sites**
(11 in routers, 1 in a job, plus the raw-SQL feed filter). A grep for the block
model itself adds only the block-list CRUD router, which is not enforcement.

I could not reproduce 16 by any method I tried. The design claim — symmetric
enforcement from a single shared pair of helpers, applied across listings,
messages, claims and the feed — is intact and is what the documents here
describe. The **count** is not, and this repository uses 13 with the command
above rather than repeating a figure it cannot re-derive.

**Resolved 2026-09-03:** the résumé line now states no count; this repository
uses 13 with the command above.

Two other counts differ by method rather than being wrong, and both are stated
with their method:

- **Knowledge tests: 108 or 113.** 108 is the `def test_` count and is what the
  résumé uses; 113 is pytest's collected count once parametrised cases expand.
  Same six files, same commit.
- **Job entrypoints: 4 or 6.** Four cron runner scripts; six job modules they
  invoke.

## Product limitations

**Stage.** Pre-launch, in active development. September 2026 is a target, not a
completed launch or a submission state.

**No CI.** No workflow in the repository at this commit; the suite ran manually
at session close. "Every change was test-gated" is false and is never claimed.

**No mobile or web tests.** All 751 tests are backend. The figure is always
written as "751 **backend** tests".

**Concurrency.** Double-capture guards are read-then-write in Python; zero row
locks; no simultaneous-double-capture test.

**Arrival.** Client-reported. The endpoint accepts no coordinates. Not a
server-verified geofence.

**Row-level security.** Enabled as unversioned Supabase dashboard state; zero RLS
statements across 44 migrations. Live-checked once, 2026-08-11. Claimed only as
"Supabase Auth with row-level security enabled."

**Location privacy.** An unset fuzz secret warns rather than failing, so a
misconfigured deployment degrades to an unkeyed scheme. Rotation is a manual
recorded procedure, performed once. There is no server-side EXIF strip and no
regression guard; a single dated live check on 2026-08-11 found one stored photo
carrying no GPS or camera identifiers.

**Message guard.** Detection is built; enforcement is partial. Duplicate-photo
detection is a stub.

**Trust model.** A separate trust-word raw counter has no writer and does not
heal — dead code, filed for deletion. Giver-side no-show scoring is approved but
unbuilt, because no event records a giver no-show.

**Authorization coverage.** No test proves a non-admin receives 403 on the
dispute-resolution endpoint.

**AI path.** No retries, no explicit timeout, no circuit breaker, no model
routing, no token accounting, no prompt versioning, no structured-output API, no
tool use, no streaming. The readability endpoint exists on the backend with no
mobile caller and is not presented as a production flow.

**Knowledge evals.** 22/22 with 0 leak failures describes the single isolated run
recorded here, at this commit. Not "across all runs." The standalone eval scripts
bind to an ambient database URL and write run rows; they were not run against a
production database, and no isolation proof exists in their source.

**Legal.** Counsel review outstanding. Operating entity unnamed. The country gate
is built but ineffective until its data source is configured. Legal pages carry
placeholder limitations. "All launch gates closed" is not claimed here — note
that an internal status document does assert all gates closed, and this
repository deliberately uses the narrower, dated claim instead.

**Backlog.** Roughly twenty priority-zero items remain open at this commit.

## Authorship

**Sole human code author.** Git records one author across the full 1,688-commit
history. Commits carry AI-assistant co-author trailers: this was built with AI
coding assistants under my direction, and architecture, decisions, review and
release authority stayed with me. "Sole developer" unqualified is not the claim;
neither is any suggestion the assistants were incidental.

## Limitations of this repository as evidence

- **It is curated.** 45 of 406 decision records, selected by me by theme. The
  selection and its reasons are in [`MANIFEST.md`](MANIFEST.md) for review.
- **Sanitised.** Tuned constants, detection patterns and the real policy corpus
  are withheld. Every removal is itemised in [`MANIFEST.md`](MANIFEST.md) with
  file and line range.
- **The source repositories are private.** Only the extracted
  [`runnable/knowledge-eval/`](runnable/knowledge-eval/) package can be executed
  by a reviewer; everything else in [`code/`](code/) is read-only evidence and is
  not runnable as extracted.
- **Two upstream source documents could not be read.** The Phase 1 survey and the
  Phase 2 verification report exist only as prior-session artifacts and are not
  on disk. Rather than quote them second-hand, the test results and repository
  metrics here were **re-run from scratch on 2026-09-03** and are recorded with
  their commands. Where a figure could only have come from those documents, it is
  attributed to its Fact-ID instead.

# Repository metrics — commands and outputs, 2026-10-03

**Source repository:** `zelbi.ai` (private)
**Branch:** `master` · **HEAD:** `88757212b5ea2395913cee61d81b05822818484a`
**Re-run:** 2026-10-03, macOS (Darwin 25.6.0), in a fresh `git clone --no-hardlinks`
of the repository checked out at that commit — never the live working tree,
which another session may be editing.

This file supersedes [`repo-metrics-2026-09-03.md`](repo-metrics-2026-09-03.md)
for every current number in this repository. The September file is kept,
unchanged, as history: what was true at `3413d028`.

Every number traces to a row here, to `pytest-summary-2026-10-03.txt`, to the
recorded run in [`../runnable/knowledge-eval/README.md`](../runnable/knowledge-eval/README.md),
or to a Fact-ID in the private fact pack. (The September file also cites an
`eval-run-2026-09-03.md`; no such file was ever published. The eval run it
meant is the one recorded in the runnable package's README.)

## Verbatim session

Every command below was run from the repository root, each in its own
subshell.

```
$ git rev-list --count HEAD
2122

$ git rev-parse HEAD
88757212b5ea2395913cee61d81b05822818484a

$ git rev-parse --abbrev-ref HEAD
master

$ git log --format=%ad --date=short | sort -u | wc -l
     155

$ git log --reverse --format=%ad --date=short | head -1
2026-04-09

$ git log -1 --format=%ad --date=short
2026-10-03

$ git log --format=%an | sort -u
nickbroyzer

$ find mobile/app -name '*.tsx' -not -name '_layout.tsx' | wc -l
      38

$ find mobile/app -name '*.tsx' | wc -l
      43

$ ls backend/app/routers/*.py | grep -v __init__ | wc -l
      22

$ ls backend/app/services/*.py | wc -l
      25

$ ls backend/app/jobs/run_*.py | wc -l
       2

$ ls backend/app/jobs/*.py | grep -v -e __init__ -e '/run_' | wc -l
       8

$ ls backend/migrations/versions/*.py | wc -l
      61

$ ls backend/tests/test_*.py | wc -l
      91

$ ls -d .github
ls: .github: No such file or directory

$ grep -ril 'row level security\|ENABLE ROW LEVEL' backend/migrations/versions | wc -l
       0

$ grep -oE '^(\*\*)?D[0-9]+' docs/agents/10-implementation-plan.md | sort -u | wc -l
     535

$ grep -oE '^[-*~#> |]*D[0-9]+' docs/agents/10-implementation-plan.md | grep -oE 'D[0-9]+' | sort -u | wc -l
     564

$ grep -oE '^[-*~#> |]*D[0-9]+' docs/agents/10-implementation-plan.md | grep -oE '[0-9]+' | sort -n | tail -1
574

$ git grep -h -oE 'Session [0-9]+' HEAD -- docs/agents | grep -oE '[0-9]+' | sort -n | tail -1
473

$ git grep -h -oE 'Session [0-9]+' HEAD -- docs/agents | sort -u | wc -l
     394

$ cd backend && grep -rn "is_blocked(\|block_exists_expr(\|NEARBY_BLOCK_FILTER_SQL" app --include="*.py" | grep -v "app/services/block_service.py"
app/routers/listings.py:20:from app.services.block_service import NEARBY_BLOCK_FILTER_SQL, block_exists_expr, is_blocked
app/routers/listings.py:603:        .filter(~block_exists_expr(current_user.id, Listing.giver_id))
app/routers/listings.py:675:    if is_blocked(db, current_user.id, user_id):
app/routers/listings.py:726:    if viewer_id is not None and is_blocked(db, viewer_id, listing.giver_id):
app/routers/claims.py:668:            ~block_exists_expr(current_user.id, Claim.picker_id),
app/routers/claims.py:698:            ~block_exists_expr(current_user.id, Listing.giver_id),
app/routers/claims.py:749:            ~block_exists_expr(current_user.id, Listing.giver_id),
app/routers/claims.py:764:            ~block_exists_expr(current_user.id, Claim.picker_id),
app/routers/claims.py:1022:    if is_picker and claim.listing is not None and is_blocked(
app/routers/claims.py:1097:    if is_picker and is_blocked(db, current_user.id, listing.giver_id):
app/routers/claims.py:1130:    if is_blocked(db, current_user.id, listing.giver_id):
app/routers/messages.py:80:    if is_blocked(db, user_id, listing.giver_id):
app/routers/messages.py:99:    if is_blocked(db, listing.giver_id, claim.picker_id):
app/jobs/post_window_sweeper.py:237:    if not is_blocked(db, claim.picker_id, listing.giver_id):
app/jobs/post_window_sweeper.py:526:        if is_blocked(db, claim.picker_id, listing.giver_id):

$ grep -c "giver_id NOT IN (SELECT blocked_id FROM blocked_users" backend/app/routers/listings.py
4

$ cat backend/app/routers/admin{,_actions,_reads,_writes}.py | grep -cE '^@router\.(get|post|put|patch|delete)\('
28

$ grep -hE 'Depends\((require_admin|_stream_admin)\)' backend/app/routers/*.py | wc -l
      43

$ grep -rn -E 'with_for_update|FOR UPDATE' backend/app --include='*.py'
backend/app/routers/users.py:508:    FOR UPDATE, in the order pending_device_check_credit reads them."""
backend/app/routers/users.py:520:        .with_for_update()
backend/app/services/referral_service.py:504:        .with_for_update()
backend/app/services/referral_service.py:579:    Locks the code row FOR UPDATE and stamps ``used_at``, ``used_by_user_id`` (the picker)

$ cat backend/tests/test_ai{,_service,_object_key_ownership,_soft_item}.py | grep -cE '^(async )?def test_'
10

$ for f in backend/tests/test_knowledge_*.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_knowledge_answer.py 20
backend/tests/test_knowledge_ask_endpoint.py 20
backend/tests/test_knowledge_eval_seed.py 15
backend/tests/test_knowledge_ingestion.py 19
backend/tests/test_knowledge_log_retention.py 1
backend/tests/test_knowledge_models.py 21
backend/tests/test_knowledge_retrieval.py 13

$ cat backend/tests/test_knowledge_*.py | grep -cE '^(async )?def test_'
109

$ grep -cE '^(async )?def test_' backend/tests/test_coordinate_privacy.py
10

$ for f in backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing,claim_deferred_intent,claim_fees,curbside_sweeper}.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_stripe_service.py 35
backend/tests/test_stripe_webhooks.py 20
backend/tests/test_pending_payment_sweeper.py 8
backend/tests/test_post_window_sweeper.py 22
backend/tests/test_stripe_customer.py 4
backend/tests/test_stripe_billing.py 3
backend/tests/test_claim_deferred_intent.py 11
backend/tests/test_claim_fees.py 10
backend/tests/test_curbside_sweeper.py 5

$ cat backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing}.py | grep -cE '^(async )?def test_'
92

$ cat backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing,claim_deferred_intent,claim_fees,curbside_sweeper}.py | grep -cE '^(async )?def test_'
118

$ for f in backend/tests/test_admin_*.py backend/tests/test_watcher.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_admin_actions.py 15
backend/tests/test_admin_authorization.py 2
backend/tests/test_admin_claims.py 11
backend/tests/test_admin_disputes.py 19
backend/tests/test_admin_flags.py 13
backend/tests/test_admin_health.py 4
backend/tests/test_admin_listings.py 16
backend/tests/test_admin_money.py 13
backend/tests/test_admin_notes.py 8
backend/tests/test_watcher.py 21

$ cat backend/tests/test_admin_*.py backend/tests/test_watcher.py | grep -cE '^(async )?def test_'
122

$ for f in backend/tests/test_{trust_service,strike,dispute_suspension,blocks,scam_detection,scam_wiring,credits_devicecheck,devicecheck_service,credits_giveaway}.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_trust_service.py 14
backend/tests/test_strike.py 10
backend/tests/test_dispute_suspension.py 8
backend/tests/test_blocks.py 35
backend/tests/test_scam_detection.py 48
backend/tests/test_scam_wiring.py 21
backend/tests/test_credits_devicecheck.py 23
backend/tests/test_devicecheck_service.py 17
backend/tests/test_credits_giveaway.py 23

$ cat backend/tests/test_{trust_service,strike,dispute_suspension,blocks,scam_detection,scam_wiring,credits_devicecheck,devicecheck_service,credits_giveaway}.py | grep -cE '^(async )?def test_'
199

$ cat backend/tests/test_{signed_photo_reads,r2_delete}.py | grep -cE '^(async )?def test_'
26

$ cat backend/tests/test_*.py | grep -cE '^(async )?def test_'
1217

$ python3 -c "import json;c=json.load(open('backend/app/data/knowledge_eval_cases.json'));c=c.get('cases',c) if isinstance(c,dict) else c;print(len(c));import collections;print(collections.Counter(x.get('expected_behavior') for x in c))"
22
Counter({'answer': 12, 'refuse_and_route': 10})

```

## The two counting methods that changed, and why

Two figures in the September repository came from commands that were not
written down. Both have now been reproduced at the September commit, so the
method that produced them is known.

```
$ git show 3413d028:docs/agents/10-implementation-plan.md | grep -oE '^(\*\*)?D[0-9]+' | sort -u | wc -l
     406

$ git show 3413d028:docs/agents/10-implementation-plan.md | grep -oE '^[-*~#> |]*D[0-9]+' | grep -oE 'D[0-9]+' | sort -u | wc -l
     435

$ git show 3413d028:docs/agents/10-implementation-plan.md | grep -oE '^- D[0-9]+' | grep -oE 'D[0-9]+' | sort -u | wc -l
      37

$ git show 3413d028:docs/agents/10-implementation-plan.md | grep -oE '^[-*#> |]*~~\**D[0-9]+' | grep -oE 'D[0-9]+' | sort -u | wc -l
       8

$ git grep -h -oE 'Session [0-9]+' 3413d028 -- docs/agents | grep -oE '[0-9]+' | sort -n | tail -1
437

$ git grep -h -oE 'Session [0-9]+' 3413d028 -- docs/agents | sort -u | wc -l
     358
```

**Decisions — correction.** The September figure, 406, counted only entries
that open a line as `D<n>` or `**D<n>`. That misses 37 entries written as list
items (`- D66 — …`) and 8 struck-through entries (`~~D1 — …`), which are
superseded but still numbered decisions. `03-decisions/INDEX.md` described 406
as "parsing every `D<n>` entry"; it was not every entry. This repository now
uses the inclusive count: **435 at `3413d028`, 564 at `8875721`**, highest
`D574`. The narrow count is shown above so the old figure stays reproducible.

**Sessions.** 437 was the **highest session number** recorded in
`docs/agents` at `3413d028`, not a count of sessions: only 358 distinct session
numbers are referenced there. At `8875721` the highest is **473** (394
referenced). This repository says "sessions numbered through 473".

## What each number means

| Metric | Value | Method / caveat | Fact-ID |
|---|---|---|---|
| Commits on `master` | 2,122 | `git rev-list --count HEAD` | Z-001 |
| Distinct Git authors | 1 (`nickbroyzer`) | Sole **human** code author; commits carry AI-assistant co-author trailers | Z-002 |
| Active development days | 155 | Distinct author dates, 2026-04-09 → 2026-10-03 (177 calendar days) | Z-003 |
| Mobile route screens | 38 | `mobile/app/**/*.tsx` excluding `_layout.tsx`; 43 with layouts. Two message screens were removed in `4d9bc06` | A-001 |
| Backend routers | 22 | `backend/app/routers/*.py` excluding `__init__.py`. `disputes.py` was deleted in `b6ced95` | A-002 |
| Backend service modules | 25 | `backend/app/services/*.py`, plus the `knowledge/` and `email_html/` packages | A-002 |
| Cron runners / job modules | 2 / 8 | `run_daily_jobs.py`, `run_frequent_jobs.py`. `b6ced95` removed `run_recommendation_scan.py` and `run_saved_deadline_scan.py`; both jobs run inside `run_daily_jobs.py` (lines 19–20) | A-002 |
| Alembic revisions | 61 | `backend/migrations/versions/*.py` | A-003 |
| Backend test files | 91 | `test_*.py` only | T-003 |
| Backend `def test_` functions | 1,217 | Collected and passed counts: see `pytest-summary-2026-10-03.txt` | T-001 |
| RLS statements in migrations | 0 | Unchanged: row-level security is dashboard state | A-004 |
| CI workflow | absent | No `.github/` directory | A-012 |
| Row locks | 2 call sites | `users.py:520` (DeviceCheck credit), `referral_service.py:504` (referral code). **None on the capture path** — the double-capture guards are still read-then-write | — |
| Numbered decisions | 564, highest D574 | Inclusive method above | Z-005 |
| Highest session number | 473 | See above | — |
| Block enforcement call sites | 14 | The September grep, minus the import line. Plus 4 inlined `NOT IN (SELECT … FROM blocked_users …)` subqueries in the nearby and map feed queries, which the grep cannot see; the imported `NEARBY_BLOCK_FILTER_SQL` constant is no longer used | — |
| Admin routes | 28 / 43 | 28 decorated routes in the four `admin*.py` routers; 43 routes across all routers that depend on `require_admin` (or the stream's admin check) | — |
| Golden eval cases | 22 | 12 answer, 10 refuse-and-route (the adversarial leak probes) | R-004 |

## Component test counts

`def test_` counts with `grep -cE '^(async )?def test_'`. pytest's collected
count is higher wherever a test is parametrized; that column is filled from the
recorded pytest run.

| Component | `def test_` | Collected | Files |
|---|---|---|---|
| AI vision pipeline | 10 | see pytest summary | `test_ai.py` 1, `test_ai_service.py` 4, `test_ai_object_key_ownership.py` 2, `test_ai_soft_item.py` 3. Was 21 at `3413d028`: `b6ced95` deleted the readability endpoint and its tests |
| Knowledge system | 109 | see pytest summary | `test_knowledge_{answer,ask_endpoint,eval_seed,ingestion,log_retention,models,retrieval}.py` (20+20+15+19+1+21+13). **None exercises the embedding, rank-fusion or daily-cap code** |
| Coordinate privacy | 10 | see pytest summary | `test_coordinate_privacy.py` |
| Payment path | 92 / 118 | see pytest summary | The six files published in September: `test_stripe_service.py` 35, `test_stripe_webhooks.py` 20, `test_pending_payment_sweeper.py` 8, `test_post_window_sweeper.py` 22, `test_stripe_customer.py` 4, `test_stripe_billing.py` 3 = 92. Plus `test_claim_deferred_intent.py` 11, `test_claim_fees.py` 10, `test_curbside_sweeper.py` 5 = 118 |
| Admin API and Sentry watcher | 122 | see pytest summary | `test_admin_{actions,authorization,claims,disputes,flags,health,listings,money,notes}.py` (15+2+11+19+13+4+16+13+8) + `test_watcher.py` 21 |
| Trust and safety | 199 | see pytest summary | `test_trust_service.py` 14, `test_strike.py` 10, `test_dispute_suspension.py` 8, `test_blocks.py` 35, `test_scam_detection.py` 48, `test_scam_wiring.py` 21, `test_credits_devicecheck.py` 23, `test_devicecheck_service.py` 17, `test_credits_giveaway.py` 23 |
| Private photo access | 26 | see pytest summary | `test_signed_photo_reads.py` 21, `test_r2_delete.py` 5 |

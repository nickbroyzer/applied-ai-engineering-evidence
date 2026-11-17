# Repository metrics — commands and outputs, 2026-11-17

**Source repository:** `zelbi.ai` (private)
**Branch:** `master` · **HEAD:** `4772472bdf2f370ea3b54971d8e94c9474cf7aaf`
**Re-run:** 2026-11-17, macOS (Darwin 25.6.0), in a fresh `git clone --no-hardlinks`
of the repository checked out at that commit — never the live working tree,
which another session may be editing.

This file supersedes [`repo-metrics-2026-10-03.md`](repo-metrics-2026-10-03.md)
for every current number in this repository. The October file is kept,
unchanged, as history: what was true at `8875721`.

Every number traces to a row here, to [`pytest-summary-2026-11-17.txt`](pytest-summary-2026-11-17.txt),
to [`ci-run-2026-11-17.md`](ci-run-2026-11-17.md), or to the recorded run in
[`../runnable/knowledge-eval/README.md`](../runnable/knowledge-eval/README.md).

## Verbatim session

Every command below is the October file's command, unchanged, run from the
repository root, each in its own subshell. The session ran before the test
suite, so no test artefacts were in the tree.

```
$ git rev-list --count HEAD
2484

$ git rev-parse HEAD
4772472bdf2f370ea3b54971d8e94c9474cf7aaf

$ git rev-parse --abbrev-ref HEAD
master

$ git log --format=%ad --date=short | sort -u | wc -l
     188

$ git log --reverse --format=%ad --date=short | head -1
2026-04-09

$ git log -1 --format=%ad --date=short
2026-11-16

$ git log --format=%an | sort -u
nickbroyzer

$ find mobile/app -name '*.tsx' -not -name '_layout.tsx' | wc -l
      43

$ find mobile/app -name '*.tsx' | wc -l
      48

$ ls backend/app/routers/*.py | grep -v __init__ | wc -l
      28

$ ls backend/app/services/*.py | wc -l
      35

$ ls backend/app/jobs/run_*.py | wc -l
       2

$ ls backend/app/jobs/*.py | grep -v -e __init__ -e '/run_' | wc -l
      10

$ ls backend/migrations/versions/*.py | wc -l
      74

$ ls backend/tests/test_*.py | wc -l
     131

$ ls -d .github
.github

$ grep -ril 'row level security\|ENABLE ROW LEVEL' backend/migrations/versions | wc -l
       0

$ grep -oE '^(\*\*)?D[0-9]+' docs/agents/10-implementation-plan.md | sort -u | wc -l
     610

$ grep -oE '^[-*~#> |]*D[0-9]+' docs/agents/10-implementation-plan.md | grep -oE 'D[0-9]+' | sort -u | wc -l
     639

$ grep -oE '^[-*~#> |]*D[0-9]+' docs/agents/10-implementation-plan.md | grep -oE '[0-9]+' | sort -n | tail -1
649

$ git grep -h -oE 'Session [0-9]+' HEAD -- docs/agents | grep -oE '[0-9]+' | sort -n | tail -1
494

$ git grep -h -oE 'Session [0-9]+' HEAD -- docs/agents | sort -u | wc -l
     415

$ cd backend && grep -rn "is_blocked(\|block_exists_expr(\|NEARBY_BLOCK_FILTER_SQL" app --include="*.py" | grep -v "app/services/block_service.py"
app/routers/listings.py:21:from app.services.block_service import NEARBY_BLOCK_FILTER_SQL, block_exists_expr, is_blocked
app/routers/listings.py:673:        .filter(~block_exists_expr(current_user.id, Listing.giver_id))
app/routers/listings.py:884:    if is_blocked(db, current_user.id, user_id):
app/routers/listings.py:936:    if viewer_id is not None and is_blocked(db, viewer_id, listing.giver_id):
app/routers/claims.py:761:            ~block_exists_expr(current_user.id, Claim.picker_id),
app/routers/claims.py:791:            ~block_exists_expr(current_user.id, Listing.giver_id),
app/routers/claims.py:842:            ~block_exists_expr(current_user.id, Listing.giver_id),
app/routers/claims.py:857:            ~block_exists_expr(current_user.id, Claim.picker_id),
app/routers/claims.py:1117:    if is_picker and claim.listing is not None and is_blocked(
app/routers/claims.py:1192:    if is_picker and is_blocked(db, current_user.id, listing.giver_id):
app/routers/claims.py:1228:    if is_blocked(db, current_user.id, listing.giver_id):
app/routers/claims.py:2250:        if is_blocked(db, current_user.id, listing.giver_id):
app/routers/messages.py:130:    if is_blocked(db, user_id, listing.giver_id):
app/routers/messages.py:149:    if is_blocked(db, listing.giver_id, claim.picker_id):
app/routers/complaints.py:124:            ~block_exists_expr(current_user.id, Listing.giver_id),
app/routers/complaints.py:135:            ~block_exists_expr(current_user.id, Claim.picker_id),
app/jobs/post_window_sweeper.py:249:    if not is_blocked(db, claim.picker_id, listing.giver_id):
app/jobs/post_window_sweeper.py:544:        if is_blocked(db, claim.picker_id, listing.giver_id):

$ grep -c "giver_id NOT IN (SELECT blocked_id FROM blocked_users" backend/app/routers/listings.py
4

$ cat backend/app/routers/admin{,_actions,_reads,_writes}.py | grep -cE '^@router\.(get|post|put|patch|delete)\('
36

$ grep -hE 'Depends\((require_admin|_stream_admin)\)' backend/app/routers/*.py | wc -l
      64

$ grep -rn -E 'with_for_update|FOR UPDATE' backend/app --include='*.py'
backend/app/routers/users.py:590:    FOR UPDATE, in the order pending_device_check_credit reads them."""
backend/app/routers/users.py:602:        .with_for_update()
backend/app/routers/claims.py:2350:    claim = db.query(Claim).filter(Claim.id == claim_id).with_for_update().first()
backend/app/routers/agents_admin.py:268:    run = (query.with_for_update() if lock else query).one_or_none()
backend/app/routers/live_activities.py:152:        .with_for_update()
backend/app/routers/live_activities.py:334:        .with_for_update()
backend/app/routers/live_activities.py:478:        .with_for_update()
backend/app/services/agents/execute.py:109:    index), locked FOR UPDATE when asked."""
backend/app/services/agents/execute.py:114:        query = query.with_for_update()
backend/app/services/referral_service.py:504:        .with_for_update()
backend/app/services/referral_service.py:579:    Locks the code row FOR UPDATE and stamps ``used_at``, ``used_by_user_id`` (the picker)

$ cat backend/tests/test_ai{,_service,_object_key_ownership,_soft_item}.py | grep -cE '^(async )?def test_'
10

$ for f in backend/tests/test_knowledge_*.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_knowledge_answer.py 20
backend/tests/test_knowledge_ask_endpoint.py 20
backend/tests/test_knowledge_eval_seed.py 15
backend/tests/test_knowledge_hybrid_path.py 7
backend/tests/test_knowledge_ingestion.py 19
backend/tests/test_knowledge_log_retention.py 1
backend/tests/test_knowledge_models.py 21
backend/tests/test_knowledge_retrieval.py 13

$ cat backend/tests/test_knowledge_*.py | grep -cE '^(async )?def test_'
116

$ grep -cE '^(async )?def test_' backend/tests/test_coordinate_privacy.py
10

$ for f in backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing,claim_deferred_intent,claim_fees,curbside_sweeper}.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_stripe_service.py 38
backend/tests/test_stripe_webhooks.py 22
backend/tests/test_pending_payment_sweeper.py 8
backend/tests/test_post_window_sweeper.py 23
backend/tests/test_stripe_customer.py 4
backend/tests/test_stripe_billing.py 3
backend/tests/test_claim_deferred_intent.py 11
backend/tests/test_claim_fees.py 10
backend/tests/test_curbside_sweeper.py 5

$ cat backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing}.py | grep -cE '^(async )?def test_'
98

$ cat backend/tests/test_{stripe_service,stripe_webhooks,pending_payment_sweeper,post_window_sweeper,stripe_customer,stripe_billing,claim_deferred_intent,claim_fees,curbside_sweeper}.py | grep -cE '^(async )?def test_'
124

$ for f in backend/tests/test_admin_*.py backend/tests/test_watcher.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_admin_actions.py 15
backend/tests/test_admin_alert_emails.py 10
backend/tests/test_admin_authorization.py 2
backend/tests/test_admin_claims.py 11
backend/tests/test_admin_complaints.py 20
backend/tests/test_admin_disputes.py 19
backend/tests/test_admin_flags.py 13
backend/tests/test_admin_health.py 4
backend/tests/test_admin_health_labels.py 1
backend/tests/test_admin_listings.py 16
backend/tests/test_admin_money.py 13
backend/tests/test_admin_notes.py 8
backend/tests/test_watcher.py 21

$ cat backend/tests/test_admin_*.py backend/tests/test_watcher.py | grep -cE '^(async )?def test_'
153

$ for f in backend/tests/test_{trust_service,strike,dispute_suspension,blocks,scam_detection,scam_wiring,credits_devicecheck,devicecheck_service,credits_giveaway}.py; do echo "$f $(grep -cE '^(async )?def test_' $f)"; done
backend/tests/test_trust_service.py 14
backend/tests/test_strike.py 10
backend/tests/test_dispute_suspension.py 8
backend/tests/test_blocks.py 35
backend/tests/test_scam_detection.py 50
backend/tests/test_scam_wiring.py 21
backend/tests/test_credits_devicecheck.py 23
backend/tests/test_devicecheck_service.py 17
backend/tests/test_credits_giveaway.py 23

$ cat backend/tests/test_{trust_service,strike,dispute_suspension,blocks,scam_detection,scam_wiring,credits_devicecheck,devicecheck_service,credits_giveaway}.py | grep -cE '^(async )?def test_'
201

$ cat backend/tests/test_{signed_photo_reads,r2_delete}.py | grep -cE '^(async )?def test_'
26

$ cat backend/tests/test_*.py | grep -cE '^(async )?def test_'
1768

$ python3 -c "import json;c=json.load(open('backend/app/data/knowledge_eval_cases.json'));c=c.get('cases',c) if isinstance(c,dict) else c;print(len(c));import collections;print(collections.Counter(x.get('expected_behavior') for x in c))"
22
Counter({'answer': 12, 'refuse_and_route': 10})
```

## Supplementary counts

The October commands count only `backend/tests/test_*.py`. Since October the
support agent's tests live in a subfolder, `backend/tests/agents/`, which those
commands do not see. These extra commands, run in the same clone after the
test suite (the `__pycache__` folders it left are ignored by Git and are not
test files), count it, the vision tests in all six of their files, and the
workflow file.

```
$ find backend/tests -name 'test_*.py' | wc -l
     148

$ find backend/tests -name 'test_*.py' -exec cat {} + | grep -cE '^(async )?def test_'
2043

$ cat backend/tests/agents/*.py | grep -cE '^(async )?def test_'
275

$ cat backend/tests/test_ai*.py | grep -cE '^(async )?def test_'
28

$ ls .github/workflows/
tests.yml
```

## What each number means

| Metric | Value | Method / caveat |
|---|---|---|
| Commits on `master` | 2,484 | `git rev-list --count HEAD`. Was 2,122 at `8875721` |
| Distinct Git authors | 1 (`nickbroyzer`) | Sole **human** code author; commits carry AI-assistant co-author trailers |
| Active development days | 188 | Distinct author dates, 2026-04-09 → 2026-11-16 (222 calendar days). Was 155 |
| Mobile route screens | 43 | `mobile/app/**/*.tsx` excluding `_layout.tsx`; 48 with layouts. Was 38 / 43 |
| Backend routers | 28 | `backend/app/routers/*.py` excluding `__init__.py`. Was 22 |
| Backend service modules | 35 | `backend/app/services/*.py`, plus the `knowledge/`, `email_html/` and `agents/` packages. Was 25 |
| Cron runners / job modules | 2 / 10 | `run_daily_jobs.py`, `run_frequent_jobs.py`. Was 2 / 8 |
| Alembic revisions | 74 | `backend/migrations/versions/*.py`. Was 61 |
| Backend test files | 131 top level, 148 in all | `test_*.py`; 17 more in `backend/tests/agents/`. Was 91 |
| Backend `def test_` functions | 1,768 top level, 2,043 in all | 275 more in `backend/tests/agents/`. Was 1,217 |
| Backend tests collected & passed, locally | **2,565** | [`pytest-summary-2026-11-17.txt`](pytest-summary-2026-11-17.txt): 2,565 passed, exit 0, clean checkout, network blocked. Was 1,265 |
| Backend tests on CI | **2,554 passed, 11 skipped** | [`ci-run-2026-11-17.md`](ci-run-2026-11-17.md): run `44041033625` at the same commit. The 11 are the GeoLite2 tests, which skip without the database file |
| Mobile Node tests on CI | 133 | The three `mobile/utils/*.test.mjs` files; 110 in `arrivalRule.test.mjs`. There are no other mobile tests |
| RLS statements in migrations | 0 | Unchanged: row-level security is dashboard state |
| CI workflow | present | `.github/workflows/tests.yml`: backend suite and the three Node test files on every push to `master`. Was absent |
| Row locks | 8 call sites | `users.py:602` (DeviceCheck credit), `referral_service.py:504` (referral code), `claims.py:2350` (arrival stamp), `live_activities.py:152,334,478` (lock-screen card rows), `agents_admin.py:268` and `agents/execute.py:114` (agent runs). **None in the capture code** — the double-capture guards are still read-then-write. Was 2 |
| Numbered decisions | 639, highest D649 | Inclusive method, as in October. The narrow count is 610. Was 564, highest D574 |
| Highest session number | 494 | 415 distinct session numbers referenced. Was 473 (394) |
| Block enforcement call sites | 17 | The grep minus the import line. Plus the same 4 inlined `NOT IN (SELECT … FROM blocked_users …)` subqueries. Was 14 + 4 |
| Admin routes | 36 / 64 | 36 decorated routes in the four `admin*.py` routers; 64 routes across all routers that depend on `require_admin` (or the stream's admin check). Was 28 / 43 |
| Golden eval cases | 22 | 12 answer, 10 refuse-and-route. Unchanged |

## Component test counts

`def test_` counts with `grep -cE '^(async )?def test_'`. pytest's collected
count (`pytest --collect-only -q <files> | tail -1`, same environment as the
recorded run) is higher wherever a test is parametrized.

| Component | `def test_` | Collected | Files |
|---|---|---|---|
| AI vision pipeline | 10 / 28 | 10 / 28 | The October four files: `test_ai.py` 1, `test_ai_service.py` 4, `test_ai_object_key_ownership.py` 2, `test_ai_soft_item.py` 3 = 10. Plus `test_ai_restricted.py` 13 and `test_ai_short_title.py` 5 = 28 |
| Knowledge system | 116 | 121 | `test_knowledge_{answer,ask_endpoint,eval_seed,hybrid_path,ingestion,log_retention,models,retrieval}.py` (20+20+15+7+19+1+21+13). `test_knowledge_hybrid_path.py` (7) is new and covers the embedding, rank-fusion, floor, fallback and daily-ceiling code with Voyage stubbed |
| Coordinate privacy | 10 | 15 | `test_coordinate_privacy.py` |
| Payment path | 98 / 124 | 102 / 128 | `test_stripe_service.py` 38, `test_stripe_webhooks.py` 22, `test_pending_payment_sweeper.py` 8, `test_post_window_sweeper.py` 23, `test_stripe_customer.py` 4, `test_stripe_billing.py` 3 = 98. Plus `test_claim_deferred_intent.py` 11, `test_claim_fees.py` 10, `test_curbside_sweeper.py` 5 = 124 |
| Admin API and Sentry watcher | 153 | 155 | `test_admin_*.py` (12 files, three of them new since October: `_alert_emails` 10, `_complaints` 20, `_health_labels` 1) + `test_watcher.py` 21 |
| Trust and safety | 201 | 230 | `test_trust_service.py` 14, `test_strike.py` 10, `test_dispute_suspension.py` 8, `test_blocks.py` 35, `test_scam_detection.py` 50, `test_scam_wiring.py` 21, `test_credits_devicecheck.py` 23, `test_devicecheck_service.py` 17, `test_credits_giveaway.py` 23 |
| Private photo access | 26 | 26 | `test_signed_photo_reads.py`, `test_r2_delete.py` |
| Support agent | 275 | 363 | `backend/tests/agents/` (17 test files), run against a fake model (`fake_model.py`) |

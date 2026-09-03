# Repository metrics — commands and outputs

**Source repository:** `zelbi.ai` (private)
**Branch:** `master` · **HEAD:** `3413d028b5abd5163a820790c4fe8d9b0c82f922`
**Re-run:** 2026-09-03, macOS (Darwin 25.5.0), working directory = repository root.

Every number in this repository's documents traces to a row here, to
`pytest-summary-2026-09-03.txt`, to `eval-run-2026-09-03.md`, or to a
Fact-ID in the project's fact pack (a private document; Fact-IDs are cited
so Nick can resolve them on request). Nothing is quoted from memory.

## Verbatim session

```
$ git rev-list --count HEAD
1688

$ git rev-parse HEAD
3413d028b5abd5163a820790c4fe8d9b0c82f922

$ git rev-parse --abbrev-ref HEAD
master

$ git log --format=%ad --date=short | sort -u | wc -l
     127

$ git log --reverse --format=%ad --date=short | head -1
2026-04-09

$ git log -1 --format=%ad --date=short
2026-09-03

$ git log --format=%an | sort -u
nickbroyzer

$ find mobile/app -name '*.tsx' -not -name '_layout.tsx' | wc -l
      36

$ find mobile/app -name '*.tsx' | wc -l
      41

$ ls backend/app/routers/*.py | grep -v __init__ | wc -l
      16

$ ls backend/app/services/*.py | wc -l
      14

$ ls backend/app/jobs/run_*.py | wc -l
       4

$ ls backend/migrations/versions/*.py | wc -l
      44

$ ls backend/tests/test_*.py | wc -l
      55

$ ls -d .github
ls: .github: No such file or directory

$ grep -ril 'row level security\|ENABLE ROW LEVEL' backend/migrations/versions | wc -l
       0
```

## What each number means, and its counting method

| Metric | Value | Method / caveat | Fact-ID |
|---|---|---|---|
| Commits on `master` | 1,688 | `git rev-list --count HEAD` after `--unshallow`. Not 1,689 — that figure counted co-author trailer lines, not commits. | Z-001 |
| Distinct Git authors, full history | 1 (`nickbroyzer`) | Sole **human** code author. Commits carry AI-assistant co-author trailers; Nick directed, reviewed, and released every change. | Z-002 |
| Active development days | 127 | Distinct git author dates, 2026-04-09 → 2026-09-03 (147 calendar days). "Five months" is a round-up; say "under five months" or give the dates. | Z-003 |
| Mobile route screens | 36 | `mobile/app/**/*.tsx` excluding `_layout.tsx`. 41 files including layouts. | A-001 |
| Backend routers | 16 | `backend/app/routers/*.py` excluding `__init__.py`. | A-002 |
| Backend service modules | 14 | `backend/app/services/*.py`, plus the `knowledge/` package (counted separately). | A-002 |
| Job entrypoints | 4 runner scripts / 6 job modules | `run_*.py` = 4 cron entrypoints; the job modules they invoke (`listing_expiry`, `pending_payment_sweeper`, `pickup_reminder`, `post_window_sweeper`, `recommendation_scan`, `saved_deadline_scan`) = 6. Both counts are stated because the two methods differ. | A-002 |
| Alembic revisions | 44 | `backend/migrations/versions/*.py`, single root. | A-003 |
| Backend test **files** | 55 | `test_*.py` only. A count including `conftest.py` and `__init__.py` gives 57. Not a resume number. | T-003 |
| Backend tests collected & passed | 751 | See `pytest-summary-2026-09-03.txt`. Always "751 **backend** tests" — mobile and web have none. | T-001, T-004 |
| RLS statements in migrations | 0 | Row-level security is enabled as unversioned Supabase **dashboard** state, not as owned migration code. Claim it only as "Supabase Auth with row-level security enabled". | A-004 |
| CI workflow | absent | No `.github/` directory at this commit. "Every change was test-gated" is a prohibited claim; the suite was run manually at session close. | A-012, T-005 |

## Component test counts (`def test_` basis)

Counted with `grep -c '^def test_\|^async def test_'`, which is the basis the
resume uses. pytest's own collected count is higher wherever a test is
parametrized; both are given where they differ.

| Component | `def test_` | Collected | Files |
|---|---|---|---|
| Knowledge system | 108 | 113 | `test_knowledge_{answer,ask_endpoint,eval_seed,ingestion,models,retrieval}.py` (20+20+15+19+21+13) |
| AI vision pipeline | 21 | 21 | `test_ai.py` 6, `test_ai_service.py` 8, `test_ai_object_key_ownership.py` 4, `test_ai_soft_item.py` 3 |
| Coordinate privacy | 10 | 15 | `test_coordinate_privacy.py` |
| Payment path | 59 + a money subset of `test_claims.py` | — | `test_stripe_service.py` 12, `test_stripe_webhooks.py` 15, `test_pending_payment_sweeper.py` 6, `test_post_window_sweeper.py` 19, `test_stripe_customer.py` 4, `test_stripe_billing.py` 3. Stated as "~60". |
| Blocking | 37 + 8 | — | `test_blocks.py` 37, `test_messages.py` 8 |

The knowledge figure is the one place two published numbers exist. **108** is
the `def test_` count and is what the resume says; **113** is what pytest
collects once parametrized cases expand. They describe the same six files at
the same commit.

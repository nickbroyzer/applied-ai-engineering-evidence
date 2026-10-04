# Résumé V8 numbers, refreshed — 2026-10-03

Every number in résumé V8, re-derived at Zelbi `8875721`
(`88757212b5ea2395913cee61d81b05822818484a`). Commands and their verbatim
output are in [`repo-metrics-2026-10-03.md`](repo-metrics-2026-10-03.md); the
test run is in [`pytest-summary-2026-10-03.txt`](pytest-summary-2026-10-03.txt).

**Ruling applied (O9, B1).** On the résumé, only the big numbers change
(commits, tests, screens, admin routes, payment tests), and the vision bullet
drops its count. The wording stays as written. Where a kept phrase is narrower
in fact than in words, the scope is stated in [`../LEDGER.md`](../LEDGER.md),
and the right column here says so.

| Résumé V8 | Refreshed value | Basis | Résumé action |
|---|---|---|---|
| 2,107 commits | **2,122** | `git rev-list --count HEAD` | update |
| 1,300 backend tests passing | **1,265** | `1265 passed`, exit 0, clean checkout, network blocked (1,217 `def test_`) | update |
| 40 app screens | **38** | `mobile/app/**/*.tsx` excluding `_layout.tsx` (43 with layouts) | update |
| "solo in six months" | 2026-04-09 → 2026-10-03, 177 days | first and last commit dates | keep wording; literally true from 2026-10-09 |
| B1: 21 failure-mode tests | 10 tests across 4 files | `test_ai{,_service,_object_key_ownership,_soft_item}.py` | **drop the count** |
| B2: 22-case leak-probe set | 22 cases: 12 answer, 10 adversarial; 22/22, 0 leaks, text-only | golden set and recorded runs | keep wording; scope in LEDGER |
| B2: daily embedding cap | 1,000 questions per UTC day | `VOYAGE_DAILY_CEILING`, counted from the query log | no number on the résumé |
| B3: 60+ tests | **118** across nine files (122 collected); 92 in the six files published in September | component table | update, e.g. "110+" |
| B5: 127-listing recompute | 127 | internal docs only (L-004) | unchanged |
| B5: 15 tests | 15 collected (10 `def test_`) | `test_coordinate_privacy.py` | unchanged |
| B6: 30 admin routes | **28** in the four admin routers; 43 behind the admin check | route grep | update to 28, or "40+" if counting every admin-gated route |
| B6: live event stream | SSE polled every 2 s; no client yet | `routers_watcher.py:348-360` | keep wording; scope in LEDGER |
| B6: 120+ tests | 122 (124 collected) | `test_admin_*.py` + `test_watcher.py` | unchanged |
| B7: credits gated by Apple DeviceCheck | giveaway and invite credits; referral credits are not gated | `claims.py:436-440` | keep wording; scope in LEDGER |
| B7: 190+ tests | 199 (219 collected) | nine files, listed in repo-metrics | unchanged |
| Construction: "(45 tests)" | 45, on the Flask operations platform | N-001, AI-008 | move to the dashboard clause |

Numbers in this repository but not on the résumé, for reference: 564 numbered
decisions (48 published), sessions numbered through 473, 61 Alembic revisions,
22 routers, 25 service modules, 109 knowledge tests (114 collected), 26 private
photo tests.

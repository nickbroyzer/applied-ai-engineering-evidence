# Résumé V8 numbers, final wording — 2026-10-03

Every number in the final résumé V8, re-derived at Zelbi `8875721`
(`88757212b5ea2395913cee61d81b05822818484a`). Commands and their verbatim
output are in [`repo-metrics-2026-10-03.md`](repo-metrics-2026-10-03.md); the
test run is in [`pytest-summary-2026-10-03.txt`](pytest-summary-2026-10-03.txt).
Each line is mapped to its evidence in [`../LEDGER.md`](../LEDGER.md).

| Final résumé wording | Value here | Basis | Before the refresh |
|---|---|---|---|
| 2,122 commits | 2,122 | `git rev-list --count HEAD` | 2,107 |
| 1,265 backend tests passing | 1,265 | `1265 passed`, exit 0, clean checkout, network blocked (1,217 `def test_`) | 1,300 |
| 38 app screens | 38 | `mobile/app/**/*.tsx` excluding `_layout.tsx` (43 with layouts) | 40 |
| "solo in six months" | 2026-04-09 → 2026-10-03, 177 days | first and last commit dates | unchanged wording |
| "nearly 20 years in business" | January 2007 → December 2025, close to 19 years | earlier-career dates (Fact-IDs E-005a, E-007a/b, E-008) | "running businesses" |
| B1 vision pipeline: no test count | 10 tests across 4 files | `test_ai{,_service,_object_key_ownership,_soft_item}.py` | (21 failure-mode tests) |
| B2: 22-case leak-probe set | 22 cases: 12 answer, 10 adversarial; 22/22, 0 leaks, text-only | golden set and recorded runs | unchanged |
| B2: daily embedding cap | 1,000 questions per UTC day | `VOYAGE_DAILY_CEILING`, counted from the query log | no number on the résumé |
| B3: (110+ tests) | 118 (122 collected) | nine payment test files, listed in repo-metrics | (60+ tests) |
| B5: 127-listing recompute | 127 | internal docs only (L-004) | unchanged |
| B5: (15 tests) | 15 collected (10 `def test_`) | `test_coordinate_privacy.py` | unchanged |
| B6: 40+ admin routes | 43 | routes depending on the admin check across all routers; 28 of them in the four admin routers | 30 admin routes |
| B6: live event stream | SSE polled every 2 s; no client yet | `routers_watcher.py:348-360` | unchanged; scope in LEDGER |
| B6: (120+ tests) | 122 (124 collected) | `test_admin_*.py` + `test_watcher.py` | unchanged |
| B7: credits gated by Apple DeviceCheck | giveaway and invite credits; referral credits are not gated | `claims.py:436-440` | unchanged; scope in LEDGER |
| B7: (190+ tests) | 199 (219 collected) | nine files, listed in repo-metrics | unchanged |
| Construction: (45 tests) on the dashboard clause | 45, on the Flask operations platform | N-001, AI-008 | attached to the ERPNext clause |
| Skills: structured JSON outputs | JSON requested, parsed and Pydantic-validated | `ai-boundary.md` §five stages | "structured outputs" |

Numbers in this repository but not on the résumé, for reference: 564 numbered
decisions (48 published), sessions numbered through 473, 61 Alembic revisions,
22 routers, 25 service modules, 109 knowledge tests (114 collected), 26 private
photo tests.

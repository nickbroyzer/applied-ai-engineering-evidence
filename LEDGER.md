# Claim-to-proof ledger

One row per sentence of résumé V8: **claim → where it is proven here → the test
→ the decision that governs it → the verification record.** Numbers are at Zelbi
`8875721`, re-derived 2026-10-03 in
[`verification/repo-metrics-2026-10-03.md`](verification/repo-metrics-2026-10-03.md)
and [`verification/pytest-summary-2026-10-03.txt`](verification/pytest-summary-2026-10-03.txt).
Quoted résumé text is the final V8 wording. Every number in it, with its basis
and its value before the refresh, is in
[`verification/resume-v8-numbers-2026-10-03.md`](verification/resume-v8-numbers-2026-10-03.md).

Then the reverse check: every folder in this repository must be reachable from
at least one row.

Fact-IDs (`Z-001`, `AI-002`, …) refer to the project's private fact pack, where
each carries its own primary source. They are cited so any row can be resolved
back to a source document on request.

**Flags.** A row marked **⚑** is a claim this repository cannot prove, or proves
only in a narrower form than the résumé words suggest. The row says which.
Where a row says **described, not published**, the code exists in a private
repository and only a description of it is here.

---

## Header

| Claim | Source | Note |
|---|---|---|
| Applied AI Engineer · LLM products, end to end | the bullets below | a title, proven by the rows that follow |
| Founder, Zelbi · zelbi.ai | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) | Z-001 |
| github.com/nickbroyzer/applied-ai-engineering-evidence | this repository | — |
| Seattle Metro, WA · linkedin.com/in/nickbroyzer · U.S. Citizen · English / Russian | — | **⚑** Personal record; not a code claim, and nothing here proves it. Verifiable on request. |

## Summary

| Claim | Proven at | Verification |
|---|---|---|
| "Builds production LLM systems end to end: vision pipelines, hybrid search with evals, payments, trust and safety." | vision: [`ai-boundary.md`](02-architecture/ai-boundary.md) · hybrid search: [`hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md) · evals: [`runnable/knowledge-eval/`](runnable/knowledge-eval/) · payments: [`money-path.md`](02-architecture/money-path.md) · trust and safety: [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) | **⚑** "hybrid search with evals": the evals are real and pass 22/22, but they run text-only. No eval and no test exercises the hybrid ranking ([LIMITATIONS](LIMITATIONS.md) §Help search). |
| "Built Zelbi solo in six months by directing AI coding assistants" | [`05-process/`](05-process/) · [`LIMITATIONS.md`](LIMITATIONS.md) §Authorship | **Solo:** `git log --format=%an \| sort -u` gives one author; commits carry AI co-author trailers. **Six months:** first commit 2026-04-09, last at this refresh 2026-10-03, which is 177 days. **⚑** Wording kept by ruling: it is literally true from 2026-10-09. |
| "nearly 20 years in business before that" | — | **⚑** Not a code claim. Fact-IDs E-005a, E-007a/b, E-008. The three earlier-career roles run from January 2007 to December 2025, close to 19 years. |

## Skills

| Skill | Proven at | Note |
|---|---|---|
| **AI** — Anthropic API (Claude), vision | [`ai-boundary.md`](02-architecture/ai-boundary.md), [`code/ai_service/`](code/ai_service/) | — |
| structured JSON outputs | [`ai-boundary.md`](02-architecture/ai-boundary.md) §five stages · [`code/ai_service/ai_service.py`](code/ai_service/ai_service.py) | The model is asked for JSON, which is fence-stripped, parsed and Pydantic-validated. The Anthropic structured-output API feature is not used and not claimed ([LIMITATIONS](LIMITATIONS.md) §AI path). |
| Pydantic validation | [`code/ai_service/ai_service.py`](code/ai_service/ai_service.py) | — |
| Voyage embeddings | [`code/knowledge/embeddings.py`](code/knowledge/embeddings.py) · [`hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md) | **⚑** Untested; the recorded evals do not exercise it. |
| hybrid retrieval (rank fusion) | [`code/knowledge/retrieval.py`](code/knowledge/retrieval.py) — `RRF_K = 60` at :51, fusion at :275-295 | **⚑** Untested, as above. |
| golden-set evals | [`runnable/knowledge-eval/`](runnable/knowledge-eval/) · [`code/knowledge/retrieval_eval.py`](code/knowledge/retrieval_eval.py), [`answer_eval.py`](code/knowledge/answer_eval.py) | 22/22, 0 leaks, recorded 2026-10-03, text-only |
| MCP | [`tooling/README.md`](tooling/README.md) | **⚑** Pointer only. Servers are configured in the Claude Code environment; no file here shows MCP work. |
| Claude Code subagents and hooks | [`tooling/agents/`](tooling/agents/), [`tooling/hooks/`](tooling/hooks/) · [`05-process/enforcement-hooks.md`](05-process/enforcement-hooks.md) | September snapshot, unchanged |
| **Engineering** — Python, FastAPI | [`code/`](code/), every backend subfolder | — |
| Flask | [`system-overview.md`](02-architecture/system-overview.md) §A second system | **⚑** Described, not published. No Flask code is here. |
| TypeScript, React Native / Expo | [`code/mobile/`](code/mobile/) · [`code/credits_devicecheck/`](code/credits_devicecheck/) (`index.ts`, `src_ZelbiDeviceCheckModule.ts`, `mobile_utils_deviceCheck.ts`, `expo-module.config.json`) | No automated mobile tests ([LIMITATIONS](LIMITATIONS.md)) |
| PostgreSQL / Supabase | [`data-and-migrations.md`](02-architecture/data-and-migrations.md) · [`code/database/database.py`](code/database/database.py) | RLS is dashboard state, claimed only as enabled |
| SQLAlchemy | [`code/database/`](code/database/) · [`data-and-migrations.md`](02-architecture/data-and-migrations.md) | 61 Alembic revisions |
| pytest | [`verification/`](verification/) | 1,265 passed, clean checkout, network blocked |
| **Infrastructure** — Stripe | [`money-path.md`](02-architecture/money-path.md) · [`code/payments/`](code/payments/) | — |
| Sentry | [`code/database/observability.py`](code/database/observability.py) · [`code/admin_ops/routers_watcher.py`](code/admin_ops/routers_watcher.py) | — |
| Railway | [`code/jobs/`](code/jobs/), the cron runners it schedules · [`system-overview.md`](02-architecture/system-overview.md) | Platform configuration is not in any file here |
| Cloudflare R2 | [`code/photo_access/cloudflare_r2.py`](code/photo_access/cloudflare_r2.py) · [`private-photo-access.md`](01-product-logic/private-photo-access.md) | — |
| Twilio, Retell AI, Gmail Pub/Sub | [`system-overview.md`](02-architecture/system-overview.md) §A second system | **⚑** Described, not published. The description says "voice receptionist over SIP" and "push-subscription webhook". It does not name Retell AI or Gmail Pub/Sub. Twilio is named only for the paused voice-bridge exploration (§Other systems). |
| Apple DeviceCheck | [`device-check-credits.md`](01-product-logic/device-check-credits.md) · [`code/credits_devicecheck/`](code/credits_devicecheck/) | — |

## Zelbi — scale line

"Sole engineer, directing AI coding assistants · 2,122 commits · 1,265 backend
tests passing · 38 app screens"

| Claim | Proven at | Verification |
|---|---|---|
| Sole engineer, directing AI coding assistants | [`05-process/`](05-process/) · [`LIMITATIONS.md`](LIMITATIONS.md) §Authorship | `git log --format=%an \| sort -u` → one author |
| 2,122 commits | [`system-overview.md`](02-architecture/system-overview.md) | `git rev-list --count HEAD` → `2122` |
| 1,265 backend tests passing | [`code/`](code/) · [`verification/netblock.py`](verification/netblock.py) | [pytest-summary](verification/pytest-summary-2026-10-03.txt): `1265 passed`, exit 0, clean checkout, network blocked (1,217 `def test_`) |
| 38 app screens | [`system-overview.md`](02-architecture/system-overview.md) | `mobile/app/**/*.tsx` excluding `_layout.tsx` → `38` |

## Zelbi — bullet 1: the vision pipeline

"Claude vision pipeline (Anthropic API, Pydantic): one photo becomes two
validated listing drafts; fence-tolerant JSON parsing, output allowlists,
per-request Cloudflare R2 authorization."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| One photo → two validated listing drafts | [`ai-boundary.md`](02-architecture/ai-boundary.md) | [`test_ai_service.py`](code/ai_service/test_ai_service.py) `…returns_ab_pair_and_confidence`, [`test_ai.py`](code/ai_service/test_ai.py) `…returns_ab_shape` | [D18](03-decisions/ai/D18.md), [D122](03-decisions/ai/D122.md), [D438](03-decisions/ai/D438.md) | AI-001 |
| Fence-tolerant JSON parsing | [`ai-boundary.md`](02-architecture/ai-boundary.md) §five stages | **⚑** no dedicated test | — | AI-002 |
| Output allowlists | same, stage 4 | `…invalid_category_in_option_a`, `…invalid_confidence_rejected` | — | AI-002 |
| Per-request Cloudflare R2 authorization | [`code/ai_service/routers_ai.py`](code/ai_service/routers_ai.py) | [`test_ai_object_key_ownership.py`](code/ai_service/test_ai_object_key_ownership.py) (2) | — | AI-003 |
| Tests overall | [`code/ai_service/`](code/ai_service/) | 4 files, 10 tests | — | The résumé states no count (ruling B1). It said 21 before the refresh; `b6ced95` deleted the readability endpoint and its 11 tests. |

## Zelbi — bullet 2: hybrid search

"Hybrid search: Voyage embeddings and PostgreSQL full-text merged by reciprocal
rank fusion, SQL access filters on both paths, a daily embedding cap, and cited
answers built without an LLM (22-case leak-probe set)."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Voyage embeddings and PostgreSQL full-text merged by reciprocal rank fusion | [`hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md) · [`retrieval.py`](code/knowledge/retrieval.py) :51, :275-295 · [`embeddings.py`](code/knowledge/embeddings.py) | **⚑** none. No test exercises embedding or fusion | D537 (cited, not published) | code only |
| SQL access filters on both paths | [`retrieval.py`](code/knowledge/retrieval.py) `_visibility_filters` :95-118, applied at :166 (full-text), :191 (keyword), :205 (vector) | [`test_knowledge_retrieval.py`](code/knowledge/test_knowledge_retrieval.py), [`test_knowledge_models.py`](code/knowledge/test_knowledge_models.py): text paths and constraints only | — | R-001, R-003 |
| A daily embedding cap | [`retrieval.py`](code/knowledge/retrieval.py) `VOYAGE_DAILY_CEILING = 1000` :58; alerts [`routers_knowledge.py`](code/knowledge/routers_knowledge.py) :96-119 | **⚑** none | [D538](03-decisions/ai/D538.md) | Counts logged questions, a conservative upper bound on query embeddings ([LIMITATIONS](LIMITATIONS.md)) |
| Cited answers built without an LLM | [`answer.py`](code/knowledge/answer.py) · [`ai-boundary.md`](02-architecture/ai-boundary.md) §Why deterministic for Help | [`test_knowledge_answer.py`](code/knowledge/test_knowledge_answer.py) (20), [`test_knowledge_ask_endpoint.py`](code/knowledge/test_knowledge_ask_endpoint.py) (20) | — | runnable: `generation_model=deterministic-composer-v1` |
| "(22-case leak-probe set)" | [`runnable/knowledge-eval/`](runnable/knowledge-eval/) · [`test_knowledge_eval_seed.py`](code/knowledge/test_knowledge_eval_seed.py) (15) | the eval itself | — | [runnable README](runnable/knowledge-eval/README.md): `22 total, 22 passed`, `leak failures: 0`, exit 0. **Wording kept by ruling; exact scope:** 22 golden cases, of which **10** are adversarial leak probes and 12 are answers graded for leaks. Text-only retrieval. |
| Knowledge tests overall | [`code/knowledge/`](code/knowledge/) | 7 files | — | 109 `def test_` / 114 collected |

## Zelbi — bullet 3: the Stripe claim-fee lifecycle

"Stripe claim-fee lifecycle: authorization, capture, void, refund, webhooks and
scheduled reconciliation; adopts provider-confirmed captures instead of
recapturing and recovers holds when webhooks are lost (110+ tests)."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Authorization, capture, void, refund, webhooks, scheduled reconciliation | [`money-path.md`](02-architecture/money-path.md) · [`marketplace-state-machine.md`](01-product-logic/marketplace-state-machine.md) · [`failure-state-matrix.md`](01-product-logic/failure-state-matrix.md) · sweepers driven by [`code/jobs/run_frequent_jobs.py`](code/jobs/run_frequent_jobs.py) | [`code/payments/`](code/payments/) | [D23](03-decisions/money/D23.md), [D211](03-decisions/money/D211.md), [D212](03-decisions/money/D212.md), [D217](03-decisions/money/D217.md), [D218](03-decisions/money/D218.md) | repo-metrics component table |
| Adopts provider-confirmed captures instead of recapturing | [`money-path.md`](02-architecture/money-path.md) | [`test_stripe_service.py`](code/payments/test_stripe_service.py) `test_capture_adopts_already_captured_intent_without_recapturing` (:188) | [D261](03-decisions/money/D261.md) | — |
| Recovers holds when webhooks are lost | [`04-troubleshooting/04`](04-troubleshooting/04-false-charge-message.md) | [`test_pending_payment_sweeper.py`](code/payments/test_pending_payment_sweeper.py) `test_live_hold_is_promoted_not_cancelled` (:148) | — | commit `14243ef` |
| "(110+ tests)" | [`code/payments/`](code/payments/) | 9 files | — | **118** `def test_` across nine files (122 collected), listed in repo-metrics. The six files published in September hold 92. |

## Zelbi — bullet 4: production debugging

"Production debugging (Sentry, source, git history): prepared-statement
collisions behind Supabase's transaction pooler, fixed at the engine layer;
random sign-outs traced to two separate auth causes."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Sentry, source, git history | [`04-troubleshooting/`](04-troubleshooting/) (whole folder) | — | [D274](03-decisions/ops/D274.md) | commit hashes in each write-up |
| Prepared-statement collisions behind the transaction pooler, fixed at the engine layer | [`04-troubleshooting/01`](04-troubleshooting/01-prepared-statements-vs-pooler.md) · [`code/database/database.py`](code/database/database.py) | — (not unit-testable; stated there) | — | commit `884af15` |
| Random sign-outs traced to two separate auth causes | [`04-troubleshooting/02`](04-troubleshooting/02-two-cause-auth-reset.md) · [`code/mobile/store_auth.ts`](code/mobile/store_auth.ts), [`utils_supabase.ts`](code/mobile/utils_supabase.ts) | — | [D276](03-decisions/ops/D276.md), [D277](03-decisions/ops/D277.md) | commit `5d02d80` |

## Zelbi — bullet 5: location privacy

"Location privacy: found the original scheme reversible and rebuilt it with
HMAC-keyed per-listing coordinate fuzzing, exact location released only after
payment authorization, and a 127-listing recompute under secret rotation (15
tests)."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Found the original scheme reversible | [`04-troubleshooting/05`](04-troubleshooting/05-location-scheme-reversal.md) | — | [D323](03-decisions/privacy/D323.md) | commit `26eaa9b` · L-003 |
| HMAC-keyed per-listing coordinate fuzzing | [`location-privacy-design.md`](01-product-logic/location-privacy-design.md) · [`code/coordinate_privacy/coordinate_privacy.py`](code/coordinate_privacy/coordinate_privacy.py) | [`test_coordinate_privacy.py`](code/coordinate_privacy/test_coordinate_privacy.py) `test_distance_in_range`, `test_seeded_stability`, `test_nearby_returns_approx_not_true_coords` | [D125](03-decisions/privacy/D125.md), [D137](03-decisions/privacy/D137.md), [D323](03-decisions/privacy/D323.md) | L-001 |
| Exact location released only after payment authorization | [`location-privacy-design.md`](01-product-logic/location-privacy-design.md) | `test_resolver_claim_holder_reveal_status`, `…_non_reveal_status`, `test_resolver_stranger_gets_approx` | [D320](03-decisions/privacy/D320.md), [D321](03-decisions/privacy/D321.md), [D322](03-decisions/privacy/D322.md) | L-002 |
| 127-listing recompute under secret rotation | [`04-troubleshooting/05`](04-troubleshooting/05-location-scheme-reversal.md) | — | [D323](03-decisions/privacy/D323.md) | L-004; internal docs only, no script output is published |
| "(15 tests)" | [`code/coordinate_privacy/`](code/coordinate_privacy/) | 1 file | — | 10 `def test_` / **15 collected** (parametrised) |

## Zelbi — bullet 6: admin API and ops console

"Admin API and ops console: 40+ admin routes for claims, disputes, rule flags,
the Stripe money path and account actions with emailed notices; Sentry webhook
with HMAC verification and a live event stream (120+ tests)."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| "40+ admin routes" | [`admin-and-ops.md`](02-architecture/admin-and-ops.md) §The routes · [`code/admin_ops/`](code/admin_ops/) `routers_admin*.py`, [`routers_watcher.py`](code/admin_ops/routers_watcher.py), [`routers_events.py`](code/admin_ops/routers_events.py) | [`test_admin_authorization.py`](code/admin_ops/test_admin_authorization.py) | — | **43** routes depend on the admin check across all routers (repo-metrics M15). 28 of them are in the four admin routers; the other 15 are the watcher, user-event, growth-source and CX-knowledge routes. The areas the sentence names are covered by the 28. |
| Claims, disputes, rule flags, the Stripe money path, account actions | [`admin-and-ops.md`](02-architecture/admin-and-ops.md) route table | `test_admin_{claims,disputes,flags,money,actions,listings,notes,health}.py` | [D324](03-decisions/money/D324.md), [D533](03-decisions/money/D533.md) | Disputes start by email (D533); no code path creates a dispute row ([LIMITATIONS](LIMITATIONS.md)) |
| With emailed notices | [`admin-and-ops.md`](02-architecture/admin-and-ops.md) §Emailed notices · [`code/admin_ops/standing_notices.py`](code/admin_ops/standing_notices.py) | `test_admin_{actions,disputes,flags,listings}.py` | — | 7 routes send email |
| Refund before the ruling | [`routers_admin.py`](code/admin_ops/routers_admin.py) :218-233 · [`money-path.md`](02-architecture/money-path.md) | [`test_admin_disputes.py`](code/admin_ops/test_admin_disputes.py) | [D324](03-decisions/money/D324.md) | **⚑** The refund-failure path has no test |
| Sentry webhook with HMAC verification | [`routers_watcher.py`](code/admin_ops/routers_watcher.py) :174-202 | [`test_watcher.py`](code/admin_ops/test_watcher.py) `test_webhook_400_when_signature_wrong`, `…_signature_missing`, `…_secret_unset` | — | No replay protection ([LIMITATIONS](LIMITATIONS.md)) |
| "a live event stream" | [`routers_watcher.py`](code/admin_ops/routers_watcher.py) :348-360 | `test_stream_401_*` (3) | — | **Wording kept by ruling; exact scope:** Server-Sent Events backed by a 2-second database poll. No client opens it yet, and only the 401 cases are tested. |
| "(120+ tests)" | [`code/admin_ops/`](code/admin_ops/) | 10 files | — | **122** `def test_` / 124 collected |
| Ops console | [`admin-and-ops.md`](02-architecture/admin-and-ops.md) §The console itself | — | — | **⚑** Described, not published. It is a single HTML file carrying project identifiers ([MANIFEST](MANIFEST.md) §1.6). |

## Zelbi — bullet 7: trust and safety

"Trust and safety: reputation model with strikes and healing, blocking enforced
across listings, messages and claims, rule-based scam detection, and credits
gated by Apple DeviceCheck through a native Swift module (190+ tests)."

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Reputation model with strikes and healing | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) · [`code/trust/trust_service.py`](code/trust/trust_service.py), [`strike_service.py`](code/trust/strike_service.py) | [`test_trust_service.py`](code/trust/test_trust_service.py) (14), [`test_strike.py`](code/trust/test_strike.py) (10), [`test_dispute_suspension.py`](code/trust/test_dispute_suspension.py) (8), [`test_claim_score_delta.py`](code/trust/test_claim_score_delta.py) | [D21](03-decisions/trust/D21.md), [D182](03-decisions/trust/D182.md), [D183](03-decisions/trust/D183.md), [D299](03-decisions/trust/D299.md) | constants published verbatim ([MANIFEST](MANIFEST.md) §1.2) |
| Blocking enforced across listings, messages and claims | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) §Blocking · [`code/trust/block_service.py`](code/trust/block_service.py) | [`test_blocks.py`](code/trust/test_blocks.py) (35) | [D318](03-decisions/trust/D318.md), [D322](03-decisions/privacy/D322.md) | 14 helper call sites (listings 3, claims 7, messages 2, sweeper 2) plus 4 inlined feed subqueries. The résumé states no count ([LIMITATIONS](LIMITATIONS.md)) |
| Rule-based scam detection | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) §The message guard · [`code/message_guard/scam_detection.py`](code/message_guard/scam_detection.py) | [`test_scam_detection.py`](code/message_guard/test_scam_detection.py) (48), [`test_scam_wiring.py`](code/message_guard/test_scam_wiring.py) (21) | [D225](03-decisions/trust/D225.md), [D226](03-decisions/trust/D226.md), [D232](03-decisions/trust/D232.md), [D264](03-decisions/trust/D264.md), [D270](03-decisions/trust/D270.md), [D272](03-decisions/trust/D272.md) | Rule table withheld ([MANIFEST](MANIFEST.md) §1.1). Active rules are 2, 3 and 6. |
| "credits gated by Apple DeviceCheck through a native Swift module" | [`device-check-credits.md`](01-product-logic/device-check-credits.md) · [`ios_ZelbiDeviceCheckModule.swift`](code/credits_devicecheck/ios_ZelbiDeviceCheckModule.swift) · [`devicecheck_service.py`](code/credits_devicecheck/devicecheck_service.py) · [`credit_service.py`](code/credits_devicecheck/credit_service.py) | [`test_credits_devicecheck.py`](code/credits_devicecheck/test_credits_devicecheck.py) (23), [`test_devicecheck_service.py`](code/credits_devicecheck/test_devicecheck_service.py) (17), [`test_credits_giveaway.py`](code/credits_devicecheck/test_credits_giveaway.py) (23) | [D542](03-decisions/trust/D542.md), [D544](03-decisions/trust/D544.md); D539, D543, D545, D549 cited | **Wording kept by ruling; exact scope:** giveaway and invite credits are gated; referral credits are not (`claims.py:436-440@8875721`, excerpt) |
| "(190+ tests)" | `code/trust/`, `code/message_guard/`, `code/credits_devicecheck/` | 9 files | — | **199** `def test_` / 219 collected (file list in repo-metrics) |

## Independent build — construction company

"AI Operations Platform + ERP Migration · Construction company · Mar – Apr 2026
· Pacific, WA". All code is private: **described, not published.**

| Claim | Proven at | Source | Note |
|---|---|---|---|
| "Claude classifier on live Gmail push events routing every inbound email to hot lead, warm lead, vendor or spam." | [`system-overview.md`](02-architecture/system-overview.md) §A second system ("a Claude classifier triages inbound mail through a push-subscription webhook") | N-001, AI-008; categories from the private fact pack | Described, not published. The four category names come from the fact pack, not from anything here. |
| "Added an AI chat that books appointments into Google Calendar, an AI voice receptionist," | same ("a public lead-capture chat that streams model replies and books appointments"; "a voice receptionist over SIP") | AI-009, AI-010 | Described, not published |
| "and an invoice approval queue (45 tests);" | same ("Vendor invoices that arrive by email wait in an approval queue…") | private repository `my-assistant`, `routes/invoices.py:240-283@a10aab6`: `approve_inbox_invoice` posts the invoice to job costs and marks the inbox item approved. Read 2026-10-03. | Described, not published |
| "moved the company onto ERPNext" | same ("a custom Frappe app with three tested doctypes and two migration engines") | N-002 | Described, not published |
| "(45 tests)", on the dashboard clause | same ("carrying a 45-test pytest suite") | N-001, AI-008 | The 45 tests belong to the Flask operations platform (the chat, receptionist and invoice queue), not to the ERPNext migration, which is where the parenthetical sat before the refresh. Described, not published. |

## Earlier career

Not code claims; nothing in this repository proves them. Private fact pack;
verifiable on request.

| Claim | Fact-ID |
|---|---|
| Herbella LLC, Apr 2013 – Dec 2025: five facilities, $1M+ capital projects, ~25% efficiency gain | E-005a, K-001, K-009 |
| Sr. Mortgage Consultant, Wells Fargo / Bank of America, Mar 2010 – May 2014: 900+ clients, $20M+ funded in 2010, top 10% (2010, 2012) | E-007a, E-007b, K-003 |
| United Financing LLC, Jan 2007 – Mar 2010: 15-person team, revenue +30% | E-008, K-005 |

---

## Reverse check: can every folder be reached from a row?

| Folder | Referenced by | Status |
|---|---|---|
| `01-product-logic/` | bullets 3, 5, 7; summary; skills | ✅ |
| `02-architecture/` | summary, scale line, bullets 1–3, 6, 7; skills; construction | ✅ |
| `03-decisions/ai/` | bullets 1, 2 | ✅ |
| `03-decisions/money/` | bullets 3, 6 | ✅ |
| `03-decisions/ops/` | bullet 4 | ✅ |
| `03-decisions/privacy/` | bullets 5, 7 | ✅ |
| `03-decisions/trust/` | bullet 7 | ✅ |
| `04-troubleshooting/` | bullets 3, 4, 5 | ✅ |
| `05-process/` | summary, scale line; skills | ✅ |
| `code/admin_ops/` | bullet 6; skills (Sentry) | ✅ |
| `code/ai_service/` | bullet 1; skills | ✅ |
| `code/coordinate_privacy/` | bullet 5 | ✅ |
| `code/credits_devicecheck/` | bullet 7; skills (Apple DeviceCheck, TypeScript) | ✅ |
| `code/database/` | bullet 4; skills | ✅ |
| `code/jobs/` | bullet 3 (scheduled reconciliation); skills (Railway) | ✅ |
| `code/knowledge/` | bullet 2; skills | ✅ |
| `code/message_guard/` | bullet 7 | ✅ |
| `code/mobile/` | bullet 4 (auth store, Supabase client); skills (TypeScript, React Native) | ⚠️ see below |
| `code/payments/` | bullet 3 | ✅ |
| `code/photo_access/` | skills (Cloudflare R2) | ⚠️ see below |
| `code/trust/` | bullet 7 | ✅ |
| `runnable/knowledge-eval/` | bullet 2; summary; skills | ✅ |
| `tooling/` | skills (MCP, subagents and hooks) | ✅ |
| `verification/` | scale line and every numeric row | ✅ |

**Two weak rows.**

- [`code/mobile/`](code/mobile/): bullet 4 cites two of its seven files. The
  other five (the message-guard client, push-tap routing, notification routing,
  listing coordinate handling, directions) are the client halves of claims
  proven on the backend, and no résumé sentence points at them directly. They
  are kept because there are **no automated mobile tests**, so reading the code
  is the only evidence available for the client.
- [`code/photo_access/`](code/photo_access/): no V8 bullet is about private
  photos. It is reached through the Cloudflare R2 skill and is kept as the
  evidence behind [`private-photo-access.md`](01-product-logic/private-photo-access.md).
  Bullet 1's "per-request Cloudflare R2 authorization" is a separate check, in
  [`code/ai_service/routers_ai.py`](code/ai_service/routers_ai.py).

**Rows dropped since September** because V8 no longer contains them:
- 100% customer-satisfaction ratings, three branches, CRM 15%;
- the tooling-project rows (nine subagents, the rule parser, the rules registry);
- Command Center, voice-bridge and ClawDeck;
- the legal-audit clause;
- client-reported arrival;
- the education line.

The evidence behind them is unchanged and is still described in
[`system-overview.md`](02-architecture/system-overview.md),
[`tradeoffs.md`](02-architecture/tradeoffs.md) and [`tooling/`](tooling/).

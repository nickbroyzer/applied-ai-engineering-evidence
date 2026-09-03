# Claim-to-proof ledger

One row per résumé sentence: **claim → where it is proven here → the test →
the decision that governs it → the verification record.**

Then the reverse check: every folder in this repository must be reachable from
at least one row.

Fact-IDs (`Z-001`, `AI-002`, …) refer to the project's private fact pack, where
each carries its own primary source. They are cited so any row can be resolved
back to a source document on request.

---

## Summary

| # | Claim | Fact-ID |
|---|---|---|
| S1 | Ships production software end to end | — |
| S2 | Sole human code author — 1,688 commits, 751 passing backend tests from a clean checkout | Z-001, Z-002, T-001 |
| S3 | Twelve years in regulated, transaction-heavy operations before software | E-016, K-009 |

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| **S1** — "ships production software end to end" | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) | whole suite | — | [repo-metrics](verification/repo-metrics-2026-09-03.md) |
| **S2a** — 1,688 commits | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) | — | — | [repo-metrics](verification/repo-metrics-2026-09-03.md) · `git rev-list --count HEAD` → `1688` |
| **S2b** — sole *human* code author, built with AI assistants under my direction | [`05-process/`](05-process/) (whole folder) | — | — | [repo-metrics](verification/repo-metrics-2026-09-03.md) · `git log --format=%an \| sort -u` → one author |
| **S2c** — 751 passing backend tests, clean checkout | [`code/`](code/) (all subfolders) | the suite itself | — | [pytest-summary](verification/pytest-summary-2026-09-03.txt) · `751 passed`, exit 0, network blocked |
| **S3** — twelve years pre-software | — (not a code claim) | — | — | Fact-IDs E-016, K-009 |

## Non-code claims (sourced outside this repository)

These rows are here so the reverse check is honest: nothing below is proven by
anything in this repository, and none of it should be read as if it were.

| Claim | Source | Note |
|---|---|---|
| **S3** — "Twelve years in regulated, transaction-heavy operations before software" | E-016, K-009 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| Herbella LLC — Founder · Head of Facility Design & Cultivation Operations — April 2013 – December 2025 | E-005a | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Designed, built, and operated five state-licensed controlled-environment agriculture facilities over twelve years in a volatile, consolidating industry." | K-001, K-009 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Led $1M+ per-site HVAC, electrical, mechanical, and structural capital projects; owned permitting, code compliance, and vendor and subcontractor negotiation." | K-001 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Improved operational efficiency ~25% across the facility portfolio." | K-001 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| Wells Fargo Home Mortgage / Bank of America — Home Mortgage Consultant → Sr. Mortgage Consultant — March 2010 – May 2014 | E-007a, E-007b | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Managed a 900+ client portfolio and $20M+ funded volume in 2010." | K-003 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Ranked Top 10% nationally by funded volume (2010, 2012); 100% customer-satisfaction ratings 2010–2013." | K-003 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Coordinated underwriting, processing, and closing across three branches." | K-003 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| United Financing LLC — Founder / Mortgage Broker — January 2007 – March 2010 | E-008 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Founded and ran a state-licensed mortgage brokerage with a 15-person team; owned P&L and compliance." | E-008, K-005 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Implemented CRM automation that cut document-processing time 15%." | K-005 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| "Built lender and referral partnerships that grew revenue 30%." | K-005 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |
| Education: "Coursework toward Applied Science degree, programming track — Bellevue College (formerly Bellevue Community College)" | ED-001 | Employment/education record; not a code claim. Private fact pack; verifiable on request. |

## Zelbi — bullet 1: architecture and scale

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| 36-screen React Native / Expo client | [`system-overview.md`](02-architecture/system-overview.md) | — (no mobile tests — [LIMITATIONS](LIMITATIONS.md)) | — | repo-metrics → `36` |
| 16-router FastAPI backend | [`system-overview.md`](02-architecture/system-overview.md) | — | — | repo-metrics → `16` |
| PostgreSQL / Supabase, 44 migrations | [`data-and-migrations.md`](02-architecture/data-and-migrations.md) | [`code/database/test_migrations_phase_9.py`](code/database/test_migrations_phase_9.py) | — | repo-metrics → `44` |
| Stripe payments | [`money-path.md`](02-architecture/money-path.md) | [`code/payments/`](code/payments/) — 6 files, 59 `def test_` | [D23](03-decisions/money/D23.md), [D217](03-decisions/money/D217.md), [D218](03-decisions/money/D218.md) | repo-metrics component table |
| Object storage, deployment platform | [`system-overview.md`](02-architecture/system-overview.md) | [`code/database/`](code/database/) | — | Fact-IDs A-006, A-007 |
| 751 backend tests, clean checkout, network blocked | [`verification/`](verification/) | the suite | — | [pytest-summary](verification/pytest-summary-2026-09-03.txt) + [`netblock.py`](verification/netblock.py) |

## Zelbi — bullet 2: the vision pipeline

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Photo → two validated listing drafts, constrained category / confidence / item-type | [`ai-boundary.md`](02-architecture/ai-boundary.md) | [`code/ai_service/test_ai_service.py`](code/ai_service/test_ai_service.py) (8), [`test_ai_soft_item.py`](code/ai_service/test_ai_soft_item.py) (3) | [D18](03-decisions/ai/D18.md), [D122](03-decisions/ai/D122.md), [D438](03-decisions/ai/D438.md) | Fact-ID AI-001 |
| Fence-tolerant JSON extraction | [`ai-boundary.md`](02-architecture/ai-boundary.md) §five stages | [`code/ai_service/test_ai_service.py`](code/ai_service/test_ai_service.py) | — | Fact-ID AI-002 |
| Pydantic validation | same | same | — | AI-002 |
| Independent allowlist enforcement | same, stage 4 | same | — | AI-002 |
| Per-request object-key authorization | [`ai-boundary.md`](02-architecture/ai-boundary.md) | [`code/ai_service/test_ai_object_key_ownership.py`](code/ai_service/test_ai_object_key_ownership.py) (4) | — | AI-003 |
| Provider-safe error mapping | same, stage 5 | [`code/ai_service/test_ai.py`](code/ai_service/test_ai.py) (6) | — | AI-002 |
| 21 tests across storage, provider, parsing, schema, authorization | [`code/ai_service/`](code/ai_service/) | 4 files | — | repo-metrics: 21 / 21 |

## Zelbi — bullet 3: determinism where a wrong answer is a safety problem

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Tier-aware policy retrieval-and-refusal system | [`ai-boundary.md`](02-architecture/ai-boundary.md) · **runnable**: [`runnable/knowledge-eval/`](runnable/knowledge-eval/) | 6 files | — (governing decision withheld; see [INDEX](03-decisions/INDEX.md)) | [runnable README](runnable/knowledge-eval/README.md) — `113 passed` |
| PostgreSQL full-text search | [`code/knowledge/retrieval.py`](code/knowledge/retrieval.py) | [`test_knowledge_retrieval.py`](code/knowledge/test_knowledge_retrieval.py) | — | Fact-ID R-001 |
| Filter-first SQL (visibility is a `WHERE` clause, not a post-filter) | [`ai-boundary.md`](02-architecture/ai-boundary.md) | [`test_knowledge_retrieval.py`](code/knowledge/test_knowledge_retrieval.py) | — | R-001, R-003 |
| Structural leak containment | [`data-and-migrations.md`](02-architecture/data-and-migrations.md) (check constraints) | [`test_knowledge_models.py`](code/knowledge/test_knowledge_models.py), [`test_knowledge_ingestion.py`](code/knowledge/test_knowledge_ingestion.py) | — | R-002, R-003 |
| Two-stage adversarial evaluation harness | [`code/knowledge/retrieval_eval.py`](code/knowledge/retrieval_eval.py), [`answer_eval.py`](code/knowledge/answer_eval.py) | [`test_knowledge_eval_seed.py`](code/knowledge/test_knowledge_eval_seed.py) (15) | — | R-004 |
| 22/22 golden cases, zero leak failures, at the audited commit | [`runnable/knowledge-eval/README.md`](runnable/knowledge-eval/README.md) | [`test_knowledge_answer.py`](code/knowledge/test_knowledge_answer.py), [`test_knowledge_ask_endpoint.py`](code/knowledge/test_knowledge_ask_endpoint.py) | — | runnable README — `22 total, 22 passed, 0 failed`, `leak failures: 0`, exit 0 |
| Backed by 108 tests | [`code/knowledge/`](code/knowledge/) | 6 files | — | repo-metrics: 108 `def test_` / 113 collected |

## Zelbi — bullet 4: the Stripe claim-fee lifecycle

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Authorization, capture, void, refund, webhooks, scheduled reconciliation | [`money-path.md`](02-architecture/money-path.md) · [`marketplace-state-machine.md`](01-product-logic/marketplace-state-machine.md) | [`code/payments/`](code/payments/) | [D23](03-decisions/money/D23.md), [D211](03-decisions/money/D211.md), [D212](03-decisions/money/D212.md), [D217](03-decisions/money/D217.md), [D324](03-decisions/money/D324.md) | repo-metrics component table |
| Adopts provider-confirmed captures instead of recapturing | [`money-path.md`](02-architecture/money-path.md) row 3 | [`test_stripe_service.py`](code/payments/test_stripe_service.py) (12) | [D261](03-decisions/money/D261.md) | — |
| Rolls back local state when provider calls fail | [`money-path.md`](02-architecture/money-path.md) row 5 | [`test_stripe_service.py`](code/payments/test_stripe_service.py) | — | — |
| Recovers live holds when authorization webhooks are lost | [`04-troubleshooting/04-false-charge-message.md`](04-troubleshooting/04-false-charge-message.md) | [`test_pending_payment_sweeper.py`](code/payments/test_pending_payment_sweeper.py) (6) — incl. *live hold is promoted, not cancelled* | — | commit `14243ef` |
| ~60 tests across services, routes, webhooks, sweepers | [`code/payments/`](code/payments/) | 6 files | — | repo-metrics: 59 + a money subset of the claims tests |

## Zelbi — bullet 5: production debugging

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Diagnosed through error reporting, source inspection, and git history | [`04-troubleshooting/`](04-troubleshooting/) (whole folder) | — | [D274](03-decisions/ops/D274.md) | commit hashes in each write-up |
| Prepared-statement collisions behind a transaction pooler, fixed at the engine layer | [`04-troubleshooting/01`](04-troubleshooting/01-prepared-statements-vs-pooler.md) | — (not unit-testable — stated there) | — | commit `884af15` · [`code/database/database.py`](code/database/database.py) |
| Authentication resets from two independent causes | [`04-troubleshooting/02`](04-troubleshooting/02-two-cause-auth-reset.md) | — | [D276](03-decisions/ops/D276.md), [D277](03-decisions/ops/D277.md) | commit `5d02d80` |
| Auth-redirect loop closed with a fixpoint guard | [`04-troubleshooting/03`](04-troubleshooting/03-auth-redirect-fixpoint.md) | — | — | commit `f17a378` |

## Zelbi — bullet 6: trust and safety

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Reputation model with strikes and healing | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) | [`code/trust/test_trust_service.py`](code/trust/test_trust_service.py), [`test_strike.py`](code/trust/test_strike.py) | [D21](03-decisions/trust/D21.md), [D182](03-decisions/trust/D182.md), [D183](03-decisions/trust/D183.md), [D299](03-decisions/trust/D299.md) | repo-metrics |
| Symmetric user blocking | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) | [`code/trust/test_blocks.py`](code/trust/test_blocks.py) (37) | [D318](03-decisions/trust/D318.md), [D322](03-decisions/privacy/D322.md) | **13** call sites — see [LIMITATIONS](LIMITATIONS.md); the résumé states no count |
| Normalizer-backed message guard on send and edit | [`trust-and-safety-design.md`](01-product-logic/trust-and-safety-design.md) | [`code/message_guard/test_scam_detection.py`](code/message_guard/test_scam_detection.py), [`test_scam_wiring.py`](code/message_guard/test_scam_wiring.py) | [D225](03-decisions/trust/D225.md), [D226](03-decisions/trust/D226.md), [D232](03-decisions/trust/D232.md), [D264](03-decisions/trust/D264.md), [D270](03-decisions/trust/D270.md), [D272](03-decisions/trust/D272.md) | rule table withheld — [MANIFEST](MANIFEST.md) |
| Admin dispute resolution issues an idempotent refund before the ruling is written | [`money-path.md`](02-architecture/money-path.md) row 12 · [`failure-state-matrix.md`](01-product-logic/failure-state-matrix.md) row 4 | [`code/payments/`](code/payments/) | [D324](03-decisions/money/D324.md) | Fact-ID TS-004 (no non-admin 403 test — [LIMITATIONS](LIMITATIONS.md)) |
| Client-reported arrival confirmation | [`tradeoffs.md`](02-architecture/tradeoffs.md) | — | [D444](03-decisions/ops/D444.md) | Fact-ID TS-005 |

## Zelbi — bullet 7: location privacy and the legal audit

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| Rebuilt after reversing the original scheme offline | [`04-troubleshooting/05`](04-troubleshooting/05-location-scheme-reversal.md) | — | [D323](03-decisions/privacy/D323.md) | commit `26eaa9b` · Fact-ID L-003 |
| HMAC-keyed per-listing fuzzing on all public surfaces | [`location-privacy-design.md`](01-product-logic/location-privacy-design.md) | [`code/coordinate_privacy/test_coordinate_privacy.py`](code/coordinate_privacy/test_coordinate_privacy.py) — *distance in range*, *seeded stability* | [D125](03-decisions/privacy/D125.md), [D137](03-decisions/privacy/D137.md), [D323](03-decisions/privacy/D323.md) | Fact-ID L-001 |
| Exact coordinates to the giver and a payment-authorized picker | [`location-privacy-design.md`](01-product-logic/location-privacy-design.md) | [`test_coordinate_privacy.py`](code/coordinate_privacy/test_coordinate_privacy.py) | [D320](03-decisions/privacy/D320.md), [D321](03-decisions/privacy/D321.md), [D322](03-decisions/privacy/D322.md) | L-002 |
| 127-listing recompute under secret rotation | [`04-troubleshooting/05`](04-troubleshooting/05-location-scheme-reversal.md) | — | [D323](03-decisions/privacy/D323.md) | Fact-ID L-004 |
| 15 tests | [`code/coordinate_privacy/`](code/coordinate_privacy/) | 1 file | — | repo-metrics: 10 `def test_` / 15 collected |
| Ten-section legal and privacy audit; versioned terms acceptance, account deletion, US-only gate shipped from its findings | [`tradeoffs.md`](02-architecture/tradeoffs.md) §legal | [`code/database/`](code/database/) | [D215](03-decisions/privacy/D215.md) | Fact-IDs C-001, C-002a–e — documents deliberately excluded |

## Independent build — construction company

| Claim | Proven at | Test | Decision | Verification |
|---|---|---|---|---|
| AI operations dashboard unifying email, phone, SMS, calendar, leads, invoices, jobs, payroll; Claude classifier triages inbound mail into a priority queue | [`system-overview.md`](02-architecture/system-overview.md) §second system | — (no code published) | — | Fact-IDs N-001, AI-008, E-003a/c |
| Voice receptionist over SIP, SMS intake, streaming lead-capture chat with calendar booking | same | — | — | AI-009, AI-010 |
| 45-test suite, nine seed scripts, file-lock concurrency, constant-time secret comparison | same | — | — | N-001, AI-008 |
| ERPNext migration: custom Frappe app, three tested doctypes, two migration engines preserving historical-date integrity | same | — | — | N-002 |

## Project — AI delivery governance and developer tooling

| Claim | Proven at | Test | Decision | Verification | Note |
|---|---|---|---|---|---|
| Nine custom subagents on top of an installed framework | [`tooling/agents/`](tooling/agents/) — 9 files | — | — | Fact-ID N-003a (24 definitions: 15 framework, 9 mine) | — |
| Runtime enforcement hooks — git-push block, JS syntax, prompt format, session lifecycle, decision ownership, brevity, plain English | [`05-process/enforcement-hooks.md`](05-process/enforcement-hooks.md) · [`tooling/hooks/`](tooling/hooks/) — 12 files | [`tooling/hooks/test_conduct_lesson_parser.py`](tooling/hooks/test_conduct_lesson_parser.py) | — | N-003b | — |
| Unit-tested rule parser | [`tooling/hooks/conduct_lesson_parser.py`](tooling/hooks/conduct_lesson_parser.py) | its own test | — | N-003b | — |
| Versioned cross-tool rules registry | [`tooling/rules-registry/`](tooling/rules-registry/) · [`05-process/behavioral-rulebook.md`](05-process/behavioral-rulebook.md) | — | — | N-003c | — |
| Flask + PostgreSQL multi-repo dev dashboard, in production two days after first commit; voice bridge (exploration, paused); Stream Deck plugin on Claude Code lifecycle hooks | described only — [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §other systems | — | — | N-004, N-005, AI-011, AI-012 | Command Center, voice-bridge and ClawDeck are separate private repositories; not published here. |

## Skills section

| Claim | Proven at |
|---|---|
| Python, TypeScript, SQL, Bash; FastAPI, React Native / Expo | [`code/`](code/) — every subfolder |
| Anthropic API, multimodal vision prompts, structured JSON outputs, Pydantic validation, output allowlists, provider-safe error mapping | [`02-architecture/ai-boundary.md`](02-architecture/ai-boundary.md), [`code/ai_service/`](code/ai_service/) |
| Document ingestion and chunking, PostgreSQL full-text retrieval, filter-first access control, golden-set evaluation, adversarial leak testing, refusal-system design | [`code/knowledge/`](code/knowledge/), [`runnable/knowledge-eval/`](runnable/knowledge-eval/) |
| Claude Code subagents and runtime enforcement hooks, cross-tool rules registry | [`tooling/`](tooling/), [`05-process/`](05-process/) |
| Scam detection, message guards, dispute/refund workflows, reputation and strike models, coordinate obfuscation, per-route rate limiting | [`01-product-logic/`](01-product-logic/), [`code/trust/`](code/trust/), [`code/message_guard/`](code/message_guard/), [`code/coordinate_privacy/`](code/coordinate_privacy/), [`code/database/rate_limit.py`](code/database/rate_limit.py) |
| SQLAlchemy, Alembic; Stripe authorization/capture, webhook signature verification, idempotency | [`02-architecture/data-and-migrations.md`](02-architecture/data-and-migrations.md), [`02-architecture/money-path.md`](02-architecture/money-path.md) |
| Sentry, pytest, scheduled jobs | [`code/database/observability.py`](code/database/observability.py), [`code/jobs/`](code/jobs/), [`verification/`](verification/) |
| Railway (deployment platform) | [`code/jobs/`](code/jobs/) — the cron runners it schedules · [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §the pieces |
| Apple Pay | [`02-architecture/money-path.md`](02-architecture/money-path.md) §the client surface — payment-sheet configuration, client-side and not exercised by the backend suite |
| PostGIS | [`02-architecture/data-and-migrations.md`](02-architecture/data-and-migrations.md) |
| SQLite | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §second system — **described, not published.** Not used by Zelbi: [`runnable/knowledge-eval/conftest.py`](runnable/knowledge-eval/conftest.py) names it only as the engine the containment tests refuse to run on |
| Supabase Auth, Supabase RLS | [`02-architecture/data-and-migrations.md`](02-architecture/data-and-migrations.md) · [`LIMITATIONS.md`](LIMITATIONS.md) — RLS is unversioned dashboard state, and is claimed only as enabled |
| JavaScript | Used in the construction-company operations dashboard (single-page JS front end) and via TypeScript in [`code/mobile/`](code/mobile/). No plain-JavaScript source is published; see [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §second system |
| Cloudflare R2 | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §the pieces |
| Cloudflare Pages / Workers | **Pages:** Zelbi's legal pages are served from Cloudflare Pages out of the private repository's `web/` folder (commit `d108873`, 2026-09-01). Not published here; verifiable on request. **Workers:** not evidenced — none is used by Zelbi |
| Doppler (secrets manager) | Secrets manager adopted 2026-07-30 (`doppler.yaml` in the private repository). Not published here; verifiable on request |
| Git, GitHub | [`05-process/enforcement-hooks.md`](05-process/enforcement-hooks.md) (the git-push blocker) · [`05-process/handoff-protocol.md`](05-process/handoff-protocol.md) |
| MCP | [`tooling/README.md`](tooling/README.md) — servers are configured in the Claude Code environment, not in any file here |
| Cursor rules and commands | [`tooling/rules-registry/tools-cursor.md`](tooling/rules-registry/tools-cursor.md) · [`tooling/README.md`](tooling/README.md) · [`MANIFEST.md`](MANIFEST.md) §1.7 |
| PII and data-exposure audit | [`02-architecture/tradeoffs.md`](02-architecture/tradeoffs.md) §legal — the audit documents themselves are deliberately excluded |
| Flask; Frappe / ERPNext; Gmail Pub/Sub; Twilio; Retell AI; Google OAuth, Calendar and Places; OpenAI Whisper | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §second system — **described, not published** |
| Gemini Live API | [`02-architecture/system-overview.md`](02-architecture/system-overview.md) §other systems — **exploration** |


Every tool named in the résumé's skills section now carries a pointer. Where the
pointer is to a description rather than to code, the row says so; where nothing
in this repository evidences the tool, the row says that instead of reaching for
the nearest plausible file.

---

## Reverse check — is every folder reachable from a row?

| Folder | Referenced by | Status |
|---|---|---|
| `01-product-logic/` | bullets 6, 7; skills | ✅ |
| `02-architecture/` | S1, bullets 1–4, 7; skills | ✅ |
| `03-decisions/money/` | bullets 1, 4 | ✅ |
| `03-decisions/trust/` | bullet 6 | ✅ |
| `03-decisions/privacy/` | bullet 7 | ✅ |
| `03-decisions/ai/` | bullets 2, 3 | ✅ |
| `03-decisions/ops/` | bullets 5, 6 | ✅ |
| `04-troubleshooting/` | bullet 5, bullets 4 and 7 | ✅ |
| `05-process/` | S2b; tooling project | ✅ |
| `code/ai_service/` | bullet 2 | ✅ |
| `code/knowledge/` | bullet 3 | ✅ |
| `code/payments/` | bullets 1, 4 | ✅ |
| `code/coordinate_privacy/` | bullet 7 | ✅ |
| `code/trust/` | bullet 6 | ✅ |
| `code/message_guard/` | bullet 6 | ✅ |
| `code/database/` | bullet 1; skills | ✅ |
| `code/jobs/` | skills (scheduled jobs) | ✅ |
| `code/mobile/` | **bullet 5 only, indirectly** | ⚠️ see below |
| `runnable/knowledge-eval/` | bullet 3 | ✅ |
| `tooling/agents/`, `hooks/`, `rules-registry/`, `skills/` | tooling project | ✅ |
| `verification/` | S2c and every numeric row | ✅ |

**One weak row.** [`code/mobile/`](code/mobile/) is reached only through the
auth-reset write-up ([bullet 5](04-troubleshooting/02-two-cause-auth-reset.md)),
which cites the Supabase client and auth store. The other four files there —
the message-guard client, push-tap routing, notification routing, and listing
coordinate handling — are the client halves of claims proven on the backend side,
and no résumé sentence points at them directly. They are kept because a reviewer
asking "what does the client do with the fuzzed coordinate?" should be able to
look, and because there are **no mobile tests**, which makes seeing the code the
only available evidence. Flagged rather than quietly padded.

**Two folders in the plan that were not created:** `tooling/cursor/` and
`03-decisions/INDEX.md`'s companion `tooling/skills/learned/`. Both are recorded
in [`MANIFEST.md`](MANIFEST.md) with the reason.

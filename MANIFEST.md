# Manifest

Every file in this repository: where it came from, and what was removed.

Compiled by hashing each output file against its candidate sources, so
"verbatim" below means **byte-identical to the private original**, not "roughly
unchanged". Anything not byte-identical is listed as authored or modified and
has an entry in the removals section.

- **227 files** · 118 verbatim · 109 authored or modified
- Source commit for all Zelbi material: `3413d028b5abd5163a820790c4fe8d9b0c82f922`
- Compiled 2026-09-03

---

## 1. Removals — every sanitization, with file and line range

### 1.1 Scam-rule table

| File | Lines | Removed | Replaced with |
|---|---|---|---|
| `code/message_guard/scam_detection.py` | 104–417 (314 lines) | The whole Rule-3 pattern table: every compiled regular expression, each an alternation of literal trigger phrases and their evasion variants, across payment brands, phone numbers and phone solicitation, urgency, currency and pricing, email and email solicitation, social handles, links, the six scheduling-intent signals, addresses, cancel/confirm intent, and the six picker-question deflect categories. | `# rule table withheld` plus a paragraph naming every category and stating that the normalizer above and the dispatcher framework below are intact. |
| `code/message_guard/scam_detection.py` | 44–45 | Listing-tempo values: the minimum interval between consecutive listings and the per-day ceiling. | The symbol `WITHHELD`, with the guard's shape stated in a comment. |
| `code/message_guard/scam_detection.py` | 9–10 | An absolute local filesystem path to a session plan file. | A generic reference to "the session plan file". |

**Why:** publishing the alternation list publishes the evasion recipe. The
normalizer — which decodes evasion *before* any pattern runs, and is where the
actual engineering is — is kept in full, as is every dispatcher, so a reviewer
can see how rules compose and where enforcement happens.

### 1.2 Trust-model tuned constants

| File | Lines | Removed | Replaced with |
|---|---|---|---|
| `code/trust/trust_service.py` | 1–13, 21–34 | Completion award, four deduction weights, heal threshold, score floor and ceiling — in both the module docstring and the constant block. | The symbol `WITHHELD`. Constant **names**, types, ordering and all consuming logic unchanged. |
| `code/trust/strike_service.py` | 5, 29–31, 33–37, 135–136 | Strike threshold, rolling-window lengths, timeout duration, dispute warning and suspension thresholds — in constants and in two docstrings. | The symbol `WITHHELD`, with the rule's shape stated. |
| `code/trust/test_trust_service.py` | 16 assertion sites | Expected trust-score values. These are the constants in arithmetic form — one completion asserting a specific score publishes the award directly. | The symbol `WITHHELD`. Test names, structure and scenarios unchanged, so *what* is tested stays visible. |
| `03-decisions/trust/D182.md` | inline | Deduction weights, heal threshold, score bands, a migration identifier. | Symbolic names + "tuned constants withheld". |
| `03-decisions/trust/D183.md` | inline | Superseded and replacement deduction weights, bonuses, floors. | Same. |
| `03-decisions/trust/D299.md` | 5 sites | Completion award, deduction weights, heal threshold, score floor and ceiling, a migration identifier. | Same. |
| `03-decisions/trust/D21.md` | 6 sites | Strike threshold, rolling-window length, timeout duration, and the superseded ladder's thresholds. | Same. |

**Known gap, flagged for the gate:** `code/trust/test_strike.py` retains loop
counts (`range(2)` followed by one more action) from which the strike threshold
is inferable. Redacting them would gut the test's readability. Nick's call
whether to withhold the file, rewrite those loops, or accept the inference.

**Ruling 2026-09-03 (Nick):** kept as is; the three-strike rule is stated on the
resume and is user-visible product policy.

The migration identifiers removed from `D182` and `D299` above, and the session
plan path removed in §1.1, were not required by plan §5. Judgment call beyond
plan §5, on the conservative side; recorded here.

### 1.3 Policy corpus

The fifteen real policy documents (8 public, 4 CX, 3 internal) are **not
published in any form** — not their text, not their titles, not their paths in
quoted output. `runnable/knowledge-eval/docs/policy/` contains three synthetic
documents about an invented tool-lending library, one per tier, and
`runnable/knowledge-eval/app/data/knowledge_eval_cases.json` contains 22
invented questions in the same contract and the same 12-answer / 10-refusal
split. The ingestion, chunking, retrieval, answer and eval code is verbatim.

### 1.4 Third-party identity

| Scope | Removed | Replaced with |
|---|---|---|
| `tooling/agents/{build-error-resolver,code-reviewer,planner,security-reviewer}.md`, `tooling/rules-registry/{my-assistant-rules,RULE-FIX-BLUEPRINT-v2,RULE-FIX-BLUEPRINT-v3}.md` | The construction company's real name — 11 occurrences across 7 files. | "the construction company" / "construction-company operations dashboard". |
| Everywhere | The company owner's real name. | Never written. Verified absent by the scan in §4. |
| `05-process/handoff-protocol.md` (2 paths), `tooling/skills/handoff-protocol/SKILL.md` (2 paths) | The company's initialism in a private note directory path — left inconsistent with the name redaction above. | `<project>`. |

### 1.5 The August 2026 credential-handling episode

No reference appears anywhere in this repository. Concretely excluded:

- Three lines from `backend/lessons.md` dated 2026-08-31 describing secret
  deletion, mail-provider key scopes, and a secret verified by length — omitted
  from `04-troubleshooting/lessons-backend.md`.
- One further lessons line about a local webhook signing secret — omitted.
- Two lessons lines describing staging credential procedures — omitted.
- `04-troubleshooting/05-location-scheme-reversal.md` describes the 127-listing
  recompute as occurring "under a secret rotation", which is true, and does not
  say what prompted the rotation.

### 1.6 Not copied at all

| Excluded | Reason |
|---|---|
| `docs/agents/backlog.md`, `00-current-state.md`, `zelbi-build-map.md` | Internal control documents (plan §5). Cited by line where a decision record needs it; never copied. |
| `docs/agents/audit-evidence/` and the legal/compliance audit documents | Plan §5 — reduced to one paragraph in `02-architecture/tradeoffs.md`. |
| Any code from the construction-company repositories | Plan §7 decision 6 — described in `02-architecture/system-overview.md`, no code. |
| Every `gsd-*` agent, hook, skill and command | Installed framework, not Nick's work. 15 agent definitions and 3 hooks excluded. |
| `~/.claude/commands/` | Contains only `gsd`. |
| `tooling/skills/learned/` (16 files) | Auto-generated queue stubs — a repeated prompt template plus a local transcript path. No content, and they leak local paths. |
| `ai-rules/db-auto-detailing-rules.md` | That project is excluded from all recruiting material by Nick's own decision. |
| `03-decisions/ai/D213.md` | Withheld after Gate 7 review: launch-time moderation posture. |
| `ai-rules/zelbi-rules.md.bak` | Backup file. |
| Real user rows, seed data resembling real people | None copied. |

### 1.7 Could not be sourced — left out, with the reason

| Wanted | Why it is not here |
|---|---|
| `tooling/cursor/` — Cursor rules and commands | **No such files exist.** There is no `.cursor/rules` directory and no `.cursorrules` file in the Zelbi repository, and `~/.cursor` holds only IDE state. The Cursor-facing rules are a single file, `tools-cursor.md`, which lives in the rules registry and is copied there. The empty folder was removed rather than shipped. |
| Verbatim quotes from the Phase 1 survey and the Phase 2 verification report | **Neither document exists on disk.** Both are prior-session artifacts. Rather than quote them second-hand, the full test suite and every repository metric were **re-run from scratch** on 2026-09-03 and recorded with their commands in `verification/`. Figures that could only have come from those documents are attributed to their Fact-ID instead. |
| A reproduction of "sixteen block call sites" | **Could not be reproduced** — 13 by every method tried. Recorded in `LIMITATIONS.md` for Nick's decision. |
| A regression test for the prepared-statement fix | Not constructible: it needs a transaction-mode pooler multiplexing callers onto one backend. Stated in the write-up rather than claimed. |

---

## 2. Modifications that are not removals

| File(s) | Change |
|---|---|
| `runnable/knowledge-eval/scripts/*.py` (6 files) | One trailing comment added to the path-shim line, marking that the package root replaces the private repository's `backend/` root. No logic changed. |
| `runnable/knowledge-eval/tests/*.py` (6 files) | Re-pointed at the synthetic corpus: repository-root depth, document paths, document counts, and the questions the parametrised cases name. Two structural adaptations, both forced by real properties of the system and both explained in `runnable/knowledge-eval/README.md`: the golden-set lookup is keyed on (question, index) because adversarial pairs share wording; and one adversarial probe is deliberately *not* word-identical to its CX counterpart because the refusal matcher is index-independent by design. **No assertion was weakened and no test was removed.** |
| `runnable/knowledge-eval/app/models.py` | The six knowledge tables are verbatim, including every check constraint and index. Imports and `Base` were reconstructed, and a minimal three-column `User` was added as a stand-in for the admin gate. |
| `runnable/knowledge-eval/docs/policy/public/tool-library-loans.md` | Authored. Its `implementation_status` is `locked_pending_build` so the composer's unbuilt-feature note path is exercised, as the private corpus document did. |
| `05-process/behavioral-rulebook.md`, `05-process/handoff-protocol.md` | Verbatim copies with a provenance comment prepended (which is why they hash as modified). The rulebook carries the §1.4 name redaction. |
| `code/*/routers_*.py`, `code/mobile/*` | Renamed on copy to keep a flat folder readable (`routers/ai.py` → `routers_ai.py`, `utils/messages.ts` → `utils_messages.ts`). Contents byte-identical. |

---

## 3. The 44 decision records — selection, with reasons

Selected from 406. Per-entry reasons for Nick's review at the gate.

### money (12)

| D | Why selected |
|---|---|
| D23 | The base ruling the whole money path implements — per-event rules instead of one blanket policy. |
| D207 | A deferral with the blocker named (no event records a giver no-show). A record that only holds wins is worthless. |
| D211 | Auto-capture timing — the ruling that makes client-reported arrival survivable. |
| D212 | The authorization-expiry protection the resume's "recover live holds" claim rests on. |
| D217 | **Cancel, never capture**, with the cost arithmetic stated and the void-before-write ordering. Then superseded — which is why it is here. |
| D218 | The booking ceiling is *derived* from the hold's lifetime, not picked. The clearest single example of reasoning from a constraint. |
| D261 | An investigation that ruled **not a defect**. Deciding not to fix is a decision. |
| D305 | Choosing a first-party checkout over the native wallet takeover, with the reasoning. |
| D306 | Corrects two of D305's own technical premises after a full read. Self-correction in the log. |
| D317 | Consent recorded, not merely shown — the ruling behind the consent columns. |
| D319 | Consent stamped at the tap, not at mount, with the measured 13.1s-vs-0.09s proof. |
| D324 | Refund through the provider before the ruling is written — the resume's dispute claim. |

### trust (11)

| D | Why selected |
|---|---|
| D21 | Replaced an escalating ladder with a single tier once the fee existed. Removing a mechanism the fee made redundant. |
| D182 | The trust rebuild — first infraction free, infractions heal, points do not return. |
| D183 | An explicit record of what the rebuild retired. Rare and valuable: most logs record what was added. |
| D225 | Extend the existing engine at the one choke point rather than build a parallel module. |
| D226 | **No per-message model**, with the latency-and-cost reason. Choosing not to use AI is an AI decision. |
| D232 | The category taxonomy on the refusal — enforcement that tells the client what happened. |
| D264 | A shipped detection rule retired and replaced with something narrower. |
| D270 | A shipped rule **deleted, not disabled**. The harder call, and stated as one. |
| D272 | No listing is ever hidden at post time — a deliberate limit on enforcement power. |
| D299 | Trust earned per handoff, and why the previous model's instant-perfect score carried no information. |
| D318 | Blocking never costs money and never files a strike. A safety principle stated as a prohibition. |

### privacy (7)

| D | Why selected |
|---|---|
| D125 | The original approximate-point system — the design that was later found reversible. Included *because* it was wrong. |
| D137 | How the approximate location is presented, and the privacy posture around it. |
| D215 | Soft delete over hard delete, with the record-link reasoning and the rejected alternative. |
| D320 | True coordinates cross at the paywall seam only. The disclosure rule in one sentence. |
| D321 | A stranger's profile serves the approximate point — closing a surface that would otherwise leak. |
| D322 | A blocked party keeps their receipt minus the address. Balancing safety against record-keeping. |
| D323 | The HMAC re-key — the fix for D125, and the ruling behind the strongest write-up here. |

### ai (5)

| D | Why selected |
|---|---|
| D18 | Two options, A/B, user picks and edits — the ruling that puts a human between the model and the database. |
| D87 | A recorded model failure mode (brand hallucination). The log naming what the model gets wrong. |
| D122 | Category-conditional photo requirements — product logic constraining a model input. |
| D438 | Implements D122 through one voice. Shows a decision travelling from ruling to interface. |
| D440 | Cached analysis still plays the beat — a small ruling that keeps a fast path from feeling broken. |

### ops (9)

| D | Why selected |
|---|---|
| D198 | Two notification lanes — the policy the notification service implements. |
| D200 | A single daily runner rather than per-job scheduling. |
| D238 | A ten-minute cadence, derived from the query window's width. Same reasoning style as D218. |
| D274 | Error reporting supersedes the log-only ruling — the direct consequence of the sixteen-hour silent crash. |
| D275 | Rate limiting in-process and per-route, with the scope reasoning. |
| D276 | "The primary client must **never** use PKCE" — one half of the two-cause auth bug. |
| D277 | "Background polls must **never** end a session" — the other half. A prohibition protecting an invisible property. |
| D442 | A rate-limit hit is an admin signal, not a user-facing bug. Holding a ceiling under pressure to remove it. |
| D444 | The arrival ping is a fast lane, not the engine — the ruling behind the client-trusted-arrival limitation. |

### Themes deliberately not represented

UI and copy rulings — panel heights, corner radii, button labels, animation
timing — are the majority of the 406. They are real decisions and they show
craft, but in a domain the resume does not claim, so none were selected.

---

## 4. Secret scan

Run over the whole output folder after everything was written, with a
19-pattern regex sweep (`__pycache__`, `.pytest_cache` and `.git` excluded).

**First pass: 56 raw hits across 7 pattern classes. Final pass: 48 hits across
3 classes, every one benign and enumerated below.** The 8 hits that disappeared
between passes were all fixed, not reclassified — see §1.4 and the note on this
file below.

Nothing was left unresolved.

| Pattern class | Result |
|---|---|
| `key`, `token`, `password`, `secret`, `DSN` (as literal values) | no findings |
| Database connection strings carrying credentials | no findings (the only connection strings present are credential-free local test URLs, which a reviewer needs to run the package) |
| Managed-database, object-storage, deployment-platform and product subdomain hosts (five host patterns; literals omitted here so this table does not reintroduce them) | no findings |
| Payment-provider live/test key and webhook-signing prefixes followed by a value | no findings |
| `AKIA[0-9A-Z]{16}` | no findings |
| `-----BEGIN` | no findings |
| 32+ character hex or base64 strings | no findings (all candidates were long test-function names and commit hashes) |
| Construction company name | 11 occurrences found and removed (§1.4) |
| Company owner's name | no findings |
| The three named host strings from the review checklist | no findings |

### The 48 remaining hits, in full

| Class | Count | What they are |
|---|---|---|
| `long-hex` (32+ hex chars) | 10 | Git commit SHAs, all of them. Commit hashes are published deliberately — plan §5 keeps them verbatim so a reviewer can locate any change in the private history. |
| `long-b64` (40+ base64 chars) | 30 | The same commit SHAs matched a second time, plus long filesystem paths in this file's own source table and two note-directory paths in the handoff protocol. |
| `postgres-dsn` | 8 | Credential-free local test URLs of the form `postgresql://localhost/<db>`, plus the scheme-rewrite lines in `runnable/knowledge-eval/app/database.py`. A reviewer needs these to run the package. No host, user or password appears anywhere. |

**Zero hits** in every remaining class: payment-provider keys, webhook signing
secrets, cloud access keys, PEM blocks, error-reporter DSNs, any
`key`/`secret`/`token`/`password` assigned a literal value, every managed-host
pattern, the company name, the owner's name, and the credential episode.

### Fixed during the scan, not reclassified

- The construction company's name — 11 occurrences, §1.4.
- Its initialism in a note-directory path — 4 occurrences, §1.4.
- **This file's own scan table.** The first draft listed the host strings it had
  searched for as literals, which reintroduced them into the repository. The
  table now names the pattern classes and omits the literals.

### Resolved false positives, kept deliberately:

- `tooling/rules-registry/RULE-FIX-BLUEPRINT-v3.md:152` lists payment-provider
  key prefixes inside a table describing a **secret-leakage detection gate**.
  Prefixes with no value attached: documentation of a pattern list, not a secret.
- `support@zelbi.ai` appears in the knowledge system's refusal template and in
  the synthetic corpus. It is the product's published support address and is the
  string the refusal tests assert on.
- `code/message_guard/test_scam_detection.py` contains reserved test numbers and
  `example.com` addresses as fixtures.
- Absolute `/Users/nickbroyzer/...` paths remain in some `tooling/` files. Kept
  **verbatim on purpose**: these are the scripts as they actually run, and the
  username is Nick's own public handle. Anyone reusing the bundle will need to
  change them, and `tooling/README.md` says so.

---

## 5. Full file list

### `(repository root)` — 3 files

| File | Source | State |
|---|---|---|
| `.gitignore` | authored for this repository | authored / modified |
| `LEDGER.md` | authored for this repository | authored / modified |
| `LIMITATIONS.md` | authored for this repository | authored / modified |

### `01-product-logic` — 4 files

| File | Source | State |
|---|---|---|
| `failure-state-matrix.md` | authored for this repository | authored / modified |
| `location-privacy-design.md` | authored for this repository | authored / modified |
| `marketplace-state-machine.md` | authored for this repository | authored / modified |
| `trust-and-safety-design.md` | authored for this repository | authored / modified |

### `02-architecture` — 5 files

| File | Source | State |
|---|---|---|
| `ai-boundary.md` | authored for this repository | authored / modified |
| `data-and-migrations.md` | authored for this repository | authored / modified |
| `money-path.md` | authored for this repository | authored / modified |
| `system-overview.md` | authored for this repository | authored / modified |
| `tradeoffs.md` | authored for this repository | authored / modified |

### `03-decisions` — 46 files

| File | Source | State |
|---|---|---|
| `INDEX.md` | authored for this repository | authored / modified |
| `ai/D122.md` | authored for this repository | authored / modified |
| `ai/D18.md` | authored for this repository | authored / modified |
| `ai/D438.md` | authored for this repository | authored / modified |
| `ai/D440.md` | authored for this repository | authored / modified |
| `ai/D87.md` | authored for this repository | authored / modified |
| `money/D207.md` | authored for this repository | authored / modified |
| `money/D211.md` | authored for this repository | authored / modified |
| `money/D212.md` | authored for this repository | authored / modified |
| `money/D217.md` | authored for this repository | authored / modified |
| `money/D218.md` | authored for this repository | authored / modified |
| `money/D23.md` | authored for this repository | authored / modified |
| `money/D261.md` | authored for this repository | authored / modified |
| `money/D305.md` | authored for this repository | authored / modified |
| `money/D306.md` | authored for this repository | authored / modified |
| `money/D317.md` | authored for this repository | authored / modified |
| `money/D319.md` | authored for this repository | authored / modified |
| `money/D324.md` | authored for this repository | authored / modified |
| `ops/D198.md` | authored for this repository | authored / modified |
| `ops/D200.md` | authored for this repository | authored / modified |
| `ops/D238.md` | authored for this repository | authored / modified |
| `ops/D274.md` | authored for this repository | authored / modified |
| `ops/D275.md` | authored for this repository | authored / modified |
| `ops/D276.md` | authored for this repository | authored / modified |
| `ops/D277.md` | authored for this repository | authored / modified |
| `ops/D442.md` | authored for this repository | authored / modified |
| `ops/D444.md` | authored for this repository | authored / modified |
| `privacy/D125.md` | authored for this repository | authored / modified |
| `privacy/D137.md` | authored for this repository | authored / modified |
| `privacy/D215.md` | authored for this repository | authored / modified |
| `privacy/D320.md` | authored for this repository | authored / modified |
| `privacy/D321.md` | authored for this repository | authored / modified |
| `privacy/D322.md` | authored for this repository | authored / modified |
| `privacy/D323.md` | authored for this repository | authored / modified |
| `trust/D182.md` | authored for this repository | authored / modified |
| `trust/D183.md` | authored for this repository | authored / modified |
| `trust/D21.md` | authored for this repository | authored / modified |
| `trust/D225.md` | authored for this repository | authored / modified |
| `trust/D226.md` | authored for this repository | authored / modified |
| `trust/D232.md` | authored for this repository | authored / modified |
| `trust/D264.md` | authored for this repository | authored / modified |
| `trust/D270.md` | authored for this repository | authored / modified |
| `trust/D272.md` | authored for this repository | authored / modified |
| `trust/D299.md` | authored for this repository | authored / modified |
| `trust/D318.md` | authored for this repository | authored / modified |

### `04-troubleshooting` — 7 files

| File | Source | State |
|---|---|---|
| `01-prepared-statements-vs-pooler.md` | authored for this repository | authored / modified |
| `02-two-cause-auth-reset.md` | authored for this repository | authored / modified |
| `03-auth-redirect-fixpoint.md` | authored for this repository | authored / modified |
| `04-false-charge-message.md` | authored for this repository | authored / modified |
| `05-location-scheme-reversal.md` | authored for this repository | authored / modified |
| `lessons-backend.md` | authored for this repository | authored / modified |
| `lessons-mobile.md` | authored for this repository | authored / modified |

### `05-process` — 7 files

| File | Source | State |
|---|---|---|
| `behavioral-rulebook.md` | authored for this repository | authored / modified |
| `build-map-and-drift-check.md` | authored for this repository | authored / modified |
| `check-build-map.sh` | `~/Projects/zelbi.ai/tools/check-build-map.sh` | verbatim |
| `enforcement-hooks.md` | authored for this repository | authored / modified |
| `handoff-protocol.md` | authored for this repository | authored / modified |
| `model-routing.md` | authored for this repository | authored / modified |
| `verification-gates.md` | authored for this repository | authored / modified |

### `code` — 66 files

| File | Source | State |
|---|---|---|
| `ai_service/ai_service.py` | `~/Projects/zelbi.ai/backend/app/services/ai_service.py` | verbatim |
| `ai_service/routers_ai.py` | `~/Projects/zelbi.ai/backend/app/routers/ai.py` | verbatim |
| `ai_service/test_ai.py` | `~/Projects/zelbi.ai/backend/tests/test_ai.py` | verbatim |
| `ai_service/test_ai_object_key_ownership.py` | `~/Projects/zelbi.ai/backend/tests/test_ai_object_key_ownership.py` | verbatim |
| `ai_service/test_ai_service.py` | `~/Projects/zelbi.ai/backend/tests/test_ai_service.py` | verbatim |
| `ai_service/test_ai_soft_item.py` | `~/Projects/zelbi.ai/backend/tests/test_ai_soft_item.py` | verbatim |
| `coordinate_privacy/coordinate_privacy.py` | `~/Projects/zelbi.ai/backend/app/services/coordinate_privacy.py` | verbatim |
| `coordinate_privacy/test_coordinate_privacy.py` | `~/Projects/zelbi.ai/backend/tests/test_coordinate_privacy.py` | verbatim |
| `database/database.py` | `~/Projects/zelbi.ai/backend/app/database.py` | verbatim |
| `database/dependencies.py` | `~/Projects/zelbi.ai/backend/app/dependencies.py` | verbatim |
| `database/observability.py` | `~/Projects/zelbi.ai/backend/app/observability.py` | verbatim |
| `database/rate_limit.py` | `~/Projects/zelbi.ai/backend/app/rate_limit.py` | verbatim |
| `database/test_migrations_phase_9.py` | `~/Projects/zelbi.ai/backend/tests/test_migrations_phase_9.py` | verbatim |
| `database/test_rate_limit_mounts.py` | `~/Projects/zelbi.ai/backend/tests/test_rate_limit_mounts.py` | verbatim |
| `jobs/listing_expiry.py` | `~/Projects/zelbi.ai/backend/app/jobs/listing_expiry.py` | verbatim |
| `jobs/recommendation_scan.py` | `~/Projects/zelbi.ai/backend/app/jobs/recommendation_scan.py` | verbatim |
| `jobs/run_daily_jobs.py` | `~/Projects/zelbi.ai/backend/app/jobs/run_daily_jobs.py` | verbatim |
| `jobs/run_frequent_jobs.py` | `~/Projects/zelbi.ai/backend/app/jobs/run_frequent_jobs.py` | verbatim |
| `jobs/test_cron_reminders.py` | `~/Projects/zelbi.ai/backend/tests/test_cron_reminders.py` | verbatim |
| `jobs/test_recommendation_scan.py` | `~/Projects/zelbi.ai/backend/tests/test_recommendation_scan.py` | verbatim |
| `jobs/test_run_daily_jobs.py` | `~/Projects/zelbi.ai/backend/tests/test_run_daily_jobs.py` | verbatim |
| `knowledge/__init__.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/__init__.py` | verbatim |
| `knowledge/answer.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/answer.py` | verbatim |
| `knowledge/answer_eval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/answer_eval.py` | verbatim |
| `knowledge/chunking.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/chunking.py` | verbatim |
| `knowledge/eval_cases.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/eval_cases.py` | verbatim |
| `knowledge/frontmatter.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/frontmatter.py` | verbatim |
| `knowledge/ingestion.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/ingestion.py` | verbatim |
| `knowledge/retrieval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/retrieval.py` | verbatim |
| `knowledge/retrieval_eval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/retrieval_eval.py` | verbatim |
| `knowledge/routers_knowledge.py` | `~/Projects/zelbi.ai/backend/app/routers/knowledge.py` | verbatim |
| `knowledge/test_knowledge_answer.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_answer.py` | verbatim |
| `knowledge/test_knowledge_ask_endpoint.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_ask_endpoint.py` | verbatim |
| `knowledge/test_knowledge_eval_seed.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_eval_seed.py` | verbatim |
| `knowledge/test_knowledge_ingestion.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_ingestion.py` | verbatim |
| `knowledge/test_knowledge_models.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_models.py` | verbatim |
| `knowledge/test_knowledge_retrieval.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_retrieval.py` | verbatim |
| `knowledge/validation.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/validation.py` | verbatim |
| `message_guard/scam_detection.py` | authored for this repository | authored / modified |
| `message_guard/test_scam_detection.py` | `~/Projects/zelbi.ai/backend/tests/test_scam_detection.py` | verbatim |
| `message_guard/test_scam_wiring.py` | `~/Projects/zelbi.ai/backend/tests/test_scam_wiring.py` | verbatim |
| `mobile/hooks_usePushTapRouting.ts` | `~/Projects/zelbi.ai/mobile/hooks/usePushTapRouting.ts` | verbatim |
| `mobile/store_auth.ts` | `~/Projects/zelbi.ai/mobile/store/auth.ts` | verbatim |
| `mobile/utils_directions.ts` | `~/Projects/zelbi.ai/mobile/utils/directions.ts` | verbatim |
| `mobile/utils_listings.ts` | `~/Projects/zelbi.ai/mobile/utils/listings.ts` | verbatim |
| `mobile/utils_messages.ts` | `~/Projects/zelbi.ai/mobile/utils/messages.ts` | verbatim |
| `mobile/utils_notificationRouting.ts` | `~/Projects/zelbi.ai/mobile/utils/notificationRouting.ts` | verbatim |
| `mobile/utils_supabase.ts` | `~/Projects/zelbi.ai/mobile/utils/supabase.ts` | verbatim |
| `payments/claim_cancel_service.py` | `~/Projects/zelbi.ai/backend/app/services/claim_cancel_service.py` | verbatim |
| `payments/pending_payment_sweeper.py` | `~/Projects/zelbi.ai/backend/app/jobs/pending_payment_sweeper.py` | verbatim |
| `payments/post_window_sweeper.py` | `~/Projects/zelbi.ai/backend/app/jobs/post_window_sweeper.py` | verbatim |
| `payments/routers_stripe_webhooks.py` | `~/Projects/zelbi.ai/backend/app/routers/stripe_webhooks.py` | verbatim |
| `payments/stripe_service.py` | `~/Projects/zelbi.ai/backend/app/services/stripe_service.py` | verbatim |
| `payments/test_pending_payment_sweeper.py` | `~/Projects/zelbi.ai/backend/tests/test_pending_payment_sweeper.py` | verbatim |
| `payments/test_post_window_sweeper.py` | `~/Projects/zelbi.ai/backend/tests/test_post_window_sweeper.py` | verbatim |
| `payments/test_stripe_billing.py` | `~/Projects/zelbi.ai/backend/tests/test_stripe_billing.py` | verbatim |
| `payments/test_stripe_customer.py` | `~/Projects/zelbi.ai/backend/tests/test_stripe_customer.py` | verbatim |
| `payments/test_stripe_service.py` | `~/Projects/zelbi.ai/backend/tests/test_stripe_service.py` | verbatim |
| `payments/test_stripe_webhooks.py` | `~/Projects/zelbi.ai/backend/tests/test_stripe_webhooks.py` | verbatim |
| `trust/block_service.py` | `~/Projects/zelbi.ai/backend/app/services/block_service.py` | verbatim |
| `trust/strike_service.py` | authored for this repository | authored / modified |
| `trust/test_blocks.py` | `~/Projects/zelbi.ai/backend/tests/test_blocks.py` | verbatim |
| `trust/test_claim_score_delta.py` | `~/Projects/zelbi.ai/backend/tests/test_claim_score_delta.py` | verbatim |
| `trust/test_strike.py` | `~/Projects/zelbi.ai/backend/tests/test_strike.py` | verbatim |
| `trust/test_trust_service.py` | authored for this repository | authored / modified |
| `trust/trust_service.py` | authored for this repository | authored / modified |

### `runnable` — 45 files

| File | Source | State |
|---|---|---|
| `knowledge-eval/README.md` | authored for this repository | authored / modified |
| `knowledge-eval/app/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/app/data/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/app/data/knowledge_eval_cases.json` | authored for this repository | authored / modified |
| `knowledge-eval/app/database.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/dependencies.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/main.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/models.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/routers/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/app/routers/admin.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/routers/knowledge.py` | `~/Projects/zelbi.ai/backend/app/routers/knowledge.py` | verbatim |
| `knowledge-eval/app/schemas/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/app/schemas/knowledge.py` | `~/Projects/zelbi.ai/backend/app/schemas/knowledge.py` | verbatim |
| `knowledge-eval/app/services/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/app/services/knowledge/__init__.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/__init__.py` | verbatim |
| `knowledge-eval/app/services/knowledge/answer.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/answer.py` | verbatim |
| `knowledge-eval/app/services/knowledge/answer_eval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/answer_eval.py` | verbatim |
| `knowledge-eval/app/services/knowledge/chunking.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/chunking.py` | verbatim |
| `knowledge-eval/app/services/knowledge/eval_cases.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/eval_cases.py` | verbatim |
| `knowledge-eval/app/services/knowledge/frontmatter.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/frontmatter.py` | verbatim |
| `knowledge-eval/app/services/knowledge/ingestion.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/ingestion.py` | verbatim |
| `knowledge-eval/app/services/knowledge/retrieval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/retrieval.py` | verbatim |
| `knowledge-eval/app/services/knowledge/retrieval_eval.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/retrieval_eval.py` | verbatim |
| `knowledge-eval/app/services/knowledge/validation.py` | `~/Projects/zelbi.ai/backend/app/services/knowledge/validation.py` | verbatim |
| `knowledge-eval/conftest.py` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/cx/cx-loan-escalations.md` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/internal/internal-loan-thresholds.md` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/public/tool-library-loans.md` | authored for this repository | authored / modified |
| `knowledge-eval/netblock.py` | authored for this repository | authored / modified |
| `knowledge-eval/pytest.ini` | authored for this repository | authored / modified |
| `knowledge-eval/requirements.txt` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/scripts/answer_knowledge.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/ingest_policy_docs.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/retrieve_knowledge.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/run_knowledge_answer_eval.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/run_knowledge_retrieval_eval.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/seed_eval_cases.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/__init__.py` | `~/Projects/zelbi.ai/backend/app/__init__.py` | verbatim |
| `knowledge-eval/tests/test_knowledge_answer.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_ask_endpoint.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_eval_seed.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_ingestion.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_models.py` | `~/Projects/zelbi.ai/backend/tests/test_knowledge_models.py` | verbatim |
| `knowledge-eval/tests/test_knowledge_retrieval.py` | authored for this repository | authored / modified |

### `tooling` — 42 files

| File | Source | State |
|---|---|---|
| `agents/build-error-resolver.md` | authored for this repository | authored / modified |
| `agents/code-reviewer.md` | authored for this repository | authored / modified |
| `agents/debugger.md` | `~/.claude/agents/debugger.md` | verbatim |
| `agents/deployment-engineer.md` | `~/.claude/agents/deployment-engineer.md` | verbatim |
| `agents/frontend-developer.md` | `~/.claude/agents/frontend-developer.md` | verbatim |
| `agents/planner.md` | authored for this repository | authored / modified |
| `agents/python-pro.md` | `~/.claude/agents/python-pro.md` | verbatim |
| `agents/security-reviewer.md` | authored for this repository | authored / modified |
| `agents/sql-pro.md` | `~/.claude/agents/sql-pro.md` | verbatim |
| `hooks/brevity-hook.py` | `~/.claude/hooks/brevity-hook.py` | verbatim |
| `hooks/conduct_lesson_parser.py` | `~/.claude/hooks/conduct_lesson_parser.py` | verbatim |
| `hooks/decision-ownership-hook.py` | `~/.claude/hooks/decision-ownership-hook.py` | verbatim |
| `hooks/git-push-blocker.sh` | `~/.claude/hooks/git-push-blocker.sh` | verbatim |
| `hooks/js-syntax-check.sh` | `~/.claude/hooks/js-syntax-check.sh` | verbatim |
| `hooks/pacing-hook.py` | `~/.claude/hooks/pacing-hook.py` | verbatim |
| `hooks/plain-english-hook.py` | `~/.claude/hooks/plain-english-hook.py` | verbatim |
| `hooks/pre-compact.sh` | `~/.claude/hooks/pre-compact.sh` | verbatim |
| `hooks/prompt-format-hook.py` | `~/.claude/hooks/prompt-format-hook.py` | verbatim |
| `hooks/session-end.sh` | `~/.claude/hooks/session-end.sh` | verbatim |
| `hooks/session-start.sh` | `~/.claude/hooks/session-start.sh` | verbatim |
| `hooks/test_conduct_lesson_parser.py` | `~/.claude/hooks/test_conduct_lesson_parser.py` | verbatim |
| `rules-registry/BREAKAGE-LOG.md` | `~/Projects/ai-rules/BREAKAGE-LOG.md` | verbatim |
| `rules-registry/RULE-FIX-BLUEPRINT-v2.md` | authored for this repository | authored / modified |
| `rules-registry/RULE-FIX-BLUEPRINT-v3.md` | authored for this repository | authored / modified |
| `rules-registry/RULES-REGISTRY.md` | `~/Projects/ai-rules/RULES-REGISTRY.md` | verbatim |
| `rules-registry/aibs-core-rules.md` | `~/Projects/ai-rules/aibs-core-rules.md` | verbatim |
| `rules-registry/command-center-v7-rules.md` | `~/Projects/ai-rules/command-center-v7-rules.md` | verbatim |
| `rules-registry/my-assistant-rules.md` | authored for this repository | authored / modified |
| `rules-registry/preferences-archive-2026-07-17.md` | `~/Projects/ai-rules/preferences-archive-2026-07-17.md` | verbatim |
| `rules-registry/tools-bench-cli.md` | `~/Projects/ai-rules/tools-bench-cli.md` | verbatim |
| `rules-registry/tools-cursor.md` | `~/Projects/ai-rules/tools-cursor.md` | verbatim |
| `rules-registry/tools-erpnext-desk.md` | `~/Projects/ai-rules/tools-erpnext-desk.md` | verbatim |
| `rules-registry/tools-frappe-cloud.md` | `~/Projects/ai-rules/tools-frappe-cloud.md` | verbatim |
| `rules-registry/zelbi-rules.md` | `~/Projects/ai-rules/zelbi-rules.md` | verbatim |
| `skills/SYNC_MAP.md` | `~/.claude/skills/SYNC_MAP.md` | verbatim |
| `skills/cowork-prompts/SKILL.md` | `~/.claude/skills/cowork-prompts/SKILL.md` | verbatim |
| `skills/debug-mode/SKILL.md` | `~/.claude/skills/debug-mode/SKILL.md` | verbatim |
| `skills/handoff-protocol/SKILL.md` | `~/.claude/skills/handoff-protocol/SKILL.md` | verbatim |
| `skills/plan-validate-execute/SKILL.md` | `~/.claude/skills/plan-validate-execute/SKILL.md` | verbatim |
| `skills/prompting-patterns/SKILL.md` | `~/.claude/skills/prompting-patterns/SKILL.md` | verbatim |
| `skills/review-claudemd/SKILL.md` | `~/.claude/skills/review-claudemd/SKILL.md` | verbatim |
| `skills/verification-techniques/SKILL.md` | `~/.claude/skills/verification-techniques/SKILL.md` | verbatim |

### `verification` — 3 files

| File | Source | State |
|---|---|---|
| `netblock.py` | authored for this repository | authored / modified |
| `pytest-summary-2026-09-03.txt` | authored for this repository | authored / modified |
| `repo-metrics-2026-09-03.md` | authored for this repository | authored / modified |

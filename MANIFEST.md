# Manifest

Every file in this repository: where it came from, and what was removed.

Compiled by hashing each output file against the private sources, so
"verbatim" below means **byte-identical to the private original**, not "roughly
unchanged". Anything not byte-identical is listed as authored or modified and,
if it came from a private file, has an entry in §1 or §2.

- **231 files** · 63 verbatim · 168 authored or modified (refresh of 2026-11-17)
- Source commit for Zelbi material: `4772472bdf2f370ea3b54971d8e94c9474cf7aaf`
  (`4772472b`, 2026-11-16). Every Zelbi-sourced file was re-hashed against the
  tree at that commit, read from a clean clone, never from a working tree. Two
  runnable-package files copied at `8875721` have changed in Zelbi since; §5
  says which.
- Material from outside Zelbi (`tooling/`, the rules registry, the skills) is
  the 2026-09-03 snapshot, unchanged since; its rows carry that date.
- Compiled 2026-11-17. The previous manifest (2026-10-03, Zelbi `8875721`,
  284 files) is in git history at `58185c6`; the one before it (2026-09-03,
  Zelbi `3413d028`, 227 files) at `e4ce1b4`.
- §1–§4 were written at `8875721`. Where the 2026-11-17 refresh changed one of
  their statements, the change is marked **(2026-11-17)**. §5 is regenerated.
  §6 (code to excerpts) and §7 (decisions added, and every redaction) are new.

---

## 1. Removals — every sanitization, with file and line range

Line ranges are in the **source** file at `8875721`.

### 1.1 Scam-rule table

| File | Lines | Removed | Replaced with |
|---|---|---|---|
| `code/message_guard/scam_detection.py` | 148–460 (313 lines) | The Rule-3 and Rule-6 pattern tables and deflect regexes: every compiled regular expression, each an alternation of literal trigger phrases and their evasion variants, across payment brands, phone numbers and phone solicitation, urgency, currency and pricing, email and email solicitation, social handles, links, scheduling intent, addresses, cancel/confirm intent, and the picker-question deflect categories. | `# rule table withheld` plus a paragraph naming every category and stating that the normalizer above (95–146) and the dispatchers below (461 onward) are intact. |
| `code/message_guard/scam_detection.py` | 38–39 | Listing-tempo values: the minimum interval between consecutive listings and the per-day ceiling. | The symbol `WITHHELD`, with the guard's shape stated in a comment. |
| `code/message_guard/scam_detection.py` | 51 | The per-day ceiling, restated as a number in rule 2's description text. | "more than the (withheld) daily ceiling". |
| `code/message_guard/scam_detection.py` | 9–10 | An absolute local filesystem path to a session plan file. | A generic reference to "the session plan file". |
| `code/message_guard/scam_detection.py` | — | — | A six-line banner added at the top saying the file is sanitized and pointing here. |

The 24-hour window rule 2 counts over is kept, as it was in September: it is
the shape of the rule, not its tuning.

**(2026-11-17)** `code/message_guard/scam_detection.py` is no longer published
(§6). The rule table stays withheld. The excerpts quote only the normalizer and
the rule-status table.

**Why:** publishing the alternation list publishes the evasion recipe. The
normalizer — which decodes evasion *before* any pattern runs, and is where the
actual engineering is — is kept in full, as is every dispatcher, so a reviewer
can see how rules compose and where enforcement happens.

### 1.2 Trust-model constants — no longer withheld

In September the completion award, deduction weights, heal threshold, score
bounds, strike threshold, windows and timeout were replaced with `WITHHELD` in
`trust_service.py`, `strike_service.py`, `test_trust_service.py` and four
decision records.

**Ruling 2026-10-03 (Nick): drop the exclusion.** The refresh found that the
September copies already stated several of the values elsewhere: in
`test_trust_service.py` test names, in `test_claim_score_delta.py` and
`test_strike.py`, and in `strike_service.py` docstrings, comments and
user-facing notice copy. The notice copy is what users read, so the values were
never secret from users. All four files are now **verbatim** at `8875721`,
`test_dispute_suspension.py` is published whole, and D21, D182, D183 and D299
are now unredacted.

The September copies remain in this repository's public git history. History
was not rewritten.

### 1.3 Policy corpus

The fifteen real policy documents (8 public, 4 CX, 3 internal) and the real
22-case eval file are **not published in any form** — not their text, not
their titles, not their paths in quoted output. `runnable/knowledge-eval/docs/policy/`
contains three synthetic documents about an invented tool-lending library, one
per tier, and `runnable/knowledge-eval/app/data/knowledge_eval_cases.json`
contains 22 invented questions in the same contract and the same 12-answer /
10-refusal split. The ingestion, chunking, embedding, retrieval, answer and eval
code is verbatim.

### 1.4 Third-party identity and account identifiers

| Scope | Removed | Replaced with |
|---|---|---|
| `tooling/agents/{build-error-resolver,code-reviewer,planner,security-reviewer}.md`, `tooling/rules-registry/{my-assistant-rules,RULE-FIX-BLUEPRINT-v2,RULE-FIX-BLUEPRINT-v3}.md` | The construction company's real name — 11 occurrences across 7 files (September, unchanged). | "the construction company" / "construction-company operations dashboard". |
| Everywhere | The company owner's real name. | Never written. |
| `05-process/handoff-protocol.md` (2 paths), `tooling/skills/handoff-protocol/SKILL.md` (2 paths) | The company's initialism in a private note directory path (September, unchanged). | `<project>`. |
| `tooling/skills/SYNC_MAP.md` lines 8–9; `tooling/rules-registry/RULES-REGISTRY.md` lines 178, 197, 203; `tooling/rules-registry/my-assistant-rules.md` lines 6, 15, 38, 43; `tooling/rules-registry/command-center-v7-rules.md` lines 100, 106, 112, 126; `tooling/rules-registry/RULE-FIX-BLUEPRINT-v2.md` line 219; `tooling/rules-registry/RULE-FIX-BLUEPRINT-v3.md` line 411; `tooling/rules-registry/zelbi-rules.md` line 253; `05-process/behavioral-rulebook.md` lines 188, 207, 213 | The company's two-letter initialism in prose and rule names, missed in September and published since. Removed 2026-10-04; the earlier copies stay in git history. | "the client" ("THE CLIENT" inside the upper-case rule name M1; "The client" at the start of a sentence). |
| `tooling/hooks/session-start.sh` line 65; `tooling/skills/cowork-prompts/SKILL.md` lines 10, 20, 25 | The same initialism inside filesystem paths: a note-vault folder and a screenshots folder. Removed 2026-10-04. | `<project>` (`MyVault/<project>`, `Desktop/<project>-Screenshots/`). |
| `code/admin_ops/test_watcher.py` lines 18, 73, 224, 318, 327 | Zelbi's Sentry organisation slug, as a subdomain (4) and in an API path (1). | `example-org`. |
| `code/credits_devicecheck/test_devicecheck_service.py` line 17 | Zelbi's real Apple Developer Team ID, used as the test's issuer. The same literal is the default in the unpublished `config.py`. | `TEAMID0000`. |

`code/admin_ops/test_watcher.py:16` keeps its webhook secret literal: it is a
fixture value invented for the test (`sentry_test_secret_…`), not a real secret.

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
| `docs/agents/backlog.md`, `00-current-state.md`, `zelbi-build-map.md`, the session log | Internal control documents. Cited by line where a write-up needs it; never copied. |
| `docs/agents/audit-evidence/` and the legal/compliance audit documents | Reduced to one paragraph in `02-architecture/tradeoffs.md`. |
| Any code from the construction-company repositories | Described in `02-architecture/system-overview.md`, no code. The LEDGER cites one private file by path and line (`my-assistant/routes/invoices.py:240-283`) without publishing it. |
| `web/dashboard/` — the operator console's single HTML file | Carries the managed-database project reference and publishable key, the production API host and seed names. Described in `02-architecture/admin-and-ops.md`; not published. |
| `backend/app/config.py` | Holds account identifiers (Apple Team ID, Sentry organisation, production host, app id). Cited by line only. |
| `backend/app/routers/claims.py`, `listings.py`, `users.py` whole | Large surfaces with nothing to add beyond the cited lines. Cited as excerpts with `file:line@8875721`. |
| `backend/app/services/referral_service.py`, `email_templates.py`, `email_html/` | Not needed by any claim; cited by line where a write-up uses them. |
| The agent-foundation work (D569–D573 and its spec) | Out of scope for this refresh. Counted in the 564 decisions, never named or selected. **(2026-11-17)** D577, D578, D579 and D580 from the support-agent work are now published, because case study 08 cites them; the spec and D569–D573 are still not. |
| Every `gsd-*` agent, hook, skill and command | Installed framework, not Nick's work. 15 agent definitions and 3 hooks excluded. |
| `~/.claude/commands/` | Contains only `gsd`. |
| `tooling/skills/learned/` (16 files) | Auto-generated queue stubs — a repeated prompt template plus a local transcript path. No content, and they leak local paths. |
| `ai-rules/db-auto-detailing-rules.md` | That project is excluded from all recruiting material by Nick's own decision. |
| `03-decisions/ai/D213.md` | D213 — withheld from the public repository; available on request. |
| `ai-rules/zelbi-rules.md.bak` | Backup file. |
| Real user rows, seed data resembling real people | None copied. |

### 1.7 Could not be sourced — left out, with the reason

| Wanted | Why it is not here |
|---|---|
| `tooling/cursor/` — Cursor rules and commands | **No such files exist.** There is no `.cursor/rules` directory and no `.cursorrules` file in the Zelbi repository, and `~/.cursor` holds only IDE state. The Cursor-facing rules are a single file, `tools-cursor.md`, which lives in the rules registry and is copied there. |
| Verbatim quotes from the Phase 1 survey and the Phase 2 verification report | **Neither document exists on disk.** The full test suite and every repository metric were re-run from scratch instead — on 2026-09-03 and again on 2026-10-03 — and recorded with their commands in `verification/`. |
| A reproduction of "sixteen block call sites" | **Never reproduced.** 13 at `3413d028`; 14 helper call sites plus 4 inlined feed subqueries at `8875721`. The résumé states no count. See `LIMITATIONS.md`. |
| A regression test for the prepared-statement fix | Not constructible: it needs a transaction-mode pooler multiplexing callers onto one backend. Stated in the write-up rather than claimed. |
| A test of the hybrid retrieval path | **None exists in Zelbi.** Not written here either: a test in this repository would be evidence of something the product itself does not test. **(2026-11-17)** Seven now exist in Zelbi (`backend/tests/test_knowledge_hybrid_path.py`, `0cd7e3ce`). They are cited, not copied. |

---

## 2. Modifications that are not removals

| File(s) | Change |
|---|---|
| `03-decisions/*/*.md` | Each record is copied verbatim from the decision log at `8875721` beneath a four-line header (source file and line, theme, reproduction note), which is why they hash as authored. |
| `runnable/knowledge-eval/app/config.py` | Authored stand-in for production's settings: one field, the Voyage API key, pinned to the empty string so the package never makes a network call. |
| `runnable/knowledge-eval/app/services/api_abuse.py` | Authored stand-in: same name and signature as production's operator-signal writer, logs instead of writing a console row. |
| `runnable/knowledge-eval/requirements.txt`, `conftest.py` | Comment wording updated for the refresh ("full Alembic" in place of a September revision count). No dependency or fixture changed. |
| `runnable/knowledge-eval/scripts/*.py` (6 files) | One trailing comment added to the path-shim line, marking that the package root replaces the private repository's `backend/` root. No logic changed. |
| `runnable/knowledge-eval/tests/*.py` (5 of 6 files) | Adapted from the private tests at `3413d028` and re-pointed at the synthetic corpus: repository-root depth, document paths, document counts, and the questions the parametrised cases name. Two structural adaptations, both forced by real properties of the system and both explained in `runnable/knowledge-eval/README.md`. **No assertion was weakened and no test was removed.** Not re-ported at `8875721`: the private tests' changes since then are real-corpus wording and an autouse sign-in fixture for production's account requirement, neither of which applies here. |
| `runnable/knowledge-eval/app/models.py` | The six knowledge tables are verbatim, including every check constraint and index. Imports and `Base` were reconstructed, and a minimal three-column `User` was added as a stand-in for the admin gate. |
| `runnable/knowledge-eval/docs/policy/public/tool-library-loans.md` | Authored. Its `implementation_status` is `locked_pending_build` so the composer's unbuilt-feature note path is exercised, as the private corpus document did. |
| `05-process/behavioral-rulebook.md`, `05-process/handoff-protocol.md` | Verbatim copies with a provenance comment prepended (which is why they hash as modified). The rulebook carries the §1.4 name redaction; the handoff protocol's session count was updated to "numbered through 473". |
| `code/*/routers_*.py`, `code/mobile/*`, `code/credits_devicecheck/{ios_,src_,mobile_utils_}*` | Renamed on copy to keep a flat folder readable (`routers/ai.py` → `routers_ai.py`, `utils/messages.ts` → `utils_messages.ts`, `modules/zelbi-device-check/ios/ZelbiDeviceCheckModule.swift` → `ios_ZelbiDeviceCheckModule.swift`). Contents byte-identical. |

---

## 3. The 48 decision records — selection, with reasons

Selected from 564 numbered decisions (the inclusive count at `8875721`; see
`03-decisions/INDEX.md` for the method and the September correction). The 44
September records were re-extracted verbatim at `8875721`; four were added on
2026-10-03, each read in full before it was selected (marked **new**).

### money (13)

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
| D533 | **New.** Disputes run by email, and the in-app notice is never sent. Records that a code path exists with no caller, and what must change if it is ever used — the reason no code creates a dispute today. |

### trust (13)

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
| D542 | **New.** The first-giveaway credit rules, including the Apple DeviceCheck spend gate. The ruling behind the résumé's DeviceCheck clause. |
| D544 | **New.** Referral credit rules: card matching, one iPhone per referred friend, caps. Selected partly because part of it (the iPhone rule) is not built — see `01-product-logic/device-check-credits.md`. |

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

### ai (6)

| D | Why selected |
|---|---|
| D18 | Two options, A/B, user picks and edits — the ruling that puts a human between the model and the database. |
| D87 | A recorded model failure mode (brand hallucination). The log naming what the model gets wrong. |
| D122 | Category-conditional photo requirements — product logic constraining a model input. |
| D438 | Implements D122 through one voice. Shows a decision travelling from ruling to interface. |
| D440 | Cached analysis still plays the beat — a small ruling that keeps a fast path from feeling broken. |
| D538 | **New.** Help abuse safeguards once embeddings cost money: sign-in, a per-account hourly limit, a 1,000-question daily ceiling, alerts. The ruling behind the résumé's daily embedding cap. |

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
timing — are the majority of the 564. They are real decisions and they show
craft, but in a domain the resume does not claim, so none were selected.

---


---

## 4. Secret scan

September's scan was a 19-pattern sweep whose patterns were never written
down, so it could not be re-run. It is replaced by
[`verification/secret-scan.sh`](verification/secret-scan.sh), which anyone can
run, in three layers:

1. **22 generic patterns, listed in the script:**
   - provider key prefixes: payment, LLM, embedding, cloud, Google, GitHub, Slack, telephony, managed database;
   - JWTs, PEM blocks, credentialed URLs, error-reporter DSNs, Postgres DSNs;
   - literal secret assignments and managed-host suffixes;
   - long hex and mixed-case base64 runs;
   - email addresses and absolute home paths.
2. **Project literals** from `verification/.scan-literals`, which is gitignored
   so the identifiers it searches for never enter the repository. It holds:
   - the construction company's name;
   - the Apple Team ID;
   - the production host;
   - the Sentry organisation's host and API path;
   - Nick's personal email and handle as an email local part.
3. **Every value in Zelbi's local env file** (`--env-file`), read into memory
   only: each value of 8+ characters, each line of a multi-line value, and the
   host of each URL. A hit would print the variable's name, never its value.

Run over all 284 files git would publish, at the commit this manifest
describes:

```
verification/secret-scan.sh --env-file ~/Projects/zelbi.ai/.env.local
```

**First pass: 891 hits across 7 classes, 781 of them `long-b64`.** That class
matched every long file path and test name. It was tightened to require upper
case, lower case and a digit, because a run of letters alone is a name, not a
key. **Final pass: 120 hits across 7 classes, every one read and benign.**

- **Zero hits** from the 65 literal and env-value needles.
- **Zero hits** in every key, token, PEM, JWT, credentialed-URL and DSN-with-host
  class.
- No file was edited to clear a hit; between passes only the pattern changed.

| Class | Hits | What they are |
|---|---|---|
| `email` | 50 | The published support address, and one `example.com` fixture address. |
| `home-path` | 30 | Absolute home paths in verbatim `tooling/` and `05-process/` files, plus this file naming them. |
| `long-b64` | 9 | Mixed-case identifiers: test names that embed a decision or ticket number (`test_D62_…`, `test_TLS_1_…`), long snapshot paths in this file and the tooling sync map. |
| `long-hex` | 15 | Git commit SHAs, and the SHA-256 of the pip freeze in the October pytest summary. |
| `managed-host` | 5 | The `example-org` replacement host in `test_watcher.py`, and this file naming it. |
| `postgres-dsn` | 6 | Credential-free `localhost` test URLs in the runnable package, the pytest summaries, and this file. |
| `secret-assign` | 5 | Invented test fixtures: a fake webhook secret, wrong-secret cases, and device-token fixtures. |

**Manual read.** Every file added or changed since `e4ce1b4` was read when it
was copied (Groups 3–5 of the refresh). That read is what caught the Team ID
and the Sentry organisation in §1.4. The 12,963 added lines were then swept for
what patterns miss:
- phone numbers: none;
- quoted personal names: none, apart from one fixture persona name in a test
  file (**(2026-11-17)** the file is no longer published, and the name is
  redacted here; §7);
- street addresses: none;
- coordinates in the region's latitude band: none;
- place names: only the résumé's own location lines.

### Resolved false positives, kept deliberately

- `support@zelbi.ai` is the product's published support address. It appears in
  the knowledge system's refusal template, the synthetic corpus and the tests
  that assert on it.
- `example-org.sentry.io` in `code/admin_ops/test_watcher.py` is the §1.4
  replacement (**(2026-11-17)** that file is no longer published; this line
  still names the host, so the scan still counts one hit here), and the `sentry_test_secret_…` and `device-token-never-logged`
  style literals are invented test fixtures.
- `postgresql://localhost/<db>` strings are credential-free local test URLs. A
  reviewer needs them to run the package.
- Commit SHAs are published deliberately, so a reviewer can locate any change in
  the private history.
- Absolute `/Users/nickbroyzer/...` paths remain in some `tooling/` and
  `05-process/` files. They are kept **verbatim on purpose**: these are the
  scripts as they actually run, and the username is Nick's own public handle.
  `tooling/README.md` says so.
- `tooling/rules-registry/RULE-FIX-BLUEPRINT-v3.md` lists payment-provider key
  prefixes with no values attached. It is documentation of a detection gate's
  pattern list.

### 2026-11-17 run

Run over all 231 files git would publish, before the refresh commit, with the
same command and the same three layers (99 literal and env-value needles):

```
verification/secret-scan.sh --env-file ~/Projects/zelbi.ai/.env.local
```

**Final pass: 112 hits across 6 classes, every one read and benign:** `email` 31, `home-path` 30, `long-b64` 5, `long-hex` 38, `managed-host` 1, `postgres-dsn` 7.

- **Zero hits** from the literal and env-value needles.
- **Zero hits** in every key, token, PEM, JWT and credentialed-URL class. A
  first pass found one `url-credentials` hit: the CI workflow's fake
  `placeholder:placeholder@localhost` database URL, quoted in the new pytest
  summary. It was abbreviated to `<placeholder DSN>`, and the `.supabase.co`
  placeholder URL beside it to `<placeholder URL>`.
- The classes that remain are the September and October ones: the published
  support address, commit SHAs (now also on line 4 of each `EXCERPTS.md` and in
  the new verification files), credential-free `localhost` test URLs, home
  paths in verbatim `tooling/` files, mixed-case identifiers, and one
  `example-org` host named in this file.

A second sweep, by `grep`, for what the brief named: `@` addresses, the
managed-database project reference, PaymentIntent ids (`pi_` and 20 or more
characters), `sk_`, `whsec_`, the Apple Team ID, the secrets manager's name,
the deployment and managed-database host suffixes, the seed test-persona names
and the four account email addresses.

- `@` addresses: only the published support address.
- The four account addresses, the project reference, the Team ID, real-shaped
  PaymentIntent ids and both host suffixes: none.
- The secrets manager's name: five hits, all redacted (§7.2).
- Seed test-persona names: four occurrences of three names, all redacted (§7.2).
- `whsec_` and `sk_`: two documentation lines that name the prefixes with no
  value (the scanner's own pattern list and `RULE-FIX-BLUEPRINT-v3.md`), one
  `"sk_test"` literal in `code/admin_ops/test_admin_money.py` (the placeholder
  key argument of the Stripe SDK's `construct_from`, no value), and substrings of
  `ask_` and `task_`. All benign; none removed.

---

## 5. Full file list

Generated on 2026-11-17 by hashing each file against the Zelbi tree at `4772472b`,
read from a clean clone. "verbatim" means byte-identical to the path shown.
A file copied at `8875721` whose source has changed since says so. Files from
outside Zelbi that have not changed since 2026-09-03 carry that snapshot's
recorded row.

### `(repository root)` — 6 files

| File | Source | State |
|---|---|---|
| `.gitignore` | authored for this repository | authored / modified |
| `LEDGER.md` | authored for this repository | authored / modified |
| `LICENSE` | authored for this repository | authored / modified |
| `LIMITATIONS.md` | authored for this repository | authored / modified |
| `MANIFEST.md` | authored for this repository | authored / modified |
| `README.md` | authored for this repository | authored / modified |

### `01-product-logic` — 6 files

| File | Source | State |
|---|---|---|
| `device-check-credits.md` | authored for this repository | authored / modified |
| `failure-state-matrix.md` | authored for this repository | authored / modified |
| `location-privacy-design.md` | authored for this repository | authored / modified |
| `marketplace-state-machine.md` | authored for this repository | authored / modified |
| `private-photo-access.md` | authored for this repository | authored / modified |
| `trust-and-safety-design.md` | authored for this repository | authored / modified |

### `02-architecture` — 7 files

| File | Source | State |
|---|---|---|
| `admin-and-ops.md` | authored for this repository | authored / modified |
| `ai-boundary.md` | authored for this repository | authored / modified |
| `data-and-migrations.md` | authored for this repository | authored / modified |
| `hybrid-retrieval.md` | authored for this repository | authored / modified |
| `money-path.md` | authored for this repository | authored / modified |
| `system-overview.md` | authored for this repository | authored / modified |
| `tradeoffs.md` | authored for this repository | authored / modified |

### `03-decisions` — 62 files

| File | Source | State |
|---|---|---|
| `INDEX.md` | authored for this repository | authored / modified |
| `ai/D122.md` | authored for this repository | authored / modified |
| `ai/D18.md` | authored for this repository | authored / modified |
| `ai/D438.md` | authored for this repository | authored / modified |
| `ai/D440.md` | authored for this repository | authored / modified |
| `ai/D537.md` | authored for this repository | authored / modified |
| `ai/D538.md` | authored for this repository | authored / modified |
| `ai/D578.md` | authored for this repository | authored / modified |
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
| `money/D533.md` | authored for this repository | authored / modified |
| `ops/D198.md` | authored for this repository | authored / modified |
| `ops/D200.md` | authored for this repository | authored / modified |
| `ops/D238.md` | authored for this repository | authored / modified |
| `ops/D274.md` | authored for this repository | authored / modified |
| `ops/D275.md` | authored for this repository | authored / modified |
| `ops/D276.md` | authored for this repository | authored / modified |
| `ops/D277.md` | authored for this repository | authored / modified |
| `ops/D410.md` | authored for this repository | authored / modified |
| `ops/D442.md` | authored for this repository | authored / modified |
| `ops/D444.md` | authored for this repository | authored / modified |
| `ops/D625.md` | authored for this repository | authored / modified |
| `ops/D627.md` | authored for this repository | authored / modified |
| `ops/D629.md` | authored for this repository | authored / modified |
| `ops/D635.md` | authored for this repository | authored / modified |
| `privacy/D125.md` | authored for this repository | authored / modified |
| `privacy/D137.md` | authored for this repository | authored / modified |
| `privacy/D215.md` | authored for this repository | authored / modified |
| `privacy/D320.md` | authored for this repository | authored / modified |
| `privacy/D321.md` | authored for this repository | authored / modified |
| `privacy/D322.md` | authored for this repository | authored / modified |
| `privacy/D323.md` | authored for this repository | authored / modified |
| `privacy/D402.md` | authored for this repository | authored / modified |
| `privacy/D636.md` | authored for this repository | authored / modified |
| `privacy/D637.md` | authored for this repository | authored / modified |
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
| `trust/D542.md` | authored for this repository | authored / modified |
| `trust/D544.md` | authored for this repository | authored / modified |
| `trust/D577.md` | authored for this repository | authored / modified |
| `trust/D579.md` | authored for this repository | authored / modified |
| `trust/D580.md` | authored for this repository | authored / modified |

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
| `check-build-map.sh` | `tools/check-build-map.sh`@8875721 | verbatim |
| `enforcement-hooks.md` | authored for this repository | authored / modified |
| `handoff-protocol.md` | authored for this repository | authored / modified |
| `model-routing.md` | authored for this repository | authored / modified |
| `verification-gates.md` | authored for this repository | authored / modified |

### `06-case-studies` — 10 files

| File | Source | State |
|---|---|---|
| `01-reminder-that-never-fired.md` | draft `case-study-01-reminder-that-never-fired.md` (2026-11-17) | verbatim |
| `02-consent-before-the-tap.md` | draft `case-study-02-consent-before-the-tap.md` (2026-11-17) | verbatim |
| `03-an-old-notification-opened-a-strangers-pickup.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `04-one-error-code-with-two-opposite-meanings.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `05-rejected-by-apple-then-proving-the-feature-needed-the-permission.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `06-live-activities-a-200-that-means-nothing.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `07-help-search-fix-the-content-first-then-add-vectors.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `08-the-support-agent-4-of-10-then-9-of-10-then-4-of-4.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `09-a-security-pass-before-submitting-to-apple.md` | split verbatim from draft `case-studies-03-09.md` (2026-11-17); concatenated with the separators, byte-identical | authored / modified |
| `INDEX.md` | authored for this repository | authored / modified |

### `code` — 24 files

| File | Source | State |
|---|---|---|
| `admin_ops/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `admin_ops/test_admin_actions.py` | `backend/tests/test_admin_actions.py`@4772472b | verbatim |
| `admin_ops/test_admin_authorization.py` | `backend/tests/test_admin_authorization.py`@4772472b | verbatim |
| `admin_ops/test_admin_claims.py` | `backend/tests/test_admin_claims.py`@4772472b | verbatim |
| `admin_ops/test_admin_disputes.py` | `backend/tests/test_admin_disputes.py`@4772472b | verbatim |
| `admin_ops/test_admin_health.py` | `backend/tests/test_admin_health.py`@4772472b | verbatim |
| `admin_ops/test_admin_listings.py` | `backend/tests/test_admin_listings.py`@4772472b | verbatim |
| `admin_ops/test_admin_money.py` | `backend/tests/test_admin_money.py`@4772472b | verbatim |
| `ai_service/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `ai_service/test_ai.py` | `backend/tests/test_ai.py`@4772472b | verbatim |
| `ai_service/test_ai_object_key_ownership.py` | `backend/tests/test_ai_object_key_ownership.py`@4772472b | verbatim |
| `coordinate_privacy/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `credits_devicecheck/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `database/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `database/test_rate_limit_mounts.py` | `backend/tests/test_rate_limit_mounts.py`@4772472b | verbatim |
| `jobs/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `jobs/test_cron_reminders.py` | `backend/tests/test_cron_reminders.py`@4772472b | verbatim |
| `knowledge/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `message_guard/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `mobile/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `payments/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `payments/test_stripe_billing.py` | `backend/tests/test_stripe_billing.py`@4772472b | verbatim |
| `photo_access/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |
| `trust/EXCERPTS.md` | authored: excerpts from Zelbi `4772472b` (§6) | authored / modified |

### `runnable` — 48 files

| File | Source | State |
|---|---|---|
| `knowledge-eval/README.md` | authored for this repository | authored / modified |
| `knowledge-eval/app/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/config.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/data/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/data/knowledge_eval_cases.json` | authored for this repository | authored / modified |
| `knowledge-eval/app/database.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/dependencies.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/main.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/models.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/routers/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/routers/admin.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/routers/knowledge.py` | `backend/app/routers/knowledge.py`@4772472b | verbatim |
| `knowledge-eval/app/schemas/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/schemas/knowledge.py` | `backend/app/schemas/knowledge.py`@4772472b | verbatim |
| `knowledge-eval/app/services/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/services/api_abuse.py` | authored for this repository | authored / modified |
| `knowledge-eval/app/services/knowledge/__init__.py` | `backend/app/services/knowledge/__init__.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/answer.py` | `backend/app/services/knowledge/answer.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/answer_eval.py` | `backend/app/services/knowledge/answer_eval.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/chunking.py` | `backend/app/services/knowledge/chunking.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/embeddings.py` | `backend/app/services/knowledge/embeddings.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/eval_cases.py` | `backend/app/services/knowledge/eval_cases.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/frontmatter.py` | `backend/app/services/knowledge/frontmatter.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/ingestion.py` | `backend/app/services/knowledge/ingestion.py`@8875721 | verbatim at `8875721`; source changed by `4772472b` |
| `knowledge-eval/app/services/knowledge/retrieval.py` | `backend/app/services/knowledge/retrieval.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/retrieval_eval.py` | `backend/app/services/knowledge/retrieval_eval.py`@4772472b | verbatim |
| `knowledge-eval/app/services/knowledge/validation.py` | `backend/app/services/knowledge/validation.py`@8875721 | verbatim at `8875721`; source changed by `4772472b` |
| `knowledge-eval/conftest.py` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/cx/cx-loan-escalations.md` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/internal/internal-loan-thresholds.md` | authored for this repository | authored / modified |
| `knowledge-eval/docs/policy/public/tool-library-loans.md` | authored for this repository | authored / modified |
| `knowledge-eval/netblock.py` | authored for this repository | authored / modified |
| `knowledge-eval/pytest.ini` | authored for this repository | authored / modified |
| `knowledge-eval/requirements.txt` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/scripts/answer_knowledge.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/ingest_policy_docs.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/retrieve_knowledge.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/run_knowledge_answer_eval.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/run_knowledge_retrieval_eval.py` | authored for this repository | authored / modified |
| `knowledge-eval/scripts/seed_eval_cases.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/__init__.py` | `backend/app/__init__.py`@4772472b | verbatim |
| `knowledge-eval/tests/test_knowledge_answer.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_ask_endpoint.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_eval_seed.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_ingestion.py` | authored for this repository | authored / modified |
| `knowledge-eval/tests/test_knowledge_models.py` | `backend/tests/test_knowledge_models.py`@4772472b | verbatim |
| `knowledge-eval/tests/test_knowledge_retrieval.py` | authored for this repository | authored / modified |

### `tooling` — 43 files

| File | Source | State |
|---|---|---|
| `README.md` | authored for this repository | authored / modified |
| `agents/build-error-resolver.md` | authored for this repository | authored / modified |
| `agents/code-reviewer.md` | authored for this repository | authored / modified |
| `agents/debugger.md` | `~/.claude/agents/debugger.md` (snapshot 2026-09-03) | verbatim |
| `agents/deployment-engineer.md` | `~/.claude/agents/deployment-engineer.md` (snapshot 2026-09-03) | verbatim |
| `agents/frontend-developer.md` | `~/.claude/agents/frontend-developer.md` (snapshot 2026-09-03) | verbatim |
| `agents/planner.md` | authored for this repository | authored / modified |
| `agents/python-pro.md` | `~/.claude/agents/python-pro.md` (snapshot 2026-09-03) | verbatim |
| `agents/security-reviewer.md` | authored for this repository | authored / modified |
| `agents/sql-pro.md` | `~/.claude/agents/sql-pro.md` (snapshot 2026-09-03) | verbatim |
| `hooks/brevity-hook.py` | `~/.claude/hooks/brevity-hook.py` (snapshot 2026-09-03) | verbatim |
| `hooks/conduct_lesson_parser.py` | `~/.claude/hooks/conduct_lesson_parser.py` (snapshot 2026-09-03) | verbatim |
| `hooks/decision-ownership-hook.py` | `~/.claude/hooks/decision-ownership-hook.py` (snapshot 2026-09-03) | verbatim |
| `hooks/git-push-blocker.sh` | `~/.claude/hooks/git-push-blocker.sh` (snapshot 2026-09-03) | verbatim |
| `hooks/js-syntax-check.sh` | `~/.claude/hooks/js-syntax-check.sh` (snapshot 2026-09-03) | verbatim |
| `hooks/pacing-hook.py` | `~/.claude/hooks/pacing-hook.py` (snapshot 2026-09-03) | verbatim |
| `hooks/plain-english-hook.py` | `~/.claude/hooks/plain-english-hook.py` (snapshot 2026-09-03) | verbatim |
| `hooks/pre-compact.sh` | `~/.claude/hooks/pre-compact.sh` (snapshot 2026-09-03) | verbatim |
| `hooks/prompt-format-hook.py` | `~/.claude/hooks/prompt-format-hook.py` (snapshot 2026-09-03) | verbatim |
| `hooks/session-end.sh` | `~/.claude/hooks/session-end.sh` (snapshot 2026-09-03) | verbatim |
| `hooks/session-start.sh` | modified from `~/.claude/hooks/session-start.sh` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `hooks/test_conduct_lesson_parser.py` | `~/.claude/hooks/test_conduct_lesson_parser.py` (snapshot 2026-09-03) | verbatim |
| `rules-registry/BREAKAGE-LOG.md` | `~/Projects/ai-rules/BREAKAGE-LOG.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/RULE-FIX-BLUEPRINT-v2.md` | authored for this repository | authored / modified |
| `rules-registry/RULE-FIX-BLUEPRINT-v3.md` | authored for this repository | authored / modified |
| `rules-registry/RULES-REGISTRY.md` | modified from `~/Projects/ai-rules/RULES-REGISTRY.md` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `rules-registry/aibs-core-rules.md` | `~/Projects/ai-rules/aibs-core-rules.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/command-center-v7-rules.md` | modified from `~/Projects/ai-rules/command-center-v7-rules.md` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `rules-registry/my-assistant-rules.md` | authored for this repository | authored / modified |
| `rules-registry/preferences-archive-2026-07-17.md` | `~/Projects/ai-rules/preferences-archive-2026-07-17.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/tools-bench-cli.md` | `~/Projects/ai-rules/tools-bench-cli.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/tools-cursor.md` | `~/Projects/ai-rules/tools-cursor.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/tools-erpnext-desk.md` | `~/Projects/ai-rules/tools-erpnext-desk.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/tools-frappe-cloud.md` | `~/Projects/ai-rules/tools-frappe-cloud.md` (snapshot 2026-09-03) | verbatim |
| `rules-registry/zelbi-rules.md` | modified from `~/Projects/ai-rules/zelbi-rules.md` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `skills/SYNC_MAP.md` | modified from `~/.claude/skills/SYNC_MAP.md` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `skills/cowork-prompts/SKILL.md` | modified from `~/.claude/skills/cowork-prompts/SKILL.md` (snapshot 2026-09-03) (§1.4) | authored / modified |
| `skills/debug-mode/SKILL.md` | `~/.claude/skills/debug-mode/SKILL.md` (snapshot 2026-09-03) | verbatim |
| `skills/handoff-protocol/SKILL.md` | `~/.claude/skills/handoff-protocol/SKILL.md` (snapshot 2026-09-03) | verbatim |
| `skills/plan-validate-execute/SKILL.md` | `~/.claude/skills/plan-validate-execute/SKILL.md` (snapshot 2026-09-03) | verbatim |
| `skills/prompting-patterns/SKILL.md` | `~/.claude/skills/prompting-patterns/SKILL.md` (snapshot 2026-09-03) | verbatim |
| `skills/review-claudemd/SKILL.md` | `~/.claude/skills/review-claudemd/SKILL.md` (snapshot 2026-09-03) | verbatim |
| `skills/verification-techniques/SKILL.md` | `~/.claude/skills/verification-techniques/SKILL.md` (snapshot 2026-09-03) | verbatim |

### `verification` — 11 files

| File | Source | State |
|---|---|---|
| `ci-run-2026-11-17.md` | authored for this repository | authored / modified |
| `draft-fact-check-2026-11-17.md` | authored for this repository | authored / modified |
| `netblock.py` | authored for this repository | authored / modified |
| `pytest-summary-2026-09-03.txt` | authored for this repository | authored / modified |
| `pytest-summary-2026-10-03.txt` | authored for this repository | authored / modified |
| `pytest-summary-2026-11-17.txt` | authored for this repository | authored / modified |
| `repo-metrics-2026-09-03.md` | authored for this repository | authored / modified |
| `repo-metrics-2026-10-03.md` | authored for this repository | authored / modified |
| `repo-metrics-2026-11-17.md` | authored for this repository | authored / modified |
| `resume-v8-numbers-2026-10-03.md` | authored for this repository | authored / modified |
| `secret-scan.sh` | authored for this repository | authored / modified |

---

## 6. Code to excerpts (2026-11-17)

**Reason, for every row in this section: Nick's policy, "show the work, not the
recipe".** Write-ups, decisions, test results and short code excerpts stay;
full source files of the core systems come out. `runnable/knowledge-eval/` and
`tooling/` are kept as they are.

### 6.1 Test files kept

Decided one file at a time. A test file is kept only if **every** test in it
drives the app from the outside, through an HTTP route, and asserts on what
comes back or on what a user could observe. All twelve were byte-identical to
Zelbi at `8875721`; eleven still are at `4772472b`, and `test_ai.py` was
refreshed to its `4772472b` version (its response-key assertion gained the two
restricted-item keys).

| File | Tests | Source |
|---|---|---|
| `code/admin_ops/test_admin_actions.py` | 15 | `backend/tests/test_admin_actions.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_authorization.py` | 2 | `backend/tests/test_admin_authorization.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_claims.py` | 11 | `backend/tests/test_admin_claims.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_disputes.py` | 19 | `backend/tests/test_admin_disputes.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_health.py` | 4 | `backend/tests/test_admin_health.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_listings.py` | 16 | `backend/tests/test_admin_listings.py`@4772472b, verbatim |
| `code/admin_ops/test_admin_money.py` | 13 | `backend/tests/test_admin_money.py`@4772472b, verbatim |
| `code/ai_service/test_ai.py` | 1 | `backend/tests/test_ai.py`@4772472b, verbatim |
| `code/ai_service/test_ai_object_key_ownership.py` | 2 | `backend/tests/test_ai_object_key_ownership.py`@4772472b, verbatim |
| `code/database/test_rate_limit_mounts.py` | 4 | `backend/tests/test_rate_limit_mounts.py`@4772472b, verbatim |
| `code/jobs/test_cron_reminders.py` | 4 | `backend/tests/test_cron_reminders.py`@4772472b, verbatim |
| `code/payments/test_stripe_billing.py` | 3 | `backend/tests/test_stripe_billing.py`@4772472b, verbatim |

Test files removed, and why each did not qualify, are in 6.2.

### 6.2 Removed

92 files removed from `code/`. Source files were removed whole. A test
file was removed when some or all of its tests call internal functions directly
rather than through a route, or, for the two message-guard test files, because
their inputs spell out the detection recipe.

| File | Kind | Reason |
|---|---|---|
| `code/admin_ops/routers_admin.py` | source | full source of a core system |
| `code/admin_ops/routers_admin_actions.py` | source | full source of a core system |
| `code/admin_ops/routers_admin_reads.py` | source | full source of a core system |
| `code/admin_ops/routers_admin_writes.py` | source | full source of a core system |
| `code/admin_ops/routers_events.py` | source | full source of a core system |
| `code/admin_ops/routers_watcher.py` | source | full source of a core system |
| `code/admin_ops/standing_notices.py` | source | full source of a core system |
| `code/admin_ops/test_admin_flags.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/admin_ops/test_admin_notes.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/admin_ops/test_watcher.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/ai_service/ai_service.py` | source | full source of a core system |
| `code/ai_service/routers_ai.py` | source | full source of a core system |
| `code/ai_service/test_ai_service.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/ai_service/test_ai_soft_item.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/coordinate_privacy/coordinate_privacy.py` | source | full source of a core system |
| `code/coordinate_privacy/test_coordinate_privacy.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/credits_devicecheck/credit_service.py` | source | full source of a core system |
| `code/credits_devicecheck/devicecheck_service.py` | source | full source of a core system |
| `code/credits_devicecheck/expo-module.config.json` | source | full source of a core system |
| `code/credits_devicecheck/index.ts` | source | full source of a core system |
| `code/credits_devicecheck/ios_ZelbiDeviceCheck.podspec` | source | full source of a core system |
| `code/credits_devicecheck/ios_ZelbiDeviceCheckModule.swift` | source | full source of a core system |
| `code/credits_devicecheck/mobile_utils_deviceCheck.ts` | source | full source of a core system |
| `code/credits_devicecheck/src_ZelbiDeviceCheckModule.ts` | source | full source of a core system |
| `code/credits_devicecheck/test_credits_devicecheck.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/credits_devicecheck/test_credits_giveaway.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/credits_devicecheck/test_devicecheck_service.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/database/database.py` | source | full source of a core system |
| `code/database/dependencies.py` | source | full source of a core system |
| `code/database/observability.py` | source | full source of a core system |
| `code/database/rate_limit.py` | source | full source of a core system |
| `code/database/test_migrations_phase_9.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/jobs/listing_expiry.py` | source | full source of a core system |
| `code/jobs/recommendation_scan.py` | source | full source of a core system |
| `code/jobs/run_daily_jobs.py` | source | full source of a core system |
| `code/jobs/run_frequent_jobs.py` | source | full source of a core system |
| `code/jobs/test_recommendation_scan.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/jobs/test_run_daily_jobs.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/__init__.py` | source | full source of a core system |
| `code/knowledge/answer.py` | source | full source of a core system |
| `code/knowledge/answer_eval.py` | source | full source of a core system |
| `code/knowledge/api_abuse.py` | source | full source of a core system |
| `code/knowledge/chunking.py` | source | full source of a core system |
| `code/knowledge/embeddings.py` | source | full source of a core system |
| `code/knowledge/eval_cases.py` | source | full source of a core system |
| `code/knowledge/frontmatter.py` | source | full source of a core system |
| `code/knowledge/ingestion.py` | source | full source of a core system |
| `code/knowledge/retrieval.py` | source | full source of a core system |
| `code/knowledge/retrieval_eval.py` | source | full source of a core system |
| `code/knowledge/routers_knowledge.py` | source | full source of a core system |
| `code/knowledge/test_knowledge_answer.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_ask_endpoint.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_eval_seed.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_ingestion.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_log_retention.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_models.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/test_knowledge_retrieval.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/knowledge/validation.py` | source | full source of a core system |
| `code/message_guard/scam_detection.py` | source | full source of a core system |
| `code/message_guard/test_scam_detection.py` | test | test file; its inputs enumerate what the scam rules catch (the recipe) |
| `code/message_guard/test_scam_wiring.py` | test | test file; its inputs enumerate what the scam rules catch (the recipe) |
| `code/mobile/hooks_usePushTapRouting.ts` | source | full source of a core system |
| `code/mobile/store_auth.ts` | source | full source of a core system |
| `code/mobile/utils_directions.ts` | source | full source of a core system |
| `code/mobile/utils_listings.ts` | source | full source of a core system |
| `code/mobile/utils_messages.ts` | source | full source of a core system |
| `code/mobile/utils_notificationRouting.ts` | source | full source of a core system |
| `code/mobile/utils_supabase.ts` | source | full source of a core system |
| `code/payments/claim_cancel_service.py` | source | full source of a core system |
| `code/payments/pending_payment_sweeper.py` | source | full source of a core system |
| `code/payments/post_window_sweeper.py` | source | full source of a core system |
| `code/payments/routers_stripe_webhooks.py` | source | full source of a core system |
| `code/payments/stripe_service.py` | source | full source of a core system |
| `code/payments/test_claim_deferred_intent.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_claim_fees.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_curbside_sweeper.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_pending_payment_sweeper.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_post_window_sweeper.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_stripe_customer.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_stripe_service.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/payments/test_stripe_webhooks.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/photo_access/cloudflare_r2.py` | source | full source of a core system |
| `code/photo_access/test_r2_delete.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/photo_access/test_signed_photo_reads.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/block_service.py` | source | full source of a core system |
| `code/trust/strike_service.py` | source | full source of a core system |
| `code/trust/test_blocks.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/test_claim_score_delta.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/test_dispute_suspension.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/test_strike.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/test_trust_service.py` | test | test file; not every test drives an HTTP route (unit tests of internals) |
| `code/trust/trust_service.py` | source | full source of a core system |

### 6.3 Excerpts

One `EXCERPTS.md` per `code/` subfolder. Each passage is verbatim from the
clean Zelbi clone at `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`), at most
40 lines, and names the documents that cite it. Two passages are the first 40
lines of a longer function and say so.

| Excerpt file | Passage | Source | Lines |
|---|---|---|---|
| `code/admin_ops/EXCERPTS.md` | The admin gate | `backend/app/routers/admin.py`@4772472b | 29–35 (7) |
| `code/admin_ops/EXCERPTS.md` | Sentry webhook: HMAC signature check | `backend/app/routers/watcher.py`@4772472b | 175–214 (40) — first 40 lines |
| `code/admin_ops/EXCERPTS.md` | The watcher stream: a 2-second database poll | `backend/app/routers/watcher.py`@4772472b | 329–345 (17) |
| `code/ai_service/EXCERPTS.md` | Stage 1: fence-tolerant JSON extraction | `backend/app/services/ai_service.py`@4772472b | 94–112 (19) |
| `code/ai_service/EXCERPTS.md` | The vision call | `backend/app/services/ai_service.py`@4772472b | 166–193 (28) |
| `code/ai_service/EXCERPTS.md` | Stages 2–4, and the restricted-item flag (D620) | `backend/app/services/ai_service.py`@4772472b | 195–226 (32) |
| `code/ai_service/EXCERPTS.md` | Object-key authorization and the 502 mapping (stage 5) | `backend/app/routers/ai.py`@4772472b | 1–40 (40) |
| `code/ai_service/EXCERPTS.md` | Support agent: the runner's contract (D578) | `backend/app/services/agents/runner.py`@4772472b | 1–26 (26) |
| `code/ai_service/EXCERPTS.md` | Support agent: the model call, with every failure handed to a person | `backend/app/services/agents/runner.py`@4772472b | 144–168 (25) |
| `code/ai_service/EXCERPTS.md` | Support agent: the leak guard on the one user-visible line | `backend/app/services/agents/leak_guard.py`@4772472b | 1–15 (15) |
| `code/ai_service/EXCERPTS.md` | Support agent: the daily spending cap and its 80% and 100% alerts | `backend/app/services/agents/spend.py`@4772472b | 43–70 (28) |
| `code/coordinate_privacy/EXCERPTS.md` | The keyed approximate point, and the warning when the key is unset | `backend/app/services/coordinate_privacy.py`@4772472b | 18–48 (31) |
| `code/coordinate_privacy/EXCERPTS.md` | Who sees the true location | `backend/app/services/coordinate_privacy.py`@4772472b | 51–70 (20) |
| `code/coordinate_privacy/EXCERPTS.md` | Test: the nearby feed returns approximate points, never true ones | `backend/tests/test_coordinate_privacy.py`@4772472b | 80–93 (14) |
| `code/credits_devicecheck/EXCERPTS.md` | Which credits wait for DeviceCheck | `backend/app/services/credit_service.py`@4772472b | 1–35 (35) |
| `code/credits_devicecheck/EXCERPTS.md` | The pending-credit lookup | `backend/app/services/credit_service.py`@4772472b | 175–190 (16) |
| `code/credits_devicecheck/EXCERPTS.md` | DeviceCheck fails closed when unconfigured | `backend/app/services/devicecheck_service.py`@4772472b | 1–8 (8) |
| `code/database/EXCERPTS.md` | Prepared statements off for the transaction pooler | `backend/app/database.py`@4772472b | 1–30 (30) |
| `code/database/EXCERPTS.md` | Error reporting, off under pytest | `backend/app/observability.py`@4772472b | 10–36 (27) |
| `code/database/EXCERPTS.md` | An explicit capture inside each except block | `backend/app/observability.py`@4772472b | 39–48 (10) |
| `code/jobs/EXCERPTS.md` | The 10-minute runner and its job list | `backend/app/jobs/run_frequent_jobs.py`@4772472b | 18–57 (40) — first 40 lines |
| `code/knowledge/EXCERPTS.md` | Visibility is a SQL predicate, on every path | `backend/app/services/knowledge/retrieval.py`@4772472b | 1–20 (20) |
| `code/knowledge/EXCERPTS.md` | Fusion constants and the daily embedding ceiling (D537, D538) | `backend/app/services/knowledge/retrieval.py`@4772472b | 50–68 (19) |
| `code/knowledge/EXCERPTS.md` | The visibility filters | `backend/app/services/knowledge/retrieval.py`@4772472b | 95–118 (24) |
| `code/knowledge/EXCERPTS.md` | The vector half, inside the same filter | `backend/app/services/knowledge/retrieval.py`@4772472b | 199–219 (21) |
| `code/knowledge/EXCERPTS.md` | Reciprocal rank fusion | `backend/app/services/knowledge/retrieval.py`@4772472b | 268–297 (30) |
| `code/knowledge/EXCERPTS.md` | The embedding call | `backend/app/services/knowledge/embeddings.py`@4772472b | 1–40 (40) — first 40 lines |
| `code/knowledge/EXCERPTS.md` | The deterministic composer: no model writes the answer | `backend/app/services/knowledge/answer.py`@4772472b | 1–20 (20) |
| `code/message_guard/EXCERPTS.md` | Rule status: rule 4 not active, rule 5 deferred | `backend/app/services/scam_detection.py`@4772472b | 55–66 (12) |
| `code/message_guard/EXCERPTS.md` | The normalizer: look-alike decoding | `backend/app/services/scam_detection.py`@4772472b | 120–133 (14) |
| `code/message_guard/EXCERPTS.md` | The normalizer: one canonical form before any rule runs | `backend/app/services/scam_detection.py`@4772472b | 136–152 (17) |
| `code/mobile/EXCERPTS.md` | Load the claim the notification names (case study 03) | `mobile/app/handoff/[claimId].tsx`@4772472b | 1272–1296 (25) |
| `code/mobile/EXCERPTS.md` | Single-flight refresh and logout | `mobile/store/auth.ts`@4772472b | 118–127 (10) |
| `code/mobile/EXCERPTS.md` | Two Supabase clients: no PKCE on the primary | `mobile/utils/supabase.ts`@4772472b | 186–222 (37) |
| `code/payments/EXCERPTS.md` | A real PaymentIntent id, by shape (case study 04) | `backend/app/services/stripe_service.py`@4772472b | 58–68 (11) |
| `code/payments/EXCERPTS.md` | A real id Stripe cannot find is left untouched (case study 04) | `backend/app/jobs/post_window_sweeper.py`@4772472b | 296–322 (27) |
| `code/payments/EXCERPTS.md` | The imminent-reminder query (case study 01) | `backend/app/jobs/post_window_sweeper.py`@4772472b | 142–163 (22) |
| `code/payments/EXCERPTS.md` | Already captured: adopt, never re-capture | `backend/app/services/stripe_service.py`@4772472b | 665–700 (36) |
| `code/payments/EXCERPTS.md` | Consent stamped at the pay tap: contract (case study 02) | `backend/app/routers/claims.py`@4772472b | 1402–1414 (13) |
| `code/payments/EXCERPTS.md` | Consent stamped at the pay tap: checks and stamp (case study 02) | `backend/app/routers/claims.py`@4772472b | 1416–1455 (40) |
| `code/payments/EXCERPTS.md` | Unreadable is not absent: the pending-payment sweeper | `backend/app/jobs/pending_payment_sweeper.py`@4772472b | 84–123 (40) — first 40 lines |
| `code/payments/EXCERPTS.md` | Test: a live hold is promoted, not cancelled | `backend/tests/test_pending_payment_sweeper.py`@4772472b | 148–187 (40) |
| `code/payments/EXCERPTS.md` | The shared cancel path | `backend/app/services/claim_cancel_service.py`@4772472b | 22–61 (40) — first 40 lines |
| `code/photo_access/EXCERPTS.md` | A photo address must be the caller's own upload (D588) | `backend/app/utils/photo_ownership.py`@4772472b | 1–40 (40) |
| `code/photo_access/EXCERPTS.md` | Signing fails open to the stored address | `backend/app/utils/cloudflare_r2.py`@4772472b | 165–199 (35) |
| `code/photo_access/EXCERPTS.md` | Deletes touch only the owner's folder | `backend/app/utils/cloudflare_r2.py`@4772472b | 97–127 (31) |
| `code/trust/EXCERPTS.md` | The trust model and its deductions | `backend/app/services/trust_service.py`@4772472b | 1–30 (30) |
| `code/trust/EXCERPTS.md` | Strike constants | `backend/app/services/strike_service.py`@4772472b | 30–41 (12) |
| `code/trust/EXCERPTS.md` | The strike check | `backend/app/services/strike_service.py`@4772472b | 52–91 (40) — first 40 lines |
| `code/trust/EXCERPTS.md` | Block checks, symmetric | `backend/app/services/block_service.py`@4772472b | 21–50 (30) |

Redactions inside the excerpts (each replaces the secrets manager's name):

| File | Line | Replaced with |
|---|---|---|
| `code/coordinate_privacy/EXCERPTS.md` | 25 | `[secrets manager]` |
| `code/coordinate_privacy/EXCERPTS.md` | 34 | `[secrets manager]` |

Links in the write-ups and `LEDGER.md` that pointed at removed files now point
at the folder's `EXCERPTS.md`; 71 links were re-pointed. Line numbers a write-up
gives at `8875721` are left as they were, and the write-up says so.

---

## 7. Decisions added, and every redaction (2026-11-17)

### 7.1 Thirteen decision records added

Each is copied verbatim from `docs/agents/10-implementation-plan.md` at
`4772472b`, under the existing four-line header, apart from the redactions in
7.2. D319 and D538 were already published and are left as they were. Reason
for every row: the case studies in `06-case-studies/` cite it.

| D | Theme | Source lines | Cited by |
|---|---|---|---|
| [D402](03-decisions/privacy/D402.md) | privacy | 2645 | case study 03 |
| [D410](03-decisions/ops/D410.md) | ops | 2661 | case study 01 |
| [D537](03-decisions/ai/D537.md) | ai | 2937 | case study 07 |
| [D577](03-decisions/trust/D577.md) | trust | 2990–3007 | case study 08 |
| [D578](03-decisions/ai/D578.md) | ai | 3008–3025 | case study 08 |
| [D579](03-decisions/trust/D579.md) | trust | 3027–3035 | the support agent's threat rule (case study 08) |
| [D580](03-decisions/trust/D580.md) | trust | 3037–3046 | case study 08; LIMITATIONS (Trust model) |
| [D625](03-decisions/ops/D625.md) | ops | 3140 | case study 06 |
| [D627](03-decisions/ops/D627.md) | ops | 3144 | case study 06 |
| [D629](03-decisions/ops/D629.md) | ops | 3148 | case study 05 (the stamp rule) |
| [D635](03-decisions/ops/D635.md) | ops | 3160 | case study 05 |
| [D636](03-decisions/privacy/D636.md) | privacy | 3161 | case study 05 |
| [D637](03-decisions/privacy/D637.md) | privacy | 3162 | case study 05 |

### 7.2 Redactions

Every redaction made in this refresh, by file and line. Names that were
redacted are not restated here.

| File | Line | What was removed | Replaced with |
|---|---|---|---|
| `03-decisions/ai/D537.md` | 9 | the secrets manager's name | `in [secrets manager] dev and prd` |
| `03-decisions/ai/D578.md` | 16 | an email address | `[email]` |
| `03-decisions/ai/D578.md` | 21 | the repository URL | `[this repository]` |
| `03-decisions/trust/D580.md` | 9 | a local file path | `[local plan file]` |
| `03-decisions/privacy/D636.md` | 9 | a local folder path | `[local folder]` |
| `03-decisions/privacy/D636.md` | 9 | an app bundle identifier (3 occurrences) | `[widget bundle id]` |
| `03-decisions/privacy/D636.md` | 9 | an app bundle identifier (2 occurrences) | `[dev bundle id]` |
| `03-decisions/privacy/D636.md` | 9 | an app bundle identifier | `[bundle id]` |
| `03-decisions/privacy/D636.md` | 9 | a seed test-persona name | `test giver A` |
| `03-decisions/privacy/D636.md` | 9 | a seed test-persona name | `test picker A` |
| `03-decisions/privacy/D637.md` | 9 | a local file path | `[local report file]` |
| `03-decisions/trust/D542.md` | 9 | a seed test-persona name | `test giver B` |
| `03-decisions/ai/D578.md` | 16 | a partial email address (local part) | `[that address]` |
| `03-decisions/privacy/D323.md` | 9 | the secrets manager's name | `[secrets manager]` |
| `03-decisions/ops/D274.md` | 9 | the secrets manager's name | `[secrets manager]` |
| `code/coordinate_privacy/EXCERPTS.md` | 25 | the secrets manager's name | `[secrets manager]` |
| `code/coordinate_privacy/EXCERPTS.md` | 34 | the secrets manager's name | `[secrets manager]` |
| `MANIFEST.md` | 307 (§4, manual read) | a seed test-persona name | a description of it |

Seed test-persona names were replaced with neutral labels: `test picker A`,
`test giver A`, `test giver B`. Two other files of this refresh were written
without hosts or credential-shaped values from the start:
`verification/pytest-summary-2026-11-17.txt` abbreviates the CI workflow's fake
placeholder URLs as `<placeholder URL>` and `<placeholder DSN>`, and
`verification/ci-run-2026-11-17.md` gives no link to the private repository.

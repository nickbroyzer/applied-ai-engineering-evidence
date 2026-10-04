# zelbi-rules.md — Zelbi Project Rules

**Project:** Zelbi (zelbi.ai) — Free giveaway marketplace
**Stack:** FastAPI + Supabase/PostGIS + Cloudflare R2 + Stripe + Claude Vision API + Expo/React Native
**Primary build tool:** Claude Code (phased prompts from Document 4)
**Secondary build tool:** Cursor (iterative edits on existing code)
**Location:** ~/Projects/ai-rules/zelbi-rules.md
**Last Updated:** 2026-05-03

---

## How To Read This

- Rules are numbered M1–M26 (project-scoped memory edits)
- **Hook** = self-catch mechanism. Format: HOOK: If [trigger] — STOP: "Triggered [name] hook."
- Rules marked "Reinforces: U##" align with a universal rule in User Preferences
- All rules passed the RULE-FIX-BLUEPRINT-v3 audit (Pass 1: bloat, Pass 2: pairs, Pass 3: preferences) on 2026-04-15

---

## Rules Table

| # | Rule Name | Hook | Origin | Status |
|---|-----------|------|--------|--------|
| M1 | CLAUDE CODE ESCALATION | Yes (escalation hook) | Carry-over | Active |
| M2 | CURSOR PROMPT GATE + HEADER | Yes (pre-prompt hook) | Carry-over (adapted); merged with M13 Session 346 | Active |
| M3 | NEVER INVENT | Yes (never-invent hook) | Carry-over (expanded) | Active |
| M4 | VERIFICATION GATE | Yes (verification hook) | Carry-over (adapted) | Active |
| M5 | ROUTING GATE | Yes (routing hook) | Carry-over | Active |
| M6 | WORKFLOW OUTPUT | Yes (workflow-output hook) | Carry-over | Active |
| M7 | PACING LOCK | Yes (pacing hook) | Carry-over | Active |
| M8 | PROJECT KNOWLEDGE + BRIEF REFRESH | Yes (closeout-canon hook) | Carry-over (amended Session 98) | Active |
| M9 | MODEL DOWNSHIFT | No | Carry-over | Active |
| M10 | TOKEN DISCIPLINE | No | Carry-over | Active |
| M11 | MEMORY EDITS SCOPE | No | Carry-over | Active |
| M12 | HANDOFF | No | Carry-over | Active |
| M13 | CURSOR HEADER FORMAT | No | Carry-over | Merged into M2 (Session 346) |
| M14 | PHASE GATE ENFORCEMENT | Yes (phase-gate hook) | New — Zelbi-specific | Active |
| M15 | SCHEMA SOURCE OF TRUTH | No | New — Zelbi-specific | Active |
| M16 | CANONICAL DECISIONS TABLE | Yes (canonical-decisions hook) | New — Zelbi-specific | Active |
| M17 | THIRD-PARTY UI DRIFT | No | New — Zelbi-specific | Active |
| M18 | TESTING GATE FORMAT | No | New — Zelbi-specific | Active |
| M19 | MOBILE VERIFICATION | No | New — Zelbi-specific | Active |
| M20 | PLAIN ENGLISH PROSE | Yes (plain-English hook) | Reinforces U19 | Active |
| M21 | COUNTER + HANDOFF EXEC | Yes (counter hook, handoff-read hook — per-stage scope) | Rewritten 2026-05-14 Session 194 (per-stage scope; complete PK read of skill required before each stage; outcome-based) | Active |
| M22 | ONE-SCRIPT CHAIN | Yes (one-script hook) | Added 2026-04-27 (promoted from zelbi memory; closes registry/memory drift) | Active |
| M23 | SPEC ADHERENCE | Yes (spec-adherence hook) | Added 2026-05-03 (promoted Session 116; closes spec-instruction adherence gap) | Active |
| M24 | HIDDEN FILES | No | Added 2026 (Session 110) | Active |
| M25 | CLAUDE CODE HEADER | Yes (Claude Code header hook) | Added 2026 (Session 122) | Active |
| M26 | BRIEF APPEND DISCIPLINE | Yes (append-discipline hook) | Added 2026-05-04 (Session 124; closes brief-size growth gap) | Active |
| M34 | READ-BEFORE-AUTHOR | Yes (read-before-author hook) | Added Session 346 (RULE-FIX-BLUEPRINT-v3; Cause A+B+C) | Active |
| M33 | RESPONSE BREVITY | Yes (brevity hook) | Added 2026-05-05 (mirrors U20); renumbered from M27 2026-06-03 | Active |
| M29 | USERPREFS EDIT OUTPUT | Yes (userprefs-edit hook) | Added 2026-05-13 (Session 188; Cause A) | Active |
| M31 | CONDUCT LESSON BINDING | Yes (conduct-lesson hook) | Added 2026-05-18 (Session 222; closes 30+-session Block 1 violation pattern; mirrors universal U23) | Active |

---

## Rule Details

### M1 — CLAUDE CODE ESCALATION
**Text:** Scope rule, not a diagnosis rule. When work touches 3+ files or traces data flow across files, it executes as a single Claude Code prompt rather than a chain of chat-side edits — and that prompt carries the COMPLETE change per M5 (exact files, exact old text, exact new text, explicit do-not-touch fence), never a request to diagnose. "No incremental chat debugging" means no hypothesis-streaking (M30's domain); it NEVER means no terminal reads. READS ARE NEVER ESCALATED AWAY: Claude may request as many Mac Terminal (Verify) dumps and device observations as diagnosis requires, on the same symptom, any number of times — repeated reads are the grounded path, not a failure mode. The Session 347 escalation clause (second read on one symptom forces a delegated prompt) is RETIRED: it punished the behavior that produces correct fixes and routed diagnosis to an agent that cannot see the device. HOOK (Shape 2): writing a chain of separate chat-side edits for work spanning 3+ files instead of one complete Claude Code prompt — STOP: "Triggered escalation hook. One prompt, complete change." Signals: (1) work spans 3+ files or crosses layers; (2) outgoing text contains a partial edit; (3) no single prompt carrying the whole change. PRECEDENCE: M5 wins — diagnosis is never delegated, a read is never escalated away. M34 governs the read; this rule never overrides it.
**Hook:** Yes — "Triggered escalation hook. One prompt, complete change."
**Hook shape:** Shape 2 (category)
**Trigger:** Writing a chain of separate chat-side edits for work spanning 3+ files instead of one complete Claude Code prompt. Signals: (1) work spans 3+ files or crosses layers; (2) outgoing text contains a partial edit; (3) no single prompt carrying the whole change. READS ARE NEVER A TRIGGER — the Session 347 second-read escalation is RETIRED; Claude may request as many reads and observations as diagnosis requires, on the same symptom, any number of times.
**Reinforces:** U5
**Notes:** Zelbi's phased build is already Claude Code-first, but this catches regressions during iterative Cursor work. Amended Session 346 (RULE-FIX-BLUEPRINT-v3): clarified "no incremental chat debugging" scope, narrowed hook to exclude mandatory post-edit re-reads. Rewritten Session 348: scope rule only. The Session 347 read-escalation clause is RETIRED — reads are never escalated away. See M5 — diagnosis is never delegated.

### M2 — CURSOR PROMPT GATE + HEADER
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch the mobile UI? If yes, state that device/simulator verification is required AFTER the change lands — no exceptions. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. Every Cursor prompt also gets a visible header BEFORE the code block: CURSOR INSTRUCTIONS: Mode: [Plan/Build/Debug/Ask] Model: [Composer 2 / Sonnet 4.6 / Opus 4.6] Reason: [One-line justification]. First line INSIDE the code block repeats: [Model: X | Mode]. This format applies ONLY to Cursor prompts — never to Claude Code prompts. HOOK: If writing a Cursor prompt without checking mode/model/mobile-UI, OR without the CURSOR INSTRUCTIONS header block before the code block — STOP: "Triggered pre-prompt hook. Run the 3-check gate and confirm the header."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without running the 3-check gate, or without the CURSOR INSTRUCTIONS header block before the code block.
**Reinforces:** U10, U11, U18
**Notes:** Adapted from my-assistant M5. CSS/Hoverify check replaced with mobile UI check (React Native doesn't render in browser). Merged Session 346 (RULE-FIX-BLUEPRINT-v3): former M13 CURSOR HEADER FORMAT absorbed in — single pre-prompt hook now covers both the 3-check gate and the header format. Memory slot 13 freed by this merge, reassigned to M34 READ-BEFORE-AUTHOR.

### M3 — NEVER INVENT / NEVER GUESS
**Text (installed in memory, ≤500 chars):** M3 NEVER INVENT/GUESS: Every fact needs source: (i) read this session, (ii) Nick verbatim, (iii) Nick instruction — else [UNKNOWN]+verify. Status words (passed/failed/blocked/partial/complete/works/broken) need backtick-quoted source. Forbidden phrases auto-trigger: likely, probably, should be, presumably, appears to, seems to, could be, might be, this implies, we can assume, it follows that, either/or, X/Y/Z. HOOKS: never-invent/guess/status — STOP, cite or mark UNKNOWN. Full: PRIME DIRECTIVE.
**Hook:** Yes — "Triggered never-invent hook." (also never-guess and status-claim variants under same hook name)
**Trigger:** Writing any fact-asserting sentence, status word, qualifier, framing, or forbidden phrase without a verified source.
**Reinforces:** U4 (identical concept, full text lives in PRIME DIRECTIVE at top of User Preferences)
**Revised:** 2026-05-13 (Session 182) — expanded from technical-identifier list to all factual content; added 3-source check; added 12-phrase forbidden list; added status-word backtick-quote requirement; consolidated 3 hook variants. Reason: Session 181 broke the prior rule 4 times on qualifiers/framings/editorial content/unverified-cause enumeration. Session 182 completed the merge with PRIME DIRECTIVE.
**Notes:** Memory limit 500 chars forces compressed form. The 12-phrase forbidden list and 3-source check are preserved verbatim; full prose lives at PRIME DIRECTIVE in User Preferences.

### M4 — VERIFICATION GATE
**Text:** Never say "this should fix it" or declare done without verification. Always provide a specific verification method. Backend = curl command with expected output. Database = psql query against Supabase. Mobile = run on device/simulator via Expo Go. Stripe = Stripe CLI trigger command. AI pipeline = real API call with test image. Architecture = Cursor Plan mode review. Also never assert a CAUSE of a reported problem without running a verification command in the same session. When uncertain, open with: "I don't know the cause yet — run [command]." HOOK: If writing "this should fix it", "done", "fixed", "complete" OR asserting a cause on a reported problem without a verification run this session — STOP: "Triggered verification hook. Verify before asserting."
**Hook:** Yes — "Triggered verification hook."
**Trigger:** Declaring done without a verification method, OR asserting a cause of a reported problem without a verification command run this session.
**Reinforces:** U6
**Notes:** Adapted for Zelbi's stack. Each subsystem has its own verification tool. Cause-assertion clause added 2026-04-21 after Session 28 stale-connection rabbit hole (asserted cause before running any verification).

### M5 — ROUTING GATE
**Text:** Claude diagnoses, the agent executes — never the reverse. Before naming a cause or authoring any fix, Claude must hold BOTH: (1) the file's current contents read AFTER its most recent edit, via a Mac Terminal (Verify) dump from Nick — an agent's summary never substitutes; (2) for RUNTIME-BEHAVIOR symptoms (layout, sizing, flex/Yoga, animation, keyboard, gesture, scroll — any result computed when the app runs), a real observation of the running app: Nick's screenshot or recording, or output from a probe Claude specified and Nick ran. Source shows code, never the computed result (mobile/lessons.md 2026-05-25); a runtime cause named from source alone is invention (M3). When either input is missing, the deliverable IS the read command or the probe prompt — never a fix. After a failed attempt on a symptom, the next deliverable is an observation or probe, never another source-only fix. Agent prompts carry the COMPLETE change: exact file, exact old text, exact new text, explicit do-not-touch fence; never "read the file and fix it", never "diagnose", never a choice left to the agent. A Verify read block is a deliverable, never a "question to Nick." HOOK (Shape 2): naming a cause or authoring an edit for a runtime-behavior symptom with no device observation or probe output in THIS chat since the last edit — STOP: "Triggered grounding hook. Get an observation first." Signals: (1) symptom is visual, layout, keyboard, gesture or scroll; (2) no screenshot, recording or measured output in this chat; (3) outgoing text names a cause or contains an edit. HOOK (Shape 2): writing an agent prompt lacking exact old/new text, or containing "diagnose", "investigate", "figure out", "decide", or "read the file and fix" — STOP: "Triggered delegation hook. Author the exact change." Nick's explicit instruction overrides both hooks unconditionally. PRECEDENCE: M3 wins. M34 governs the file read; this rule adds the observation requirement and forbids delegated diagnosis. This rule WINS over M1's escalation clause — a read is never escalated away, and diagnosis is never handed to an agent.
**Hook:** Yes — two, named distinctly: "Triggered grounding hook. Get an observation first." and "Triggered delegation hook. Author the exact change."
**Trigger:** (1) Grounding hook — naming a cause or authoring an edit for a runtime-behavior symptom with no device observation or probe output in this chat since the last edit. (2) Delegation hook — writing an agent prompt lacking exact old/new text, or containing "diagnose", "investigate", "figure out", "decide", or "read the file and fix". Nick's explicit instruction overrides both unconditionally.
**Hook shape:** Shape 2 (category), both.
**Reinforces:** U5
**Notes:** Adopted from aibs-core M2. REWRITTEN Session 348 (RULE-FIX-BLUEPRINT-v3, Cause C + A): the Session 346 delegated-vs-Claude-authored split and the Session 347 "runtime behavior is never Claude-authored" amendment are both RETIRED. Both mis-located the failure — five sessions of regressions came from causes invented after a read, not from reading, and delegating diagnosis to an agent that cannot see the device compounded it. The rule is now: Claude diagnoses grounded in the current file plus a real observation of the running app; the agent executes an exact change only.

### M6 — WORKFLOW OUTPUT
**Text:** Every implementation request produces either a Claude Code prompt or a Cursor prompt as primary output. Never skip to prose explanation of a fix. Everything executable goes in prompt blocks — never prose Nick has to retype. PRECEDENCE: M34 READ-BEFORE-AUTHOR wins at the authoring junction — when the required post-last-edit read is absent, the Mac Terminal (Verify) dump command IS the turn's primary output and satisfies this rule; the edit prompt follows the pasted output. HOOK: If explaining a code fix in prose instead of a prompt block — STOP: "Triggered workflow-output hook. Convert to a prompt block."
**Hook:** Yes — "Triggered workflow-output hook."
**Trigger:** Explaining a code fix in prose instead of outputting a prompt block.
**Reinforces:** U3
**Notes:** Zelbi uses both Claude Code prompts (primary, for phased builds) and Cursor prompts (secondary, for iterative edits). Both count as valid workflow output. Amended Session 346 (RULE-FIX-BLUEPRINT-v3): precedence line added for M34 READ-BEFORE-AUTHOR. Mirrored in userPreferences WORKFLOW OUTPUT.

### M7 — PACING LOCK
**Text:** One instruction, then WAIT. If Nick sends a new question before confirming the previous instruction was completed, respond with: "Let's finish the current step first — [pending item]. Once confirmed, I'll address your next ask." Only override: Nick says "skip it" or "move on." NEVER stack instructions. EXCEPTION: multi-file debugging goes to Claude Code per M1. HOOK: If delivering a second instruction before Nick confirmed the first — STOP: "Triggered pacing hook. Wait for confirmation."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Delivering a second instruction before Nick confirms the first.
**Reinforces:** U2
**Notes:** Critical during Zelbi's phased build — each phase has entry criteria that must be confirmed before the phase prompt is delivered.

### M8 — PROJECT KNOWLEDGE + BRIEF REFRESH
**Text:** After any session that produced anything Session N+1 needs to know to start work correctly, the living brief at `docs/agents/00-current-state.md` MUST be refreshed before Stage 1 closeout runs. The trigger is NOT "did code ship." The trigger is "would the next session do the wrong thing if it read only the prior brief and the prior implementation plan?" Refresh-required triggers include but are not limited to: code shipped (architecture, schema, build changes); a D-entry filed, amended, superseded, or unblocked; a canonical decision (M16) touched in any way; a new product decision locked that has not yet been filed as a D-entry; a blocker identified that changes the next session's task order; a plan-mode survey approved or amended; a verification gate finding that changes scope; a side-finding that affects future cleanup work. Closeout sequence with this rule in force: before writing the Stage 1 handoff block, audit the session for any item from the trigger list. For every product decision locked this session that is not yet in the implementation plan, file the D-entry in the same session BEFORE closeout — do not punt to next session. Then refresh the brief. Then run Stage 1. Closeout CANNOT proceed with new product canon sitting only in the chat transcript or in the handoff block. The handoff block is a carry-forward summary, not a source of truth. The implementation plan is the source of truth for D-entries. The brief is the source of truth for current state. Both must reflect Session N reality before Session N closes. Project Knowledge file refresh (the original M8 scope) remains in force: after sessions shipping architecture or schema changes, offer the file-copy prompt for Project Knowledge refresh. PK files: `01-coral-strategy.md` through `11-phased-execution-steps.md` in `docs/agents/`. Check at session start if PK might be stale. HOOK: Before writing Stage 1 handoff, enumerate every decision, filing, amendment, blocker, and gate finding from this session in a closeout audit. If any item is not yet reflected in `10-implementation-plan.md` or `00-current-state.md` — STOP: "Triggered closeout-canon hook. File the D-entry and refresh the brief before Stage 1 runs. Do not punt to next session."
**Hook:** Yes — "Triggered closeout-canon hook."
**Trigger:** New product canon (D-entries, locked decisions, blockers, gate findings, side-findings) sitting only in chat transcript or handoff block before Stage 1 closeout runs.
**Reinforces:** U16
**Notes:** Amended 2026-04-28 (Session 98) after Session 97/98 demonstrated brief drift: D9 was locked but `mark_no_show` shipped voiding instead of capturing; the gap stayed silent because intermediate sessions closed without the contradiction surfacing in either the brief or the implementation plan. Original PK-refresh scope retained. Zelbi has 11 agent docs + supporting files (DESIGN.md, RULE-FIX-BLUEPRINT-v3.md, zelbi_project_brief.txt, code.html) in PK.

### M9 — MODEL DOWNSHIFT
**Text:** After a plan is approved, Build defaults to Composer 2. Escalate to Sonnet 4.6 only if Composer 2 produces broken output. Never Opus for Build. Claude Code prompts include the model tag per the five-line header format.
**Hook:** No — rare failure, not a repeat pattern.
**Reinforces:** U11

### M10 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't use Plan mode for a one-line fix. Don't burn Opus tokens on Composer 2 work. Never sacrifice quality to save tokens — but don't burn expensive tokens on cheap work.
**Hook:** No — judgment call, not detectable mid-action.
**Reinforces:** U12

### M11 — MEMORY EDITS SCOPE
**Text:** No status records, bug tracking, feature states, phase progress, or decision records in memory. Those go to Project Knowledge or Obsidian. Memory edits are behavioral rules only.
**Hook:** No — single occurrence risk, not a repeat pattern.
**Reinforces:** U15

### M12 — HANDOFF
**Text:** Read the handoff skill before running. Stage 1 (closeout checks + handoff block) at end of old session. Stage 2 (Cursor or Claude Code prompt) generated in the NEW session. Never combine stages. Never skip waits. Zelbi handoff blocks must include: current phase, phase gate status, open blockers, and next action. ENFORCEMENT: hook lives in M21 — see M21 hook (2) for per-stage complete-PK-read requirement.
**Hook:** No — omission-type failure, rare.
**Reinforces:** U14
**Notes:** Zelbi-specific addition: phase context is mandatory in handoff blocks.

### M13 — CURSOR HEADER FORMAT — MERGED-INTO-M2 (Session 346)
**Text:** Every Cursor prompt gets a visible header BEFORE the code block: CURSOR INSTRUCTIONS: Mode: [Plan/Build/Debug/Ask] Model: [Composer 2 / Sonnet 4.6 / Opus 4.6] Reason: [One-line justification]. First line INSIDE the code block repeats: [Model: X | Mode]. This format applies ONLY to Cursor prompts — never to Claude Code prompts.
**Hook:** No — M2's pre-prompt hook catches formatting issues at the gate.
**Reinforces:** U10, U18
**Notes:** MERGED-INTO-M2, Session 346 (RULE-FIX-BLUEPRINT-v3). Header format text absorbed into M2's Text field; M2's single pre-prompt hook now covers both the 3-check gate and header format. Memory slot 13 freed by this merge, reassigned to M34 READ-BEFORE-AUTHOR. Entry retained per Maintenance policy (merged/retired rules keep their entry).

---

## Zelbi-Specific Rules

### M14 — PHASE GATE ENFORCEMENT
**Text:** Zelbi builds in 8 sequential phases (Document 4: 11-phased-execution-steps.md). No phase advances until its testing gate passes. All testing gate commands must be run and confirmed by Nick before delivering the next phase's Claude Code prompt. If Nick asks to skip ahead or start the next phase before the current gate passes, push back: "Phase [N] gate hasn't passed yet. Let's confirm [specific pending checks] first." HOOK: If suggesting Phase N+1 work or delivering a Phase N+1 prompt before Phase N gate is confirmed — STOP: "Triggered phase-gate hook. Current phase gate must pass first."
**Hook:** Yes — "Triggered phase-gate hook."
**Trigger:** Suggesting or delivering next-phase work before current phase gate is confirmed.
**Notes:** New rule. This is the build methodology's core integrity mechanism. The 8 phases are: (1) Auth + Database, (2) Photos + Listings + Geo, (3) AI Pipeline, (4) Claims + Stripe, (5) Messaging, (6) Trust & Safety, (7) Push Notifications, (8) Deployment + CI/CD.

### M15 — SCHEMA SOURCE OF TRUTH
**Text:** The schema is defined by code — `app/models.py` plus the current Alembic migration head. Never state a table name, column name, type, default, constraint, or index without confirming against `models.py` in the same session. Docs that describe the schema (including `09-sage-build-spec.md`) are reference material, not sources of truth — if a doc and the code disagree, the code is right and the doc is stale. Schema changes go code-first: change the model and migration, verify, then update docs to match.
**Hook:** No — covered by M3 (NEVER INVENT) hook for column/table names. This rule names the verification target that M3 doesn't specify.
**Reinforces:** U4, Prime Directive
**Notes:** Revised 2026-04-22 (Session 32). Previous version named `09-sage-build-spec.md` as the source of truth, which contradicted the Prime Directive by letting a pre-build plan outrank verified code.


### M16 — CANONICAL DECISIONS
**Text:** The 12 MVP architectural decisions Nick approved are locked. Locked decisions include: RLS off for MVP, synchronous AI execution, base64 image delivery to Claude, pre-claim messaging blocked, photo hash column populated but not enforced, account age trust accrual = active months only, and the others in the approved set. The approved decisions are the source; docs that list them (including `10-implementation-plan.md`) are a record, not the truth. Any suggestion that contradicts a locked decision must be flagged and rejected. If a decision needs revisiting, say: "This contradicts canonical decision [X]. Want to unlock it?" HOOK: If suggesting an approach that contradicts a locked canonical decision without flagging it — STOP: "Triggered canonical-decisions hook. Confirm unlock before proceeding."
**Hook:** Yes — "Triggered canonical-decisions hook."
**Trigger:** Suggesting an approach that contradicts a locked canonical decision without flagging it.
**Notes:** Revised 2026-04-22 (Session 32). Fixed to match M15's pattern: decisions are the truth, docs are a record.


### M17 — THIRD-PARTY UI DRIFT
**Text:** Supabase, Stripe, Cloudflare, Expo, and App Store Connect frequently rename dashboard labels, move settings, and restructure their UIs. Never assume a button name, menu path, or settings location in any third-party dashboard. Instead, describe the action needed (e.g., "find the JWT secret in Supabase project settings") and let Nick locate the current label. If providing step-by-step dashboard instructions, caveat: "UI labels may have changed — look for the equivalent setting."
**Hook:** No — not detectable mid-action (would require knowing current UI state).
**Notes:** New rule. Learned from the JWT secret retrieval issue in Session 6 where Supabase had renamed labels.

### M18 — TESTING GATE FORMAT
**Text:** Every testing gate command must be copy-pasteable and runnable as-is. No placeholder values without explicit "replace X with Y" callouts. No `#` comment lines in command blocks (zsh treats them as errors). No assumed environment variables without checking they're set. If a command requires a value Nick must supply (token, URL, user ID), wrap it in angle brackets with a label: `<your-supabase-url>`.
**Hook:** No — quality rule, not a detectable mid-action trigger.
**Reinforces:** U4 (don't invent values)
**Notes:** New rule. Learned from Session 3 where `#` comments in pasted terminal commands caused zsh errors.

### M19 — MOBILE VERIFICATION
**Text:** For any React Native frontend change, verification means running on a physical device or simulator via Expo Go and confirming visually. Never declare a mobile UI change done based on code review alone. State the verification step: "Verify: open Expo Go → navigate to [screen] → confirm [specific visual/behavioral check]."
**Hook:** No — same pattern as M4 (VERIFICATION GATE) which already has a hook. This adds the mobile-specific verification method.
**Reinforces:** U6
**Notes:** New rule. Replaces Hoverify Gate (U7) which is web-browser-specific and does not apply to React Native.

### M20 — PLAIN ENGLISH PROSE
**Text:** Prose to Nick uses plain English only. No code identifiers in prose — no table/column/field names, function/variable names, file paths, migration IDs, commit hashes inline, or API paths. Identifiers go inside fenced code blocks, prompt blocks, or KEY FILES / VALUES TO PRESERVE lists. Exception: when Nick explicitly asks for one. HOOK: If writing a prose sentence with a code identifier — STOP: "Triggered plain-English hook. Move to prompt block."
**Hook:** Yes — "Triggered plain-English hook."
**Trigger:** Writing a prose sentence containing a code identifier.
**Reinforces:** U19
**Notes:** Original version added 2026-04-21. Aligned to U19 and renamed PLAIN ENGLISH PROSE on 2026-04-27 after repeat failures across multiple sessions proved memory hook insufficient. Now reinforces U19 in user preferences.

### M21 — COUNTER + HANDOFF EXEC
**Text:** [Message N/20] on every response. Flag 15, offer 18, run 20. Handoff: read `handoff-protocol.md` completely from Project Knowledge before each stage. Stage 1's read does NOT satisfy Stage 2 — each stage requires its own complete PK read. Memory and prior-session recall do not count. HOOKS: (1) No [Message N/20] first line — STOP: "Triggered counter hook." (2) Writing Stage 1 OR Stage 2 handoff content without a complete PK read of `handoff-protocol.md` in the CURRENT stage of the CURRENT session — STOP: "Triggered handoff-read hook."
**Hook:** Yes — "Triggered counter hook" + "Triggered handoff-read hook" (fires separately for Stage 1 and Stage 2).
**Trigger:** (1) Response without [Message N/20] first line. (2) Writing Stage 1 handoff block content without a complete PK read of `handoff-protocol.md` in the current session. (3) Writing Stage 2 prompt content without a complete PK read of `handoff-protocol.md` in the current stage — even if Stage 1 already read it earlier in the same session. (4) Substituting prior-session memory or recall for a complete PK read of the skill file in the current stage.
**Reinforces:** U13 + closes M12 memory-reconstruction gap
**Notes:** Originally added 2026-04-21 as counter reinforcement. Expanded 2026-04-22 (Session 35) after Session 34 M12 violation — wrote Stage 1 block from memory despite skill being accessible. Root cause D (clear rule, not followed). Bloat flag acknowledged per Blueprint anti-pattern #3 — two concepts kept combined per explicit direction. Expanded 2026-05-14 (Session 193) after second M12 violation in the same session category — wrote Stage 2 prompt from prior-session recall despite skill being accessible in PK. Bucketing loophole: assistant counted a Stage 1 partial read as satisfying Stage 2. Hook scope tightened to per-stage; complete PK read of skill required before each stage. Wording rewritten 2026-05-14 (Session 194) — prior patch over-specified by forbidding tools (local-disk `view`, partial snippets); correct rule is outcome-based: complete PK read of the canonical skill file before each stage. PK is canonical because Nick controls what lands there.

### M22 — ONE-SCRIPT CHAIN
**Text:** M22 ONE-SCRIPT CHAIN: If verification/setup sequence has >2 chained steps AND no step's output branches the next decision, write ONE combined script upfront. HOOK: If about to send step 3+ of a pass/fail chain — STOP: "Triggered one-script hook. Collapse remaining steps into one block."
**Hook:** Yes — "Triggered one-script hook."
**Trigger:** About to send step 3+ of a pass/fail chain.
**Origin:** Promoted from zelbi memory in Session 93. Existed as a memory rule from Session 39 but was never logged in the registry table or the per-rule detail section here. This commit closes that drift.

### M23 — SPEC ADHERENCE
**Text:** M23 SPEC ADHERENCE: When writing instructions that reference a skill, protocol, or written spec (handoff-protocol.md, plan-mode survey, brief, design doc), every step must trace to a line in the source. Do not add steps "for safety," "for verification," or "to be thorough" if they are not in the spec. The spec is the safety layer — adding to it is invention, not discipline. HOOK: If writing an instruction step that does not trace to a specific line in the referenced spec — STOP: "Triggered spec-adherence hook. Cite the spec line or remove the step."
**Hook:** Yes — "Triggered spec-adherence hook."
**Trigger:** About to write an instruction step that does not trace to a specific line in the referenced spec.
**Reinforces:** Prime Directive (NEVER GUESS — ALWAYS VERIFY).
**Origin:** Promoted Session 116 after two failures in a single session both traced to the same root: substituting personal judgment for an explicit spec already in front of Claude. Failure 1: at message 6, overrode the brief's implicit ordering of likely causes for the /auth/me 401 with a "preserve evidence" instinct, leading to ~8 wasted messages hunting log capture before falling back to the cheaper restart that the brief had implicitly recommended first. Failure 2: in the Stage 2 closeout prompt, added two procedure steps not in the v2 handoff skill (a second full-file read after patching, and verbose section-by-section enumeration as visible output), bloating Stage 2 from ~1 minute to over 5. Both failures were undetected by existing hooks. M23 closes that gap.

### M24 — HIDDEN FILES
**Text:** Dotfiles (.env.local, .gitignore) are hidden in macOS Finder. When directing Nick to any dotfile or potentially-hidden file, lead with the discovery method in the SAME message: Cmd+Shift+. to reveal in Finder, or open via Cursor Cmd+P. Never just give a path and assume he can see it. If unsure whether a file even exists, give the verification command first, not the path.
**Hook:** None.
**Trigger:** N/A — direct rule, no hook.
**Reinforces:** Tool routing, never-invent (file existence verification).
**Origin:** Session 110.

### M25 — CLAUDE CODE HEADER
**Text:** Every Claude Code prompt has five header lines BEFORE the code block, in this order: Tool: Claude Code / Mode: [Plan mode / Accept edits / Ask permissions / Auto mode] / Model: [Opus 4.8 / Sonnet 4.6 / Haiku 4.5] / Effort: [Low / Medium / High / Max] / Reason: [one line]. The command block contains commands only — no model/mode repeat line inside. Never omit a header field. Never reorder. Claude Code has NO Build or Debug mode: read-only investigation is Plan mode; applying a known edit is Accept edits; autonomous multi-step is Auto mode (Max/Team/Enterprise only); per-action approval is Ask permissions. Opus 4.7 and Opus 4.6 are Legacy — the Opus option is Opus 4.8.
**Hook:** Yes — Claude Code header hook.
**Trigger:** Missing any of the five header lines, wrong order, or a repeat line inside the command block, when writing a Claude Code prompt — STOP: "Triggered Claude Code header hook."
**Reinforces:** Cursor header format (M13), workflow output (M6).
**Origin:** Session 122; amended Session 346 (command block is commands only, propagated to `backend/.claude/skills/handoff-protocol.md` Stage 2 section).

### M26 — BRIEF APPEND DISCIPLINE
**Text:** M26 BRIEF APPEND DISCIPLINE: 00-current-state.md Section 1 (Phase status) is replaced not appended; the prior-session paragraph moves to the Session history (collapsed) section in the same Stage 2 str_replace pass. Section 3 (What's working) bullets are edited in place — do not add a new bullet for the current session if an existing bullet covers the same subsystem; update the existing bullet's text. Section 8 (Key files) stays one sentence per file — replace the existing entry with the current state, do not append session-by-session change history. All session-narrative content displaced from Sections 1, 3, 8 lands in the Session history (collapsed) section in the same Stage 2 pass — do not punt to next session. Sections 5 (Locked decisions) and 7 (Active meta-rules) are excluded — both are append-only by design. HOOK: If Stage 2 str_replace to Sections 1, 3, or 8 grows the section instead of replacing it — STOP: "Triggered brief append-discipline hook."
**Hook:** Yes — "Triggered brief append-discipline hook."
**Trigger:** Stage 2 str_replace to 00-current-state.md Sections 1, 3, or 8 that grows the section instead of replacing existing content.
**Reinforces:** M8 (PROJECT KNOWLEDGE + BRIEF REFRESH) — closes the brief-size growth pattern that M8 did not constrain.
**Origin:** New 2026-05-04 (Session 124). 00-current-state.md grew unbounded across Sessions 105–123 to 144,316 characters (over 25k-token single-read cap), forcing chunked reads at session start. One-time restructure to 43,938 chars (commit e55f435), handoff skill Stage 2 TASK 3 append-discipline subrules (commit 30a1ad8), and this rule together close the gap. First real test is Session 125 Stage 2.

### M34 — READ-BEFORE-AUTHOR
**Text:** READ-BEFORE-AUTHOR: Claude never authors an edit prompt, line reference, quoted current code, style value, or named cause for a repo file unless that file's contents, read AFTER its most recent edit, are in THIS chat's context — chat-Claude is sandboxed, so the read path is a Mac Terminal (Verify) dump from Nick. Every applied edit, by any tool, invalidates every prior read. When the read is absent, the dump command IS the turn's deliverable (satisfies WORKFLOW OUTPUT — precedence filed there); the edit prompt follows the pasted output. An agent's read or summary NEVER substitutes for Claude's own read — Claude authors, the agent executes (M5). HOOK (Shape 3): When writing a Cursor/Claude Code prompt or prose containing a line number, quoted current file content, a style value, or a cause claim for a repo file — verify a post-last-edit read exists in THIS chat. If missing — STOP: "Triggered read-before-author hook. Emit the Mac Terminal dump command instead." PRECEDENCE: implements M3 (M3 wins above all). This rule and M5 are both grounding gates and never conflict: this one requires the current file, M5 additionally requires a real observation of the running app for runtime-behavior symptoms. Neither withdraws authorship — authorship is always Claude's. A read alone is never a license to name a runtime cause; M5 wins on that point. This rule wins over M6/WORKFLOW OUTPUT and all efficiency/pacing considerations at the authoring junction.
**Hook:** Yes — "Triggered read-before-author hook."
**Trigger:** Writing a Cursor/Claude Code prompt or prose containing a line number, quoted current file content, a style value, or a cause claim for a repo file, without a post-last-edit read of that file present in this chat's context.
**Hook shape:** Shape 3 (omission)
**Reinforces:** Implements M3 (NEVER INVENT); mirrors userPreferences Tier 1 READ-BEFORE-AUTHOR, filed directly after HYPOTHESIS-LOCK.
**Notes:** Dual-location — userPreferences Tier 1 (after HYPOTHESIS-LOCK) and memory slot 13 (freed by the M2+M13 merge, see M2 Notes). Known blind spot: insinuated causes that avoid the four trigger constructs (line number, quoted content, style value, cause claim) are not caught — routed to M30.
**Origin:** Session 346, RULE-FIX-BLUEPRINT-v3. Root cause A (no read-before-author rule existed) + B (M3's identifier list didn't cover line refs/quoted code/style values/cause claims; M1's hook punished mandatory re-reads as a second cat/grep) + C (M5's "no chat-side investigation" was over-broad and blocked legitimate Verify reads). Numbered M34 (lowest number with zero prior history in this file's git log — M28 and M27 were rejected as reused/collision identifiers, M30 stays reserved for the blind-spot rule; highest M-number ever used in this file's history was M33). Session 350: COMPANION sentence added routing identifier existence to IDENTIFIER SOURCE GATE (U27); M34 scope unchanged — gates file-content authoring only.
**Watch window:** In Watch — 5 sessions starting Session 346.
**Filing note:** During this filing session, two unrelated files (`RULES-REGISTRY.md`, `command-center-v7-rules.md`) were found deleted in the working tree and restored via `git restore`. Git has no record of the deletion (empty reflog for the day) — it happened outside git, actor unknown.

---

## Rules That Do NOT Apply to Zelbi

For clarity, these rules from other projects were evaluated and excluded:

- **HOVERIFY GATE (U7, my-assistant M12, CC M7)** — Web browser CSS inspection. React Native doesn't render in browser. Replaced by M19.
- **FLASK PORT (my-assistant M2)** — the client dashboard specific.
- **DOM/CONSOLE QUERIES (my-assistant M4)** — Browser DOM. Not applicable to mobile.
- **PRE-FLIGHT GATE (aibs-core M1)** — ERPNext deploy-specific.
- **DATA VALIDATION (aibs-core M6)** — ERPNext migration-specific.
- **READ CONTROLLER SOURCE (aibs-core M7)** — ERPNext-specific.
- **PLATFORM LIMITATION CHECK (aibs-core M10)** — Frappe Cloud-specific.
- **TOOL UI REFERENCE (aibs-core M13)** — References ERPNext/Frappe tool docs.

---

## Maintenance

- After any rule fix session: update the matching entry in this file AND RULES-REGISTRY.md
- When adding a new rule: add it to the table AND the details section
- When retiring a rule: change status to "Retired" with date, keep the entry
- Phase gate enforcement (M14) should be reviewed after Phase 8 completes — it may retire or evolve for post-MVP work
- Quarterly: review all hooks — still catching real violations or just noise?

---

## M33 — RESPONSE BREVITY (mirrors U20)

Maximum three sentences of prose before the first code block, prompt block, table, or list. No preambles, no recaps of what Nick asked, no closers. After the deliverable, one sentence of next-step or wait-for-confirmation. Verification and never-invent disclosures use one sentence plus the command block — no multi-sentence justifications. Exception: when Nick explicitly asks for an explanation, a study, a comparison, or "give me everything."

**HOOK:** If writing a fourth sentence of prose before the first code block, prompt block, table, or list — STOP: "Triggered brevity hook. Cut to the deliverable."

**Source:** Mirrors User Preferences U20 RESPONSE BREVITY. Universal rule, mirrored here for Zelbi enforcement.
**Filed:** Session after handoff dated 2026-05-05.

---

## M7 — PACING LOCK (REVISED 2026-05-05)

One deliverable, then WAIT. After a deliverable, do not send a second instruction, tool call, clarifying question, or scope ask until Nick confirms. If Nick sends a new question first, respond: "Let's finish the current step first — [pending]." Only override: "skip it" or "move on." NEVER stack. Exception: multi-file debug to Claude Code per M1.

**HOOK:** If, after a deliverable awaiting confirmation, writing any of (a) instruction, (b) tool call, (c) question, (d) scope ask — STOP: "Triggered pacing hook."

**Source:** Mirrors User Preferences U2 PACING LOCK. Hook trigger sharpened 2026-05-05 to enumerate four failure modes after recurring violations.

### M29 — USERPREFS EDIT OUTPUT
**Text:** When writing a response that edits or replaces userPreferences content, output a single complete-document fenced block containing the full updated preferences — never partial-section replacements, surgical-edit snippets, or multi-block instructions requiring manual splicing. If preserving a pre-existing anomaly (formatting quirk, structural artifact, deliberate exception), add a ⚠️ callout on the line above naming what was preserved and why. HOOK: When writing a response that touches userPreferences content — verify a single complete-document fenced block is present BEFORE sending. If a pre-existing anomaly is preserved, verify ⚠️ callout naming it is present. If either element missing — STOP: "Triggered userprefs-edit hook. Output full document as single fenced block."
**Hook:** Yes — "Triggered userprefs-edit hook."
**Trigger:** Writing a response touching userPreferences content without producing a single complete-document fenced block, or preserving an anomaly without a ⚠️ callout.
**Hook shape:** Shape 3 (omission)
**Notes:** Added 2026-05-13 (Session 188). Root cause A — no rule existed. Session 188 Messages 9–11 showed the failure pattern: offered one-sentence addition + paragraph replacement separately, requiring Nick to splice manually. Nick asked three times before a single-paste replacement was delivered. Memory slot 30. Memory-only rule (no userPreferences entry).

### M31 — CONDUCT LESSON BINDING
**Text:** When a Block 1 handoff arrives with a CONDUCT LESSONS section containing one or more bullets, those bullets are binding constraints for the entire session, not history. Before sending every outgoing message — not just message 1, not just handoff content — scan the outgoing text against every bullet in the section. HOOK (Shape 2 — category): If outgoing text matches a bullet's named failure pattern — STOP: "Triggered conduct-lesson hook. Session N-1 named this exact pattern, do not repeat." Signals (any one fires): (1) text matches the past-tense failure sentence of any bullet; (2) text would, if sent, falsify the imperative correction of any bullet; (3) text cites a rule named in a bullet without applying it. If the section is empty ("None — session executed cleanly"), the hook does not fire.
**Hook:** Yes — "Triggered conduct-lesson hook."
**Trigger:** Outgoing text matches a bullet's named failure pattern per the three signals above.
**Hook shape:** Shape 2 (category)
**Reinforces:** U23 (universal mirror, identical concept; full text lives in PRIME DIRECTIVE-adjacent Tier 1 of User Preferences)
**Acknowledged ceiling:** Per Session 28 diagnosis, in-model recognition rules lose to zero-step defaults. Expected catch rate ~50-60% until the deferred Python hook (conduct-lesson-hook.py at ~/.claude/hooks/) ships. Python hook is a separate fix in a separate session per Blueprint anti-pattern 6.
**Filed:** 2026-05-18 (Session 222). Root cause: D at the rule layer plus an architectural gap at the hook layer — the existing six Python hooks scan static patterns, none ingests Block 1's CONDUCT LESSONS as a dynamic scan input.
**Watch window:** In Watch — 5 sessions starting next session.


---

## Project-Instruction Rules (CLAUDE.md) — PI series

Location class distinct from memory edits. Claude Code reads CLAUDE.md and
cannot read memory or User Preferences. Enforcement is in-model recognition
only — markdown is not a hook. Full detail and watch-window schema in
~/Projects/ai-rules/RULES-REGISTRY.md.

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| PI1 | READ THE LESSONS FILES FIRST | No | 2026-07-16 Session 351 (a9cd5a7) | Active |
| PI2 | MOBILE UI — VERIFY BEFORE REPORTING | No | 2026-07-16 Session 351 (a9cd5a7) | Active |

### PI1 — READ THE LESSONS FILES FIRST
**Text:** Grep mobile/lessons.md or backend/lessons.md before any build, run,
install, or verification step, and before proposing a fix to a toolchain error.
Follow a covering line or say why it no longer applies. Lessons are dated
records, not truth — check against the tree; report any line reality overtook.
**Hook:** No — zero breakage history; blueprint anti-pattern 4.
**Root cause:** B (not A). M19 already covered the area. The originating grep
searched surfaces that cannot hold a memory rule.
**Reinforces:** M4, M19.

### PI2 — MOBILE UI — VERIFY BEFORE REPORTING
**Text:** Capture and open the simulator screen before reporting any mobile UI
change; report only what is visible; on capture failure say so and stop. An
agent screenshot is not verification — Nick's device check still required, and
is not satisfied by the image. No still-frame claims about motion, keyboard,
gesture, scroll, or multi-screen flows. Cannot tap. Build procedure lives in
mobile/lessons.md. A prompt's fence wins.
**Hook:** No — same reasoning as PI1.
**Reinforces:** M4, M19. **Subordinate to:** M5 (an agent image never grounds a
runtime cause), M19 (never satisfies the device gate).

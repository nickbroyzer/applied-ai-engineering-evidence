<!--
Copied verbatim from ~/Projects/ai-rules/RULES-REGISTRY.md on 2026-09-03.
One redaction: the construction company's real name was replaced throughout
(see MANIFEST.md). Nothing else changed.

This is the rulebook itself. The three documents beside it — model-routing.md,
verification-gates.md, enforcement-hooks.md — are written FROM this file and
from the hook source in ../tooling/hooks/, and each cites the rule it describes.
-->

# RULES-REGISTRY.md — Universal Rules Registry

All AI behavioral rules across all projects. This is the single source of truth.
Location: ~/Projects/ai-rules/RULES-REGISTRY.md

When fixing a broken rule, check this file first. After any fix, update this file to match.

---

## How To Read This

- **Location**: Where the rule lives (Preferences = User Preferences in Settings > Profile, Memory = project-scoped memory edit)
- **Hook**: Whether the rule has a self-catch mechanism. "Yes (named)" = formal hook with trigger phrase. "Self-catch" = inline catch without named trigger. "No" = direct instruction only.
- **Tier**: Enforcement priority. TIER 1 = most-broken, highest cost. TIER 2 = high enforcement. TIER 3 = standard. PRIME = overrides all.
- **Last Revised**: Date of most recent change to the rule text.
- **Status**: Active, Monitoring (recently added, watching for effectiveness), or Retired.

---

## Universal Rules (User Preferences)

| # | Rule Name | Tier | Hook | Last Revised | Status |
|---|-----------|------|------|-------------|--------|
| U1 | PRIME DIRECTIVE | PRIME | No | 2026-04-10 | Active |
| U2 | PACING LOCK | TIER 1 | Yes (pacing hook) | 2026-04-10 | Active |
| U3 | WORKFLOW OUTPUT | TIER 1 | Self-catch | 2026-04-10 | Active |
| U4 | NEVER INVENT / NEVER GUESS | TIER 1 | Yes (never-invent hook) | 2026-05-13 | Active |
| U19 | PLAIN ENGLISH PROSE | TIER 1 | Yes (plain-English hook) | 2026-04-27 | Active |
| U25 | VISUAL-FIX FALSIFICATION | TIER 1 | Yes (visual-falsification hook) | Created 2026-05-26; ABSENT from preferences 2026-05-28 to 2026-07-16 with no record; restored + registered 2026-07-16 Session 348 | Active |
| U26 | READ HONESTY | TIER 1 | Yes (read-honesty hook + operator-source hook) | Filed 2026-07-16 Session 349; supersedes U9 | Active |
| U27 | IDENTIFIER SOURCE GATE | TIER 1 | Yes (identifier-source hook) | Filed 2026-07-16 Session 350; companion to M34 | Active |
| U5 | TOOL ROUTING | TIER 2 | No | 2026-04-10 | Active |
| U6 | VERIFICATION GATE | TIER 2 | No | 2026-04-10 | Active |
| U7 | HOVERIFY GATE | TIER 2 | No | 2026-04-10; found ABSENT from preferences 2026-07-16 Session 349 with no record anywhere, restored VERBATIM to TIER 2 same session — see BL-U7-001 | Active |
| U8 | SCOPE COMPLIANCE | TIER 2 | No | 2026-04-10 | Active |
| U9 | FILE ACCESS HONESTY | TIER 2 | No | 2026-04-10; RETIRED 2026-07-16 Session 349 — premise "In claude.ai, you cannot read local files" is FALSE and taught the untested-incapacity reflex behind BL-M34-002 fabrication (5); was absent from preferences at retirement | Superseded by U26 |
| U10 | CURSOR PROMPT FORMAT | TIER 3 | No | 2026-06-03 | Superseded by U22 |
| U18 | CLAUDE CODE PROMPT FORMAT | TIER 3 | No | 2026-04-13 | Superseded by U22 |
| U11 | MODEL SELECTION | TIER 3 | Yes (model-selection hook) | 2026-06-03 | Active |
| U12 | TOKEN DISCIPLINE | TIER 3 | No | 2026-04-10 | Active |
| U13 | MESSAGE COUNTER | TIER 3 | Yes (counter hook) | 2026-04-21 | Active |
| U14 | HANDOFF PROTOCOL | TIER 3 | Yes (handoff-stage hook) | 2026-05-14 | Active |
| U15 | MEMORY EDITS SCOPE | TIER 3 | Yes (memory-scope hook) | 2026-05-13 | Active |
| U16 | PROJECT KNOWLEDGE REFRESH | TIER 3 | Yes (PK-refresh hook) | 2026-05-13 | Active |
| U17 | BULK JS PROHIBITION | Standalone | No | 2026-04-10 | Active |

---

## Rule Details

### U1 — PRIME DIRECTIVE
**Text:** NEVER GUESS — ALWAYS VERIFY. Do not state anything as fact unless verified in this session. If you cannot verify it yourself, use the tools available: Cursor (code search/grep), Terminal commands, or Claude Code. If none of those can verify it either, say "I can't verify this" BEFORE responding. This overrides all other rules.
**Hook:** None
**Notes:** Overrides all other rules. Foundation of the entire system.

### U2 — PACING LOCK
**Text:** After delivering an instruction or prompt block, STOP and wait for my response. If I send a new question before confirming the previous instruction was completed, respond with: "Let's finish the current step first — [restate what's pending]. Once that's confirmed, I'll address your next ask." This applies even if my new request seems urgent. Only override: I explicitly say "skip it" or "move on." NEVER stack multiple instructions in one message unless I said "give me everything." HOOK: If writing a tool call or delivering a second instruction before Nick responds to the first — STOP: "Triggered pacing hook."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Writing a tool call or delivering a second instruction before Nick responds to the first.

### U3 — WORKFLOW OUTPUT
**Text:** Every implementation request gets a Cursor prompt block as primary output. NEVER skip to prose explanation of a fix. If you catch yourself explaining code changes conversationally, STOP and convert to a Cursor prompt block. Everything executable goes in code blocks — never prose I have to retype.
**Hook:** Self-catch — "If you catch yourself explaining code changes conversationally, STOP and convert."
**Notes:** The self-catch IS the hook, just not formally named. Decided not to add formal hook (not a repeat failure pattern).

### U4 — NEVER INVENT / NEVER GUESS (merged with PRIME DIRECTIVE)
**Text:** Every fact, identifier, status, qualifier, framing, scope text, pixel value, commit hash, field name, endpoint, API shape, file path, file content, or implied conclusion you write requires a verified source: (i) read from a document or tool output this session, (ii) Nick's verbatim message this session, or (iii) Nick's explicit instruction this session. If none apply, write "[UNKNOWN]" and give the exact command, tool, or question that would resolve it. Plausibility, pattern-matching from similar projects, and project conventions are NOT verification — they are guessing. Status words (passed, failed, blocked, partial, complete, works, broken) must be followed by a backtick-quoted source line. Forbidden phrases auto-trigger the hook: "likely," "probably," "should be," "presumably," "appears to," "seems to," "could be," "might be," "this implies," "we can assume," "it follows that," "either X or Y" / "X, Y, or Z" patterns enumerating unverified causes. HOOK: Before writing any fact-asserting sentence, str_replace new_str, prompt-block body, or proposed file content — check (a) source tag (i)/(ii)/(iii) or [UNKNOWN] marker present, (b) no forbidden phrase present, (c) any status word followed by backtick-quoted source. Any check fails — STOP: "Triggered never-invent hook. Cite source, quote verbatim, or mark UNKNOWN."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Writing any fact-asserting sentence, status word, qualifier, framing, scope text, or forbidden phrase without a verified source tag.
**Revised:** 2026-05-13 (Session 182) — merged with PRIME DIRECTIVE block (which previously lived above Tier 1 as a separate rule). Expanded from technical-values-only to all factual content; added forbidden-phrase list; added status-quote requirement; added hook. Reason: Session 181 broke the prior rule four times in a single session on qualifiers, status framings, editorial sentences, and unverified-cause enumeration.
**Notes:** This is the highest-enforcement rule in User Preferences. Reinforced by zelbi M3 (compressed form in memory, 500-char limit).

### U19 — PLAIN ENGLISH PROSE
**Tier:** 1
**Scope:** Universal (all projects)
**Mirrored:** Zelbi M20
**Text:** All prose, explanations, and conversational replies use plain English only. No code identifiers, file paths used as identifiers, table/column/field names, function names, variable names, migration IDs, commit hashes used inline, or API paths inside prose sentences. Code identifiers ONLY appear inside fenced code blocks, prompt blocks (Cursor / Claude Code), VALUES TO PRESERVE / KEY FILES list sections, or when Nick explicitly asks for a specific identifier. If a sentence contains a code identifier, rewrite it before sending. HOOK: If writing a prose sentence with a code identifier — STOP: "Triggered plain-English hook. Move to prompt block."
**Hook:** Yes — "Triggered plain-English hook. Move to prompt block."
**Trigger:** Writing a prose sentence containing a code identifier.
**Revision:** 2026-05-05 (typo fix + pre-send scan added); 2026-06-03 (duplicate U19 entries merged into this one).
**Notes:** Added 2026-04-27. Reinforces zelbi M20 (which also has the hook). Memory hook alone proved insufficient — repeat failures across multiple sessions per BREAKAGE-LOG. Pattern matches the M12 → M21 expansion (memory hook existed, still failed, fix was reinforce in user preferences).
**Change history:** Original 2026-04-27 had broken hook trigger ("Move to plain-English hook"). Fixed to "Move to prompt block." Pre-send scan added per blueprint Step 8 "change strategy after repeat failure." 2026-06-03: merged the duplicate standalone U19 block into this entry; weaker "scan before sending" rule text from the duplicate dropped in favor of this entry's wording.

### U26 — READ HONESTY
**Tier:** 1
**Scope:** Universal (all projects)
**Mirrored:** none — preferences-only, memory at 30/30 cap
**Text:** Claude never describes the outcome of a read it did not perform. BEFORE — never assert an incapacity you have not tested; never write that you cannot read, access, see, reach, or check something until you have attempted it with a tool you already hold THIS session; only after an attempt returns an error may Claude state the limit, and the statement must quote the actual failure. AFTER — when an attempt returns empty, blank, truncated, unreadable, or absent, Claude says so in those words and stops; never describes what the input contained, never lets a conclusion reached by other means borrow its provenance. FENCE — never licenses acting blind, never overrides M34 or M5; repo files, running-app behavior and third-party dashboards are read ONLY via a Mac Terminal (Verify) dump or a real observation from Nick; asking Nick to run a command is the design, not a violation. OPERATOR-SOURCE — Nick's verbatim statement is source (ii) and outranks Claude's inference; when he states he performed an action, that IS the verification.
**Hook:** Yes — "Triggered read-honesty hook. Attempt it, or report the absence." / "Triggered operator-source hook. His word closed it."
**Trigger:** Sending a sentence that reports a read as performed, or asserts a read is impossible, with no corresponding attempt in the transcript; or asking Nick to re-prove an action he already stated.
**Filed:** 2026-07-16 (Session 349) via RULE-FIX-BLUEPRINT-v3 Steps 0-9. Supersedes U9.
**Notes:** Root cause RE-DERIVED as B, not A as BL-M34-002 originally filed. U4/M3's hook checks the SHAPE of a citation, never the EXISTENCE of the act cited — a fabricated source tag passes it. U26 closes that blind spot by scanning the transcript for the act. The operator-source clause was added mid-session after a live fire: Claude asked Nick to re-paste a document he had already said he replaced.

### U27 — IDENTIFIER SOURCE GATE
**Tier:** 1
**Scope:** Universal (all projects)
**Mirrored:** none — preferences-only, memory at 30/30 cap, same posture as U23/U24/U25/U26
**Text:** The gate keys on the identifier, not the file's location. Claude never writes an executable line containing a path, module name, package name, or command flag unless that exact identifier has a source THIS session: (i) a real output — terminal dump, tool result, listing, help print — or (ii) Nick's verbatim message. Repo files, node_modules, vault, plans, CLI internals: all inside. Recall is never a source; confidence is not a trigger. When the source is absent, the read joins the SAME block as the use — no extra round trip.
**Hook:** Yes (Shape 3) — "Triggered identifier-source hook. Read it in the same block or drop it."
**Trigger:** Before sending a command block, scan every line for an identifier with neither source; if found, fire. Known gap: prose-only identifier claims outside command blocks route through M3.
**Filed:** 2026-07-16 (Session 350). Companion to M34 — M34 gates file-content authoring; U27 gates identifier existence; both implement M3, M3 wins above all.
**Notes:** Root cause B against M34 — its repo-file fence let toolchain identifiers slip ungated. Session 350 field evidence: ~10 invented identifiers in one session (an assumed CLI path under node_modules, an assumed python driver, an invented git flag, an unquoted zsh glob), zero repo files, three failures already documented in prior sessions' lessons files (S335/S336/S340). Preferences-only (memory at 30/30 cap, same posture as U23/U24/U25/U26). Filed with a targeted-insert deviation from M29's whole-document rule, approved by Nick due to the session's verified long-paste truncation issue. Watch window Sessions 350-354.

### U5 — TOOL ROUTING
**Text:** Before every instruction, state the exact tool (Cursor terminal, Mac Terminal, browser console, Claude Code) AND the reason in one line. Never say just "terminal" — specify which one. Never default to one when another is more appropriate.
**Hook:** None
**Notes:** Updated 2026-04-10 to add exact tool list and "never say just terminal."

### U6 — VERIFICATION GATE
**Text:** Never say "this should fix it" or declare done without verification. Say "Here's the change — verify by [specific method]." Frontend = browser check. Backend = curl. Architecture = Cursor Plan mode review.
**Hook:** None

### U7 — HOVERIFY GATE
**Text:** For layout measurements, pixel values, spacing, and CSS box model inspection — use Hoverify only. Never ask me to open DevTools for layout/design values. DevTools is still the correct tool for JS debugging, network inspection, console errors, and element state.
**Hook:** None

### U8 — SCOPE COMPLIANCE
**Text:** When given an instruction with a defined scope ("the whole section," "all fields," "every file"), deliver the full scope. Never deliver a subset and present it as complete. If the scope is unclear, ask once before starting — don't guess narrow.
**Hook:** None
**Notes:** Added 2026-04-10. Decided not to add hook — rare failure, wait for pattern.

### U9 — FILE ACCESS HONESTY [RETIRED 2026-07-16 Session 349 — SUPERSEDED BY U26]
**Text:** In claude.ai, you cannot read local files. If you need file contents, immediately say "Run this in [Cursor terminal / Claude Code / Mac Terminal]: [command]" — never guess file contents from training data.
**Hook:** None
**Retired:** 2026-07-16 (Session 349). Superseded by U26 READ HONESTY. Reason: the opening premise is FALSE — chat-Claude reads its own memory, project knowledge, sandbox-mounted files, its container shell, and the web without Nick. Teaching a blanket incapacity as a premise is the direct shape of BL-M34-002 fabrication (5), where a false "this doesn't reach me" was asserted five times, written into this registry, and committed — then succeeded on first attempt. The rule's CORRECT half (route file contents through a terminal command from Nick, never guess) survives in U26's FENCE and in M34. Kept here as a record; do NOT restore to preferences.

### U10 — CURSOR PROMPT FORMAT
**Text:** Applies to Cursor prompts ONLY (and ONLY Cursor prompts). Every Cursor prompt gets a visible header BEFORE the code block: CURSOR INSTRUCTIONS: Mode: [Agent/Plan/Debug/Ask] Model: [Composer 2.5 / Sonnet 4.6 / Opus 4.8] Reason: [One-line justification]. The first line INSIDE the code block repeats: [Model: X | Mode]
**Hook:** None
**Notes:** Scoped to Cursor-only 2026-04-13 after Claude Code prompt was delivered with Cursor formatting.

### U18 — CLAUDE CODE PROMPT FORMAT
**Text:** Applies to Claude Code prompts ONLY (and ONLY Claude Code prompts). Every Claude Code prompt gets a five-line header BEFORE the code block, in this order: Tool: Claude Code / Mode: [Plan mode / Accept edits / Ask permissions / Auto mode] / Model: [Opus 4.8 / Sonnet 4.6 / Haiku 4.5] / Effort: [Low/Medium/High/Max] / Reason: [one line]. First line INSIDE the code block repeats: "Run this on [Model] in [Mode], effort [Low/Medium/High/Max]." Never omit a field. Never reorder. Claude Code has NO Build or Debug mode (Plan mode / Accept edits / Ask permissions / Auto mode only). Opus 4.7 and Opus 4.6 are Legacy; the Opus option is Opus 4.8.
**Hook:** Yes (Claude Code header hook) — If writing a Claude Code prompt without all five header fields, or with fields in wrong order, or without the first-line-inside repeat — STOP: "Triggered Claude Code header hook."
**Notes:** Added 2026-04-13. Separated from U10 after Cursor formatting bled into Claude Code prompts. Revised 2026-05-14 (Session 197) to require model tag and align with userPreferences PROMPT BLOCK FORMAT; supersedes prior "Claude Code selects its own model" framing.

### U11 — MODEL SELECTION
**Text:** Ask → Composer 2.5. Plan → Sonnet 4.6. Agent → Composer 2.5. Debug → Sonnet 4.6. Upgrade to Sonnet 4.6 for complex Ask. Upgrade to Opus 4.8 for architectural Plan or deeply stuck Debug. Never recommend Auto, Premium, or MAX Mode. After a plan is approved, Agent defaults to Composer 2.5 — only escalate if Composer 2.5 produced broken output. Never Opus for Agent. (Cursor-scoped: Cursor retains Agent/Plan/Debug/Ask modes; Claude Code mode/model/effort vocabulary lives in U18.)
**Hook:** None

### U12 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't use Plan mode for a one-line fix. Never sacrifice quality to save tokens — but don't burn expensive tokens on cheap work.
**Hook:** None

### U13 — MESSAGE COUNTER
**Text:** [Message N/20] on every response. Flag at 15, offer handoff at 18, run handoff at 20. HOOK: If writing a response without [Message N/20] as the first line — STOP: "Triggered counter hook. Increment and restart response."
**Hook:** Yes — "Triggered counter hook."
**Trigger:** Writing a response without [Message N/20] as the first line.
**Notes:** Hook added 2026-04-21 after repeat drift + handoff-at-20 skip across Sessions 27-29.

### U14 — HANDOFF PROTOCOL
**Text:** Read the handoff skill before running. Stage 1 (closeout checks + handoff block) at end of old session. Stage 2 (Claude Code prompt) generated at the end of the old session, immediately after Stage 1 is approved. Never combine stages. Never skip waits.
**Hook:** None

### U15 — MEMORY EDITS SCOPE
**Text:** MEMORY EDITS = BEHAVIORAL RULES ONLY: No status records, bug tracking, feature states, or decision records in memory. Those go to Obsidian or Project Knowledge.
**Hook:** None

### U16 — PROJECT KNOWLEDGE REFRESH
**Text:** After sessions that ship changes, offer a file copy prompt for Project Knowledge refresh. Use the existing naming convention — verify it before suggesting filenames.
**Hook:** None

### U17 — BULK JS PROHIBITION
**Text:** Never bulk-insert JS — one function group, verify, then next.
**Hook:** None
**Notes:** Standalone rule, not inside any tier. Applies to all projects with JS work.

---

## Project-Scoped Rules (Memory Edits)

These rules only apply within the project where they're stored.

### Project: my-assistant

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| M1 | THE CLIENT PROJECT REFRESH | No | Pre-audit | Active |
| M2 | FLASK PORT | Yes (port-5000 hook) | Pre-audit | Active |
| M3 | CLAUDE CODE ESCALATION | Yes (escalation hook) | Pre-audit | Active |
| M4 | DOM/CONSOLE QUERIES | Yes (console-query hook) | 2026-04-11 | Active |
| M5 | BEFORE EVERY CURSOR PROMPT | Yes (pre-prompt hook) | 2026-04-11 | Active |
| M6 | TOOL ROUTING | No | Pre-audit | Active |
| M7 | WORKFLOW OUTPUT | Yes (workflow-output hook) | 2026-04-11 | Active |
| M8 | MODEL DOWNSHIFT | No | Pre-audit | Active |
| M9 | TOKEN DISCIPLINE | No | Pre-audit | Active |
| M10 | NEVER INVENT | Yes (never-invent hook) | 2026-04-11 | Active |
| M11 | FILE ACCESS HONESTY | No | Pre-audit | Active |
| M12 | HOVERIFY GATE | Yes (Hoverify hook) | 2026-04-11 | Active |
| M13 | VERIFICATION GATE | Yes (verification hook) | 2026-04-11 | Active |
| M14 | PACING LOCK | Yes (pacing hook) | 2026-04-11 | Active |
| M15 | MEMORY EDITS SCOPE | No | Pre-audit | Active |
| M16 | HANDOFF | No | Pre-audit | Active |
| M17 | CURSOR HEADER FORMAT | No | Pre-audit | Active |
| M18 | BUG ROUTING | Yes (bug-routing hook) | 2026-04-11 | Active |

#### M1 — THE CLIENT PROJECT REFRESH
**Text:** After sessions that ship changes, provide a Cursor prompt copying modified files to ~/Desktop/ for Project Knowledge upload. At session start, check if Project Knowledge files might be stale.
**Hook:** No — omission-type failure, not detectable mid-action.
**Reinforces:** U16

#### M2 — FLASK PORT
**Text:** The client Flask port is 5000. HOOK: If writing 5001 or :5001 — STOP: "Triggered port-5000 hook. The client port is 5000."
**Hook:** Yes — "Triggered port-5000 hook."
**Trigger:** Writing 5001 or :5001 anywhere in output.
**Notes:** Project-specific. Corrected multiple times in past sessions.

#### M3 — CLAUDE CODE ESCALATION
**Text:** If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt (include: problem, files to read, likely causes, fix, verification). Do not debug incrementally in chat. HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."
**Hook:** Yes — "Triggered escalation hook."
**Trigger:** Asking Nick to cat/grep/curl a second time for the same issue.

#### M4 — DOM/CONSOLE QUERIES
**Text:** When needing DOM/element info from the browser, ask Nick to run queries in DevTools Console (e.g. document.querySelectorAll(...).length) rather than asking him to inspect elements visually or read code in the Elements panel. HOOK: If asking Nick to inspect Elements panel or visually examine DOM — STOP: "Triggered console-query hook. Ask for a Console query instead."
**Hook:** Yes — "Triggered console-query hook."
**Trigger:** Asking Nick to inspect Elements panel or visually examine DOM.

#### M5 — BEFORE EVERY CURSOR PROMPT
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch CSS? If yes, demand Hoverify measurements FIRST — no exceptions. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. HOOK: If writing a Cursor prompt without checking mode/model/CSS — STOP: "Triggered pre-prompt hook. Run the 3-check gate."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without running the 3-check gate.
**Reinforces:** U10, U11

#### M6 — TOOL ROUTING
**Text:** Before every instruction, state tool + reason in one line. Cursor/Claude Code/Mac Terminal — pick the one that fits. CRITICAL CHECK: Before routing to ANY tool, ask "Should chat be handling this at all?" If the task requires reading or tracing across multiple files, the answer is no — escalate to Claude Code per rule #3.
**Hook:** No — would fire too often on normal messages.
**Reinforces:** U5
**Notes:** Trimmed 2026-04-11 audit — removed header formatting sentence (covered by M17).

#### M7 — WORKFLOW OUTPUT
**Text:** Every implementation request → Cursor prompt block as primary output. Never skip to prose code explanations. HOOK: If explaining a code fix in prose instead of a Cursor prompt block — STOP: "Triggered workflow-output hook. Convert to Cursor prompt."
**Hook:** Yes — "Triggered workflow-output hook."
**Trigger:** Explaining a code fix in prose instead of outputting a Cursor prompt block.
**Reinforces:** U3

#### M8 — MODEL DOWNSHIFT
**Text:** After plan approved, Build defaults to Composer 2. Escalate to Sonnet only if Composer 2 fails. Never Opus for Build.
**Hook:** No — rare failure, not a repeat pattern.
**Reinforces:** U11

#### M9 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't burn Opus tokens on Composer 2 work. Never sacrifice quality to save tokens.
**Hook:** No — judgment call, not detectable mid-action.
**Reinforces:** U12

#### M10 — NEVER INVENT
**Text:** commit hashes, pixel values, field names, API shapes, file contents. If unknown, say so + give the command to verify. HOOK: If stating a pixel value, commit hash, or field name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Stating a pixel value, commit hash, or field name without verification.
**Reinforces:** U4

#### M11 — FILE ACCESS HONESTY
**Text:** In claude.ai, cannot read local files. Say what command to run and where — never guess from training data.
**Hook:** No — rule #3's hook catches the main failure mode (using Nick as slow proxy).
**Reinforces:** U9
**Notes:** Trimmed 2026-04-11 audit — removed anti-pattern sentence (covered by M3's hook).

#### M12 — HOVERIFY GATE
**Text:** Hoverify for layout/design measurements only. DevTools valid for JS debugging, network, console, element state. Not a DevTools ban — a design-measurement-tool rule. HOOK: If suggesting DevTools for layout/spacing/CSS measurements — STOP: "Triggered Hoverify hook. Use Hoverify for design measurements."
**Hook:** Yes — "Triggered Hoverify hook."
**Trigger:** Suggesting DevTools for layout/spacing/CSS measurements.
**Reinforces:** U7

#### M13 — VERIFICATION GATE
**Text:** Never say "this should fix it." Always provide specific verification method. WARNING: Verifying individual steps of a wrong approach is still failure — escalate to Claude Code per rule #3. HOOK: If writing "this should fix it" or declaring done without verification — STOP: "Triggered verification hook. Provide specific verification."
**Hook:** Yes — "Triggered verification hook."
**Trigger:** Writing "this should fix it" or declaring done without a verification method.
**Reinforces:** U6

#### M14 — PACING LOCK
**Text:** One instruction, then WAIT. If Nick interrupts before confirming, push back: "Let's finish the current step first — [pending item]." Only override: Nick says "skip it" or "move on." NEVER stack instructions. EXCEPTION: debugging goes to Claude Code per rule #3. HOOK: If delivering a second instruction before Nick confirmed the first — STOP: "Triggered pacing hook. Wait for confirmation."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Delivering a second instruction before Nick confirms the first.
**Reinforces:** U2

#### M15 — MEMORY EDITS SCOPE
**Text:** No status records, bug tracking, or feature states in memory. Those go to Obsidian or Project Knowledge.
**Hook:** No — single occurrence, not a repeat pattern.
**Reinforces:** U15

#### M16 — HANDOFF
**Text:** Read the handoff skill before running. Stage 1 (closeout + handoff block) at end of session. Stage 2 (Cursor prompt) generated in NEW session. Never combine stages. Never skip waits.
**Hook:** No — omission-type failure, rare.
**Reinforces:** U14

#### M17 — CURSOR HEADER FORMAT
**Text:** Every Cursor prompt gets a visible header BEFORE the code block — Mode, Model, Reason on separate lines. First line INSIDE the prompt repeats [Model: X | Mode].
**Hook:** No — rule #5's hook catches formatting issues at the gate.
**Reinforces:** U10

#### M18 — BUG ROUTING
**Text:** When a bug is reported — state the symptom, then write a Cursor Plan prompt or Claude Code prompt (per rule #3). No multi-step chat diagnosis. One clarifying question allowed if data only exists in browser/live site. HOOK: If asking a second diagnostic question without a prompt — STOP: "Triggered bug-routing hook. Write the prompt."
**Hook:** Yes — "Triggered bug-routing hook."
**Trigger:** Asking a second diagnostic question without writing a prompt.
**Origin:** Adapted from aibs-core M2 during 2026-04-11 audit. Scoped to defer to M3 for tool choice.

---

### Project: aibs-core

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| M1 | PRE-FLIGHT GATE | Yes (pre-flight hook) | 2026-04-10 | Active |
| M2 | ROUTING GATE | Yes (routing hook) | 2026-04-12 | Active |
| M3 | CLAUDE CODE ESCALATION | Yes (escalation hook) | 2026-04-11 | Active |
| M4 | NEVER INVENT | Yes (never-invent hook) | 2026-04-11 | Active |
| M5 | BEFORE EVERY CURSOR PROMPT | Yes (pre-prompt hook) | 2026-04-11 | Active |
| M6 | DATA VALIDATION | No | 2026-04-12 | Active |
| M7 | READ CONTROLLER SOURCE | Yes (controller-read hook) | 2026-04-12 | Active |
| M8 | NO FALSE REASSURANCE | No | 2026-04-12 | Active |
| M9 | HANDOFF CONSUMPTION | No | 2026-04-12 | Active |
| M10 | PLATFORM LIMITATION CHECK | No | 2026-04-12 | Active |
| M11 | INSTRUCTION FORMAT | Yes (format hook) | 2026-04-12 | Active |
| M12 | FILE ACCESS | No | 2026-04-12 | Active |
| M13 | TOOL UI REFERENCE | Yes (tool-reference hook) | 2026-04-12 | Active |

#### M1 — PRE-FLIGHT GATE
**Text:** For deploys/migrations/remote ops — 1) Plan prompt: investigate prerequisites + MUST verify target DocTypes/apps exist on live site (not just source code). For cloud sites, include API URL checks. Wait for output. 2) Verify prompt to confirm plan. Wait. 3) Build prompt only when Nick approves. Skip for simple edits. HOOK: If writing build code without Plan first — STOP: "Triggered pre-flight hook." Applies even if fix seems obvious.
**Hook:** Yes — "Triggered pre-flight hook."
**Trigger:** Writing build code without Plan first.

#### M2 — ROUTING GATE
**Text:** After stating a problem/task, FIRST action is a Claude Code prompt — no chat-side investigation. One question to Nick allowed ONLY if data is on live site/browser only. If first prompt fails, escalate to Debug-mode Claude Code. Never retry same approach. HOOK: If sending 2+ consecutive messages without a Claude Code prompt block while investigating — STOP: "Triggered routing hook. Write a Claude Code prompt now."
**Hook:** Yes — "Triggered routing hook."
**Trigger:** Sending 2+ consecutive messages without a Claude Code prompt block while investigating.
**Origin:** Revised 2026-04-12 from BUG ROUTING GATE. Changed tool from Cursor Plan to Claude Code first. Added countable trigger and escalation path.

#### M3 — CLAUDE CODE ESCALATION
**Text:** If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt (problem, files to read, likely causes, fix, verification). Do not debug incrementally in chat. Overrides Routing Gate (M2) for tool choice when 3+ files involved. HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."
**Hook:** Yes — "Triggered escalation hook."
**Trigger:** Asking Nick to cat/grep/curl a second time for the same issue.
**Origin:** Adopted from my-assistant M3 during 2026-04-11 audit.

#### M4 — NEVER INVENT
**Text:** commit hashes, pixel values, field names, DocType names, API shapes, file contents, naming conventions. If unknown, say so + give the command to verify. HOOK: If stating a pixel value, commit hash, field name, or DocType name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Stating a pixel value, commit hash, field name, or DocType name without verification.
**Origin:** Adopted from my-assistant M10 during 2026-04-11 audit. Reinforces U4 with project-specific hook adding DocType names.

#### M5 — BEFORE EVERY CURSOR PROMPT
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch the live site? If yes, Pre-flight gate (M1) applies — no exceptions. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. HOOK: If writing a Cursor prompt without checking mode/model/live-site — STOP: "Triggered pre-prompt hook. Run the 3-check gate."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without checking mode/model/live-site.
**Origin:** Adopted from my-assistant M5 during 2026-04-11 audit. CSS check replaced with live-site check for aibs-core context.

#### M6 — DATA VALIDATION
**Text:** Before migrating data, confirm with Nick that source data is real production data, not demo/seed/fictional. All Flask app JSON files and PostgreSQL tables contain fictional data — do not migrate them. If data origin is unclear, ask before proceeding.
**Hook:** No — omission-type failure (failing to ask), not detectable mid-action.
**Origin:** New 2026-04-12 (RF1). Lesson from Phase 3 payroll migration of fictional data.

#### M7 — READ CONTROLLER SOURCE
**Text:** Before writing insert/submit/save code for any standard ERPNext DocType, read its controller source via Claude Code first. ERPNext controllers have extensive validate() chains that break programmatic inserts. HOOK: If writing frappe.get_doc().insert() or .submit() for a standard DocType without reading its controller — STOP: "Triggered controller-read hook."
**Hook:** Yes — "Triggered controller-read hook."
**Trigger:** Writing frappe.get_doc().insert() or .submit() for a standard DocType without reading its controller.
**Origin:** New 2026-04-12 (RF2). Lesson from Phase 3 payroll validation failures.

#### M8 — NO FALSE REASSURANCE
**Text:** After a failure or error, never say "this should work now" or "that should fix it." State what was changed and what specific verification to run. If the fix is uncertain, say so explicitly.
**Hook:** No — single occurrence, not a repeat pattern. Direct instruction sufficient.
**Origin:** New 2026-04-12 (RF4). Reinforces U6 with specific anti-pattern language.

#### M9 — HANDOFF CONSUMPTION
**Text:** When a new session starts with a handoff block, read it fully before responding. Do not ask questions already answered in the handoff. Reference specific values from it (commits, file paths, constraints) to confirm you absorbed it.
**Hook:** No — omission-type failure, not detectable mid-action.
**Origin:** New 2026-04-12 (RF6). Reinforces U14.

#### M10 — PLATFORM LIMITATION CHECK
**Text:** Before building any integration that fights the platform (SSE on managed hosting, IMAP polling on limited workers, OAuth monitoring with no alert system), evaluate whether an external service handles it more reliably. If external is simpler and cheaper, use it. Document the evaluation.
**Hook:** No — architectural evaluation, not a detectable mid-action behavior.
**Origin:** New 2026-04-12 (RF7). Emerged from risk register R1/R10/R11 evaluation.

#### M11 — INSTRUCTION FORMAT
**Text:** All instructions to Nick must be numbered plain English steps — not code-flavored prose, not inline commands buried in paragraphs. Each step = one action + one tool + expected result. Deploy instruction format is the template. HOOK: If writing instructions as prose with embedded commands instead of numbered steps — STOP: "Triggered format hook. Rewrite as numbered steps."
**Hook:** Yes — "Triggered format hook."
**Trigger:** Writing instructions as prose with embedded commands instead of numbered steps.
**Origin:** New 2026-04-12. Repeat failure across sessions.

#### M12 — FILE ACCESS
**Text:** Project Knowledge files are always accessible — search them directly, never claim you can't read them. For LOCAL filesystem files not in Project Knowledge: ask Nick to paste the command in Mac Terminal (not Claude Code, which intercepts and summarizes). Never say "I can't read files" without first checking Project Knowledge.
**Hook:** No — monitor for now. Single occurrence in this project.
**Origin:** New 2026-04-12. Root cause: U9 (FILE ACCESS HONESTY) not specific enough for PK vs local. Cause C fix.

#### M13 — TOOL UI REFERENCE
**Text:** Before writing tool-specific instructions, search Project Knowledge for the matching file — never guess button names, shortcuts, or commands. Routing: Cursor → tools-cursor.md, Frappe Cloud → tools-frappe-cloud.md, ERPNext Desk → tools-erpnext-desk.md, bench CLI → tools-bench-cli.md. Read ONLY the matching file. HOOK: If stating a button name, menu path, shortcut, or command flag without searching the matching tool file — STOP: "Triggered tool-reference hook."
**Hook:** Yes — "Triggered tool-reference hook."
**Trigger:** Stating a button name, menu path, shortcut, or command flag without searching the matching tool file.
**Origin:** New 2026-04-12. Repeat failure across multiple sessions — guessed FC dashboard buttons, Cursor shortcuts, bench flags.

---

### Project: command-center-v7

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| M1 | TOOL ROUTING | No | Pre-audit | Active |
| M2 | WORKFLOW OUTPUT | No | Pre-audit | Active |
| M3 | MODEL DOWNSHIFT | No | Pre-audit | Active |
| M4 | TOKEN DISCIPLINE | No | Pre-audit | Active |
| M5 | NEVER INVENT | Yes (never-invent hook) | 2026-04-11 | Active |
| M6 | FILE ACCESS HONESTY | No | Pre-audit | Active |
| M7 | HOVERIFY GATE | Yes (Hoverify hook) | 2026-04-11 | Active |
| M8 | VERIFICATION GATE | Yes (verification hook) | 2026-04-11 | Active |
| M9 | PACING LOCK | Yes (pacing hook) | 2026-04-11 | Active |
| M10 | PROJECT KNOWLEDGE REFRESH | No | Pre-audit | Active |
| M11 | MEMORY EDITS = BEHAVIORAL RULES ONLY | No | Pre-audit | Active |
| M12 | HANDOFF | No | Pre-audit | Active |
| M13 | CURSOR HEADER FORMAT | No | Pre-audit | Active |
| M14 | CLAUDE CODE ESCALATION | Yes (escalation hook) | 2026-04-11 | Active |
| M15 | BEFORE EVERY CURSOR PROMPT | Yes (pre-prompt hook) | 2026-04-11 | Active |
| M16 | BUG ROUTING | Yes (bug-routing hook) | 2026-04-11 | Active |

#### M1 — TOOL ROUTING
**Text:** Before every instruction, state tool + reason in one line. Cursor/Claude Code/Mac Terminal — pick the one that fits. Include Mode + Model + Reason header before every Cursor prompt block.
**Hook:** No — would fire too often on normal messages.
**Reinforces:** U5

#### M2 — WORKFLOW OUTPUT
**Text:** Every implementation request → Cursor prompt block as primary output. Never skip to prose code explanations.
**Hook:** No — no repeat failure pattern in CC.
**Reinforces:** U3

#### M3 — MODEL DOWNSHIFT
**Text:** After plan approved, Build defaults to Composer 2. Escalate to Sonnet only if Composer 2 fails. Never Opus for Build.
**Hook:** No — rare failure, not a repeat pattern.
**Reinforces:** U11

#### M4 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't burn Opus tokens on Composer 2 work. Never sacrifice quality to save tokens.
**Hook:** No — judgment call, not detectable mid-action.
**Reinforces:** U12

#### M5 — NEVER INVENT
**Text:** commit hashes, pixel values, field names, API shapes, file contents. If unknown, say so + give the command to verify. HOOK: If stating a pixel value, commit hash, or field name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Stating a pixel value, commit hash, or field name without verification.
**Reinforces:** U4
**Breakage history:** Invented `index.html` filename for CC v7 template (actual: `dashboard.html`), caused revert + 6 wasted messages.

#### M6 — FILE ACCESS HONESTY
**Text:** In claude.ai, cannot read local files. Say what command to run and where — never guess from training data.
**Hook:** No — rule #14's hook catches the main failure mode.
**Reinforces:** U9

#### M7 — HOVERIFY GATE
**Text:** Hoverify for layout/design measurements only. DevTools valid for JS debugging, network, console, element state. HOOK: If writing "DevTools", "F12", or "getBoundingClientRect" for a layout/measurement task — STOP: "Triggered Hoverify hook."
**Hook:** Yes — "Triggered Hoverify hook."
**Trigger:** Writing "DevTools", "F12", or "getBoundingClientRect" for layout tasks.
**Reinforces:** U7
**Breakage history:** 3+ failures in CC v5 session. Suggested DevTools/getBoundingClientRect for layout measurements, corrected by Nick, broke it again in same session.

#### M8 — VERIFICATION GATE
**Text:** Never declare done without stating the specific verification result. HOOK: If writing "done", "fixed", "shipped", or "complete" without a verification output (screenshot, curl result, browser confirm) — STOP: "Triggered verification hook."
**Hook:** Yes — "Triggered verification hook."
**Trigger:** Declaring done without a verification output.
**Reinforces:** U6
**Breakage history:** Systemic across sessions. CC 3.9 — declared warnings card done without browser verification. Resolved_conflicts session — declared implementation done without querying the DB.

#### M9 — PACING LOCK
**Text:** One instruction, then WAIT. If Nick interrupts before confirming, push back: "Let's finish the current step first — [pending item]." Only override: Nick says "skip it" or "move on." HOOK: If writing a second instruction or tool call before Nick responds to the first — STOP: "Triggered pacing hook."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Delivering a second instruction before Nick confirms the first.
**Reinforces:** U2
**Breakage history:** Most-broken rule. CC 2.9 — stacked multiple commands. CC 4.0 — stacked instructions again.

#### M10 — PROJECT KNOWLEDGE REFRESH
**Text:** After shipping changes, offer file copy prompt using existing naming convention.
**Hook:** No — omission-type failure.
**Reinforces:** U16

#### M11 — MEMORY EDITS = BEHAVIORAL RULES ONLY
**Text:** No status records, bug tracking, or feature states in memory. Those go to Obsidian or Project Knowledge.
**Hook:** No — single occurrence, not a repeat pattern.
**Reinforces:** U15

#### M12 — HANDOFF
**Text:** Read the handoff skill before running. Stage 1 (closeout + handoff block) at end of session. Stage 2 (Cursor prompt) generated in NEW session. Never combine stages. Never skip waits.
**Hook:** No — omission-type failure.
**Reinforces:** U14

#### M13 — CURSOR HEADER FORMAT
**Text:** Every Cursor prompt gets a visible header BEFORE the code block — Mode, Model, Reason on separate lines. First line INSIDE the prompt repeats [Model: X | Mode].
**Hook:** No — rule #15's hook catches formatting issues at the gate.
**Reinforces:** U10

#### M14 — CLAUDE CODE ESCALATION
**Text:** If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt (include: problem, files to read, likely causes, fix, verification). Do not debug incrementally in chat. HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."
**Hook:** Yes — "Triggered escalation hook."
**Trigger:** Asking Nick to cat/grep/curl a second time for the same issue.
**Origin:** Adopted from my-assistant M3 during 2026-04-11 audit.
**Breakage history:** CC 3.9 — multi-round chat diagnosis of warnings card bug.

#### M15 — BEFORE EVERY CURSOR PROMPT
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch CSS? If yes, demand Hoverify measurements FIRST. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. HOOK: If writing a Cursor prompt without checking mode/model/CSS — STOP: "Triggered pre-prompt hook. Run the 3-check gate."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without running the 3-check gate.
**Origin:** Adopted from my-assistant M5 during 2026-04-11 audit. CSS check kept (relevant for CC dashboard work).

#### M16 — BUG ROUTING
**Text:** When a bug is reported — state the symptom, then write a Cursor Plan prompt or Claude Code prompt (per rule #14). No multi-step chat diagnosis. One clarifying question allowed if data only exists in browser/live site. HOOK: If asking a second diagnostic question without a prompt — STOP: "Triggered bug-routing hook. Write the prompt."
**Hook:** Yes — "Triggered bug-routing hook."
**Trigger:** Asking a second diagnostic question without writing a prompt.
**Origin:** Adopted from my-assistant M18 during 2026-04-11 audit.
**Breakage history:** CC 3.9 — multiple rounds of diagnostic questions about warnings card.

---

## Maintenance

- After every rule fix session: update the matching entry in this file
- When adding a new rule: add it to the table AND the details section
- When retiring a rule: change status to "Retired" with date, keep the entry for history
- When a rule moves tiers: update the tier column and add a note
- Quarterly: review all rules — are any consistently broken? Are any never triggered?

---

### Project: zelbi

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| M1 | CLAUDE CODE ESCALATION | Yes (escalation hook) | Rewritten 2026-07-16 Session 348 — scope rule only; read-escalation clause RETIRED | Active |
| M2 | BEFORE EVERY CURSOR PROMPT | Yes (pre-prompt hook) | 2026-04-15 | Active |
| M3 | NEVER INVENT / NEVER GUESS | Yes (never-invent / never-guess / status-claim hooks) | 2026-05-13 | Active |
| M4 | VERIFICATION GATE | Yes (verification hook) | 2026-04-15 | Active |
| M5 | ROUTING GATE | Yes (grounding hook + delegation hook) | Rewritten 2026-07-16 Session 348 — Claude diagnoses, agent executes; observation required for runtime symptoms | Active |
| M6 | WORKFLOW OUTPUT | Yes (workflow-output hook) | 2026-04-15 | Active |
| M7 | PACING LOCK | Yes (pacing hook) | 2026-04-15 | Active |
| M8 | PROJECT KNOWLEDGE REFRESH | No | 2026-04-15 | Active |
| M9 | MODEL DOWNSHIFT | No | 2026-04-15 | Active |
| M10 | TOKEN DISCIPLINE | No | 2026-04-15 | Active |
| M11 | MEMORY EDITS SCOPE | No | 2026-04-15 | Active |
| M12 | HANDOFF | No | 2026-04-15 | Active |
| M13 | CURSOR HEADER FORMAT | No | 2026-04-15 | Active |
| M14 | PHASE GATE ENFORCEMENT | Yes (phase-gate hook) | 2026-04-15 | Active |
| M15 | SCHEMA SOURCE OF TRUTH | No | 2026-04-22 | Active |
| M16 | CANONICAL DECISIONS | Yes (canonical-decisions hook) | 2026-04-22 | Active |
| M17 | THIRD-PARTY UI DRIFT | No | 2026-04-15 | Active |
| M18 | TESTING GATE FORMAT | No | 2026-04-15 | Active |
| M19 | MOBILE VERIFICATION | No | 2026-04-15 | Active |
| M20 | PLAIN ENGLISH PROSE | Yes (plain-English hook) | 2026-04-27 | Active |
| M21 | COUNTER + HANDOFF EXEC | Yes (counter hook, handoff-read hook — per-stage scope) | Rewritten 2026-05-14 Session 194 (per-stage scope; complete PK read of skill required before each stage; outcome-based) | Active |
| M22 | ONE-SCRIPT CHAIN | Yes (one-script hook) | 2026-04-27 | Active |
| M23 | SPEC ADHERENCE | Yes (spec-adherence hook) | 2026-05-03 | Active |
| M24 | HIDDEN FILES | No | 2026 (Session 110) | Active |
| M25 | CLAUDE CODE HEADER | Yes (Claude Code header hook) | 2026 (Session 122) | Active |
| M26 | BRIEF APPEND DISCIPLINE | Yes (append-discipline hook) | 2026-05-04 | Active |
| M33 | RESPONSE BREVITY | Yes (brevity hook) | 2026-05-05 (renumbered from M27 2026-06-03) | Active |
| M34 | READ-BEFORE-AUTHOR | Yes (read-before-author hook) | Filed 2026-07-15 Session 346; amended 2026-07-16 Session 348; Session 350: COMPANION sentence added routing identifier existence to IDENTIFIER SOURCE GATE (U27); M34 scope unchanged — gates file-content authoring only | Active |
| M29 | USERPREFS EDIT OUTPUT | Yes (userprefs-edit hook) | 2026-05-13 | Active |
| M31 | CONDUCT LESSON BINDING | Yes (conduct-lesson hook) | 2026-05-18 | Active |

See ~/Projects/ai-rules/zelbi-rules.md for full rule details.

---

## Watch Window — Step 9.5 Schema Entries

Rules currently in Phase 3 field-validation watch window (0–5 sessions remaining). Full Step 9.5 schema recorded here. `fix_held` flips to "Yes" only after 5 sessions with zero missed firings.

### WW-M3 — NEVER INVENT / NEVER GUESS (zelbi M3 / universal U4)

| Field | Value |
|-------|-------|
| rule_id | M3 (zelbi) / U4 (universal) |
| name | NEVER INVENT / NEVER GUESS |
| tier | 1 |
| location_memory | slot 3 |
| location_pref | PRIME DIRECTIVE section (top of User Preferences, above Tier 1) |
| synced_hash | memory:5471b02a / pref:748a3855 (cap-divergence expected — memory compressed to ≤500 chars; trigger surface preserved verbatim in both) |
| hook_shape | Shape 1 |
| hook_text | HOOKS: never-invent/guess/status — STOP, cite or mark UNKNOWN. (memory compressed form); full form: HOOK: Before writing any fact-asserting sentence, str_replace new_str, prompt-block body, or proposed file content — check (a) source tag (i)/(ii)/(iii) or [UNKNOWN] marker present, (b) no forbidden phrase present, (c) any status word followed by backtick-quoted source, (d) no bare covered identifier. Any check fails — STOP: "Triggered never-invent hook. Cite source, quote verbatim, or mark UNKNOWN." |
| rule_surface_rows | fact-asserting sentence \| identifier (table/column/endpoint/Stripe event/PostGIS fn/Expo API/file path) \| status word \| forbidden phrase |
| hook_surface_rows | (a) source tag (i)/(ii)/(iii) or [UNKNOWN] present \| (b) no forbidden phrase \| (c) status word + backtick-quoted source \| (d) no bare covered identifier |
| known_blind_spots | identifier types outside 7 enumerated classes (env var names, npm package names, git branch names); identifiers buried in multi-paragraph drafts may be missed same-session — Phase 3 watch catches field misses |
| last_modified | 2026-05-13 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M3-001 |

### WW-M29 — USERPREFS EDIT OUTPUT (zelbi M29, memory-only)

| Field | Value |
|-------|-------|
| rule_id | M29 (zelbi) |
| name | USERPREFS EDIT OUTPUT |
| tier | 3 |
| location_memory | slot 30 |
| location_pref | none (memory-only rule) |
| synced_hash | none (single-location — no sync required) |
| hook_shape | Shape 3 (omission) |
| hook_text | HOOK: When writing a response that touches userPreferences content — verify a single complete-document fenced block is present BEFORE sending. If a pre-existing anomaly is preserved, verify ⚠️ callout naming it is present. If either element missing — STOP: "Triggered userprefs-edit hook. Output full document as single fenced block." |
| rule_surface_rows | any response touching userPreferences content \| preserved pre-existing anomaly |
| hook_surface_rows | single complete-document fenced block present \| ⚠️ callout present if anomaly preserved |
| known_blind_spots | very-large userPreferences exceeding single-message budget (future boundary case, undefined behavior) |
| last_modified | 2026-05-13 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M29-001 |

### WW-M31 — CONDUCT LESSON BINDING (zelbi M31 / universal U23)

| Field | Value |
|-------|-------|
| rule_id | M31 (zelbi) / U23 (universal) |
| name | CONDUCT LESSON BINDING |
| tier | 1 |
| location_memory | none (memory at 30/30 cap at filing time; userPreferences-only until a memory slot is freed in a future audit) |
| location_pref | TIER 1, between HYPOTHESIS-LOCK and M27 WORKTREE DRIFT GUARD |
| synced_hash | none (single-location — no sync required at this time) |
| hook_shape | Shape 2 (category) |
| hook_text | HOOK (Shape 2 — category): If outgoing text matches a bullet's named failure pattern — STOP: "Triggered conduct-lesson hook. Session N-1 named this exact pattern, do not repeat." Signals: (1) text matches past-tense failure sentence of any bullet; (2) text falsifies imperative correction of any bullet; (3) text cites a rule named in a bullet without applying it. Empty section = no fire. |
| rule_surface_rows | Block 1 CONDUCT LESSONS bullets (past-tense failure sentence) \| Block 1 CONDUCT LESSONS bullets (imperative correction sentence) \| rule citation inside a bullet \| empty section ("None — session executed cleanly") |
| hook_surface_rows | Signal 1: text matches past-tense failure sentence of any bullet \| Signal 2: text would falsify the imperative correction of any bullet \| Signal 3: text cites a rule named in a bullet without applying it \| empty-section guard: hook does not fire if section is empty |
| known_blind_spots | G1: abstract bullets ("be more careful") cannot be scanned — mitigated by handoff-protocol.md line 138-141 requiring concrete past-tense + imperative form. G2: semantic-similarity violations (paraphrased version of named failure with different surface wording) — partial in-model catch only; Python hook deferred. G3: multi-message latent violations (failure spans messages 2-7) — hook scans per-message; session-level state requires the deferred Python hook. |
| last_modified | 2026-05-18 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M31-001 |

### WW-U5 — TOOL ROUTING (zelbi M-routing / universal U5, Shape 3 wrong-tool omission)

| Field | Value |
|-------|-------|
| rule_id | U5 (universal) / M-routing (zelbi) |
| name | TOOL ROUTING |
| tier | 2 |
| location_memory | None — no memory slot; hook lives in User Preferences TIER 2 (zelbi-rules.md) only (grep of zelbi memory for wrong-tool / Mac Terminal (Verify) returned no match, Session 245) |
| location_pref | TIER 2, TOOL ROUTING section (Shape 3 wrong-tool-omission hook appended Session 243) |
| synced_hash | none (single-location — no memory mirror, no sync required) |
| hook_shape | Shape 3 (omission) |
| hook_text | HOOK (Shape 3 — wrong-tool omission, additive to the tag-presence hook): Before writing any command block, classify the command — if NO line writes a file, mutates git or database state, deploys, or has an agent act on its own output (block is purely ls/cat/grep/find/sed-print/git status\|diff\|log/pwd/which/head/tail/wc/alembic current/read-only pytest), the tool tag MUST be Mac Terminal (Verify) — not Claude Code. Claude Code tag above an all-read-only block — STOP: "Triggered wrong-tool hook. Read-only block routes to Mac Terminal, not Claude Code." |
| rule_surface_rows | command block with a tool tag \| all-read-only command block \| state-mutating command block |
| hook_surface_rows | every line is read-only → tag must be Mac Terminal (Verify) \| any line mutates state → Claude Code permitted |
| known_blind_spots | documented inverse error (state-mutating block mis-tagged Mac Terminal) is NOT caught here — self-surfaces because an agent cannot perform file edits from a terminal tag |
| last_modified | 2026-05-25 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-U5-001 |

---

### WW-U24 — BROWSER-AUTOMATION ROUTING (universal, no hook at filing)

| Field | Value |
|-------|-------|
| rule_id | U24 (universal) |
| name | BROWSER-AUTOMATION ROUTING |
| tier | 2 |
| location_memory | None — memory at 30-edit cap (`Maximum number of memories reached`); no memory mirror filed |
| location_pref | TIER 2, BROWSER-AUTOMATION ROUTING section (immediately after TOOL ROUTING) |
| synced_hash | none (single-location — no memory mirror, no sync required) |
| hook_shape | documentation-only (no hook at filing) |
| hook_text | none — revisit after a test run |
| rule_surface_rows | web/dashboard work an agent can self-drive (Railway, Stripe, Supabase web UIs) \| native mobile app (out of scope — web browsers only) |
| hook_surface_rows | none (no hook at filing) |
| known_blind_spots | no enforcement hook — in-model recognition only until a test run justifies one |
| last_modified | 2026-05-31 |
| watch_window_sessions_remaining | 0 (no hook to watch) |
| fix_held | N/A (no hook) |
| breakage_log_refs | BL-U24-001 |

---

### WW-M1 — CLAUDE CODE ESCALATION (zelbi M1, memory-only)

| Field | Value |
|-------|-------|
| rule_id | M1 (zelbi) |
| name | CLAUDE CODE ESCALATION |
| tier | 1 |
| location_memory | slot 1 |
| location_pref | none (memory-only, project-scoped) |
| synced_hash | none (single-location) |
| hook_shape | Shape 2 (category) |
| hook_text | HOOK (Shape 2): writing a chain of separate chat-side edits for work spanning 3+ files instead of one complete Claude Code prompt — STOP: "Triggered escalation hook. One prompt, complete change." |
| rule_surface_rows | chain of partial edits across 3+ files \| agent prompt that delegates diagnosis \| reads on one symptom \| hypothesis-streaking without a read |
| hook_surface_rows | chain of partial edits across 3+ files → fires \| delegated diagnosis → covered by M5 delegation hook \| reads on one symptom → NO HOOK BY DESIGN \| hypothesis-streaking → covered by M30 |
| known_blind_spots | "crosses layers" is a judgment call at the margin; nothing catches a complete prompt that is complete but wrong |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M5-001 |

### WW-M5 — ROUTING GATE (zelbi M5, memory-only)

| Field | Value |
|-------|-------|
| rule_id | M5 (zelbi) |
| name | ROUTING GATE |
| tier | 1 |
| location_memory | slot 5 |
| location_pref | none (memory-only, project-scoped) |
| synced_hash | none (single-location) |
| hook_shape | Shape 2 (category), two hooks |
| hook_text | HOOK 1 (Shape 2): naming a cause or authoring an edit for a runtime-behavior symptom with no device observation or probe output in THIS chat since the last edit — STOP: "Triggered grounding hook. Get an observation first." HOOK 2 (Shape 2): writing an agent prompt lacking exact old/new text, or containing "diagnose", "investigate", "figure out", "decide", or "read the file and fix" — STOP: "Triggered delegation hook. Author the exact change." |
| rule_surface_rows | runtime cause named without observation \| runtime edit authored without observation \| second source-only fix after a failure \| agent prompt that delegates diagnosis \| agent prompt missing exact old/new text \| file read staleness after an edit \| agent silently ignoring the fence |
| hook_surface_rows | grounding hook fires on rows 1-3 \| delegation hook fires on rows 4-5 \| row 6 covered by M34 \| row 7 BLIND SPOT |
| known_blind_spots | where a screenshot stops being enough and measured numbers are required; a logic error that only manifests on runtime data; nothing verifies the agent honored the fence — only Nick's device check catches it |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M5-001 |

### WW-M34 — READ-BEFORE-AUTHOR (zelbi M34 / universal, dual-location)

| Field | Value |
|-------|-------|
| rule_id | M34 (zelbi) |
| name | READ-BEFORE-AUTHOR |
| tier | 1 |
| location_memory | slot 13 |
| location_pref | TIER 1, after HYPOTHESIS-LOCK and immediately before U25 VISUAL-FIX FALSIFICATION |
| synced_hash | VERIFIED ALIGNED 2026-07-16 Session 348 — Pass 4 run by chat-Claude, which holds both texts in context (memory slot 13 via the memory tool; User Preferences via the account-level preferences block). Claude Code cannot read either and did not perform this check — it applied this line as dictated attestation. Result: body clause, agent-substitution clause, Shape 3 hook trigger, STOP string, and precedence clause all IDENTICAL across both locations. CORRECTION: this field previously read PENDING with the check "deferred to Session 349" and the preferences side "operator-attested only" — that was FALSE. Both texts were readable in-session throughout; the deferral was fabricated. Logged as BL-M34-002. |
| hook_shape | Shape 3 (omission) |
| hook_text | HOOK (Shape 3): When writing a Cursor/Claude Code prompt or prose containing a line number, quoted current file content, a style value, or a cause claim for a repo file — verify a post-last-edit read exists in THIS chat. If missing — STOP: "Triggered read-before-author hook. Emit the Mac Terminal dump command instead." |
| rule_surface_rows | edit prompt with a line number \| prose quoting current file content \| style value authored for a repo file \| named cause claim for a repo file \| whether a runtime cause is grounded at all \| future divergence between the two locations |
| hook_surface_rows | rows 1-4 fire \| row 5 routed to M5 by design \| row 6 BLIND SPOT — audit Pass 4 only |
| known_blind_spots | nothing detects future drift between memory and preferences except a manual Pass 4 audit — the same structural hole that let two Tier 1 preference rules vanish unnoticed between 2026-05-28 and 2026-07-15 |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M34-001, BL-M5-001, BL-M34-003 |
| companion_note | Session 350: COMPANION sentence added routing identifier existence to IDENTIFIER SOURCE GATE (U27); M34 scope unchanged — gates file-content authoring only. |

---

### WW-U25 — VISUAL-FIX FALSIFICATION (universal, preferences-only)

| Field | Value |
|-------|-------|
| rule_id | U25 (universal) |
| name | VISUAL-FIX FALSIFICATION |
| tier | 1 |
| location_memory | none — memory at 30/30 cap (verified Session 348); preferences-only until a slot frees, same posture as U23 and U24 |
| location_pref | TIER 1, directly after M34 READ-BEFORE-AUTHOR |
| synced_hash | none (single-location) |
| hook_shape | Shape 2 (category) — shape not declared in the rule text; the text predates the shape convention and was restored verbatim per Nick's approval. Classified here. |
| hook_text | HOOK: if proposing a second styling edit in the same file after the first failed, without an intervening scope-widening read or isolation test — STOP: "Triggered visual-falsification hook. Widen scope or isolate before the next fix." |
| rule_surface_rows | second styling edit in the same file after a failure \| third and beyond in the same file \| widening read of the parent layer \| isolation test \| failed fix in a DIFFERENT file \| adequacy of the observation itself |
| hook_surface_rows | rows 1-2 fire \| rows 3-4 correctly do not fire (intended path) \| row 5 BLIND SPOT — hook keys on same-file, a location hypothesis can span files \| row 6 routed to M5 by design |
| known_blind_spots | same-file keying misses a cross-file location hypothesis; "widen scope" is a judgment call at the margin; no chat-layer Python hook exists — in-model recognition only, same acknowledged ceiling as U23 |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-U25-001 |

---

### WW-U26 — READ HONESTY (universal, preferences-only)

| Field | Value |
|-------|-------|
| rule_id | U26 (universal) |
| name | READ HONESTY |
| tier | 1 |
| location_memory | none — memory at 30/30 cap, verified Session 349 by chat-Claude's own memory_user_edits view (not carried from the prior session's attestation); preferences-only until a slot frees, same posture as U23, U24, U25 |
| location_pref | TIER 1, first rule after the PRIME DIRECTIVE, immediately before PACING LOCK |
| synced_hash | none (single-location) |
| hook_shape | Shape 3 (omission), primary. Plus a Shape 2 (category) operator-source hook added same session after a live fire. |
| hook_text | HOOK (Shape 3 — omission): Before sending any sentence that (a) reports a read, check, comparison, diff, or verification as having been performed, or (b) asserts that a read is impossible or that content does not reach Claude — scan THIS transcript for the corresponding tool call, command output, or pasted artifact. If no attempt exists, or the attempt returned empty — STOP: "Triggered read-honesty hook. Attempt it, or report the absence." |
| hook_text_2 | HOOK (Shape 2): asking Nick to re-supply, re-paste, or re-confirm something he has already stated he did — STOP: "Triggered operator-source hook. His word closed it." |
| rule_surface_rows | claims a read/check/diff/comparison happened \| claims a read is impossible or does not reach Claude \| describes contents of an input that arrived blank \| correct conclusion with borrowed provenance \| asks Nick to re-prove an action he already stated \| misparse of REAL discontinuous output |
| hook_surface_rows | rows 1-4 fire on the Shape 3 hook \| row 5 fires on the Shape 2 hook \| row 6 BLIND SPOT — an attempt exists, so the omission hook passes |
| known_blind_spots | misparsing real multi-range output as continuous text (BL-M34-002 fabrication 6) — an attempt exists so the omission hook passes; mitigated by requesting one contiguous range per read and routed to U4/M3, which requires a quoted line behind any finding. No chat-layer Python hook exists — in-model recognition only, same acknowledged ceiling as U23/U25. |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M34-002, BL-U7-001 |

---

### WW-U27 — IDENTIFIER SOURCE GATE (universal, preferences-only)

| Field | Value |
|-------|-------|
| rule_id | U27 (universal) |
| name | IDENTIFIER SOURCE GATE |
| tier | 1 |
| location_memory | none — memory at 30/30 cap |
| location_pref | TIER 1, directly after M34 |
| synced_hash | none (single-location) |
| hook_shape | Shape 3 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | BL-M34-003 |

---

### Project: db-auto-detailing

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| M1 | PACING LOCK | Yes (pacing hook) | 2026-04-18 | Active |
| M2 | NEVER INVENT | Yes (never-invent hook) | 2026-04-18 | Active |
| M3 | WORKFLOW OUTPUT | Yes (workflow-output hook) | 2026-04-18 | Active |
| M4 | VERIFICATION GATE | Yes (verification hook) | 2026-04-18 | Active |
| M5 | CLAUDE CODE ESCALATION | Yes (escalation hook) | 2026-04-18 | Active |
| M6 | BEFORE EVERY CURSOR PROMPT | Yes (pre-prompt hook) | 2026-04-18 | Active |
| M7 | TOOL ROUTING | No | 2026-04-18 | Active |
| M8 | FILE ACCESS HONESTY | No | 2026-04-18 | Active |
| M9 | MODEL DOWNSHIFT | No | 2026-04-18 | Active |
| M10 | TOKEN DISCIPLINE | No | 2026-04-18 | Active |
| M11 | MEMORY EDITS SCOPE | No | 2026-04-18 | Active |
| M12 | HANDOFF (points at db-auto-detailing-handoff-protocol.md) | No | 2026-05-11 | Active (replaced 2026-05-11) |
| M13 | CURSOR HEADER FORMAT | No | 2026-04-18 | Active |
| M14 | PROJECT KNOWLEDGE REFRESH | No | 2026-04-18 | Active |
| M15 | BUG ROUTING | Yes (bug-routing hook) | 2026-04-18 | Active |
| M16 | PHASE GATE ENFORCEMENT | Yes (phase-gate hook) | 2026-04-18 | Active |
| M17 | SCHEMA SOURCE OF TRUTH | No | 2026-04-18 | Active |
| M18 | CANONICAL DECISIONS TABLE | Yes (canonical-decisions hook) | 2026-04-18 | Active |
| M19 | THIRD-PARTY UI DRIFT | Yes (UI-drift hook) | 2026-04-18 | Active |
| M20 | TESTING GATE FORMAT | No | 2026-04-18 | Active |
| M21 | ROUTING GATE | Yes (routing hook) | 2026-04-18 | Active |
| M22 | MEASUREMENT ROUTING (Playwright preferred, Hoverify fallback) | Yes (measurement-routing hook) | 2026-05-11 | Active (replaced 2026-05-11) |
| M23 | DOM/CONSOLE QUERIES | Yes (console-query hook) | 2026-04-18 | Active |
| M24 | INSTRUCTION FORMAT | Yes (format hook) | 2026-04-18 | Active |
| M25 | HANDOFF CONSUMPTION | No | 2026-04-18 | Active |

See ~/Projects/ai-rules/db-auto-detailing-rules.md for full rule details.

## U20 — RESPONSE BREVITY
**Tier:** 1
**Scope:** Universal (all projects)
**Hook:** Yes — "Triggered brevity hook. Cut to the deliverable."
**Revision:** 2026-05-05
**Mirrored:** Zelbi M33
**Text:** Maximum three sentences of prose before the first code block, prompt block, table, or list. No preambles, no recaps, no closers. After the deliverable, one sentence of next-step. Verification and never-invent disclosures use one sentence plus the command block. Exception: when Nick explicitly asks for an explanation, a study, a comparison, or "give me everything."

## U2 — PACING LOCK (REVISED 2026-05-05)
**Tier:** 1
**Scope:** Universal (all projects)
**Hook:** Yes — "Triggered pacing hook." Trigger enumerates four failure modes: (a) second instruction, (b) tool call, (c) clarifying question, (d) scope ask after a deliverable awaiting confirmation.
**Revision:** 2026-05-05 (hook trigger sharpened — added clarifying question and scope ask as explicit failure modes)
**Mirrored:** Zelbi M7
**Text:** After delivering an instruction or prompt block, STOP and wait. Never stack instructions unless Nick says "give me everything." Override: "skip it" or "move on." Hook trigger now lists four enumerated failure modes instead of "tool call or second instruction" only.
**Change history:** Original hook said "tool call or second instruction" — let clarifying questions and scope asks rationalize through. Sharpened 2026-05-05 to enumerate (a)/(b)/(c)/(d) per blueprint Step 8 "change strategy after repeat failure."

## U21 — DECISION OWNERSHIP
**Tier:** 1
**Scope:** Universal (all projects)
**Hook:** Yes — "Triggered decision-ownership hook. Pick one and execute."
**Revision:** 2026-05-05
**Mirrored:** None (universal only)
**Text:** Claude makes implementation decisions, Nick makes product decisions. HOW questions (library, approach, command flag, file order, whether to verify) — Claude picks and executes. WHAT questions (feature, product behavior, user-facing outcome) — ask Nick. Never present 2+ implementation options for Nick to choose between. Never ask "should I X or Y" when X is the clearly correct technical choice. If genuinely ambiguous between two technical paths, pick one, state the alternative in one line, and execute.
**Change history:** Original entry. Filed per RULE-FIX-BLUEPRINT-v3.md Steps 1-9 to address recurring decision-overload failure mode (Cause A — no rule existed).

## U22 — PROMPT BLOCK FORMAT
**Tier:** 3
**Scope:** Universal (all projects)
**Hook:** Yes — "Triggered prompt-format hook. Split into two blocks." Additive hook: "Triggered auto-mode-tag hook." (Shape 3 omission, Claude Code header only)
**Revision:** 2026-05-16
**Auto-mode safe payload criteria (Claude Code only):** (a) read-only inspection; (b) single-file edit to non-config application code; (c) lint/typecheck/test; (d) dependency install from existing manifest (no new deps); (e) documentation/markdown edits.
**Auto-mode disqualifiers (omit line if ANY apply):** migrations/schema changes; destructive git; env var changes, secret reads, .env edits; deploys; multi-file edits crossing layers; .claude/ changes; rm/mv/chmod outside repo; new dependency additions.
**Auto-mode change note 2026-05-16:** Added "Auto-mode: safe" optional sixth header line for Claude Code prompts when payload qualifies per criteria above; additive Shape 3 omission hook fires when tag is missing on qualifying payload or present on disqualifying payload.
**Mirrored:** None (universal only)
**Supersedes:** U10 CURSOR PROMPT FORMAT, U18 CLAUDE CODE PROMPT FORMAT
**Text:** Every prompt or command for Nick to execute follows the same two-block pattern: header in one fenced block, command(s) in a separate fenced block. Never combine. Header stays copy-skippable; command stays copy-pastable as-is. Covers Cursor prompts, Claude Code prompts, and Mac Terminal commands. Cursor prompts include Mode/Model/Reason header with model repeated inside the command block. Claude Code prompts include the five-line Tool/Mode/Model/Thinking/Reason header with the model repeated inside the command block. Mac Terminal commands include Tool/Mode/Reason header with no tag inside.
**Change history:** Original entry. Filed per RULE-FIX-BLUEPRINT-v3.md Steps 1-9 to address recurring header/command combination failure (Cause A — no Mac Terminal format rule existed; existing Cursor and Claude Code rules folded into unified rule).

## U23 — CONDUCT LESSON BINDING
**Tier:** 1
**Scope:** Universal (all projects)
**Hook:** Yes — "Triggered conduct-lesson hook. Session N-1 named this exact pattern, do not repeat."
**Revision:** 2026-05-18 (filed Session 222)
**Mirrored:** Zelbi M31
**Text:** When a Block 1 handoff arrives with a CONDUCT LESSONS section containing one or more bullets, those bullets are binding constraints for the entire session, not history. Before every outgoing message, scan the text against every bullet. Three category signals fire the hook: text matches the past-tense failure sentence of any bullet; text would falsify the imperative correction of any bullet; text cites a rule named in a bullet without applying it. Empty section ("None — session executed cleanly") = hook does not fire.
**Change history:** Original entry. Filed per RULE-FIX-BLUEPRINT-v3.md Steps 1-9 after a verified 30+-session breakage pattern spanning April 22 to May 18 (Sessions 28 through 221). Root cause D at the rule layer plus architectural hook-layer gap. In-model recognition only at this time; Python hook (conduct-lesson-hook.py at ~/.claude/hooks/) deferred to a dedicated session as Part 2 of the fix.

---

## Hook Layer (~/.claude/hooks/)

**What it is:** Claude Code Stop and PreToolUse event hooks that enforce Nick's chat rules at the agent layer. Hooks read JSON from stdin, scan the assistant's outgoing message (or pending tool input), and exit 2 with a stderr message on violation. Stop-event hooks fire after every assistant turn; PreToolUse hooks fire before every tool call.

**Currently registered hooks (`~/.claude/settings.json`, as of 2026-05-17):**

PreToolUse, in firing order:
  1. `/Users/nickbroyzer/Projects/clawdeck-vsd/hooks/deck-hook.sh pending`
  2. `python3 "/Users/nickbroyzer/.claude/hooks/decision-ownership-hook.py"`

Stop, in firing order:
  1. `/Users/nickbroyzer/Projects/clawdeck-vsd/hooks/deck-hook.sh idle`
  2. `python3 "/Users/nickbroyzer/.claude/hooks/brevity-hook.py"`
  3. `python3 "/Users/nickbroyzer/.claude/hooks/plain-english-hook.py"`
  4. `python3 "/Users/nickbroyzer/.claude/hooks/pacing-hook.py"`
  5. `python3 "/Users/nickbroyzer/.claude/hooks/prompt-format-hook.py"`

UserPromptSubmit, PostToolUse, Notification, SessionStart: see `settings.json` — non-rule-enforcement hooks (deck-hook UI signaling, GSD update check, session-start banner).

**Rule-enforcement hook → Universal Rule mapping:**
- `brevity-hook.py` → U20 RESPONSE BREVITY
- `plain-english-hook.py` → U19 PLAIN ENGLISH PROSE (Claude Code Stop hook only — does NOT run in claude.ai chat; chat-side prose enforcement DEFERRED, same status as conduct-lesson-hook.py)
- `pacing-hook.py` → U2 PACING LOCK
- `prompt-format-hook.py` → U22 PROMPT BLOCK FORMAT (covers two-block split and auto-mode-tag omission check; auto-mode-tag is chat-side enforcement only — no .py hook yet)
- `decision-ownership-hook.py` → U21 DECISION OWNERSHIP (PreToolUse, narrowly tool-name-gated to user-question tools)
- `conduct-lesson-hook.py` → U23 CONDUCT LESSON BINDING (DEFERRED — not yet implemented; rule enforced via in-model recognition only at this time; Python hook scoped for a dedicated future session)

**Backup convention:** `~/.claude/settings.json.bakN`, monotonic. Currently at bak7 (next backup = bak8). Every rule-fix session that edits `settings.json` increments. Backups preserved indefinitely.

**Architectural rule learned 2026-05-05:** Chat-side rules (rules about what the assistant says to Nick) belong on the Stop event, NOT PreToolUse. PreToolUse fires before every internal tool call and conflates approved task execution with stacked instructions to Nick. The original `pacing-hook.py` was registered on PreToolUse with a per-session counter and blocked tool calls 2..N inside any user-approved multi-step task. Generalized rule: if a hook enforces a rule about chat output, it MUST fire on Stop and scan `last_assistant_message`. PreToolUse is appropriate only for tool-input rules (e.g., `decision-ownership-hook` gating user-question tool inputs).

**Audit flag:** `decision-ownership-hook.py` is currently the only rule-enforcement hook on PreToolUse. It is narrowly scoped — gates on `tool_name` being one of the user-question tools (`AskUserQuestion`, `ask_user_input_v0`, `ask_user_question`) and silent-passes for any other tool. This means it does NOT over-fire on ordinary tool calls, but it remains the only PreToolUse rule hook in the layer and is worth a closer review for completeness and false-positive risk.




---

## Project-Instruction Rules (CLAUDE.md)

A third location class. Neither User Preferences nor memory edits. These rules
live in a repo's auto-loaded project-instructions file and are the ONLY rule
surface Claude Code reads — it cannot read User Preferences and cannot read
memory. Numbered PI-series, deliberately outside the M-series: M-numbers map
one-to-one onto memory slots and the Step 9.5 watch-window rows depend on that
mapping.

Enforcement ceiling: in-model recognition only. Prose in an auto-loaded
markdown file is NOT a hook. Real hooks are Python files at ~/.claude/hooks/
registered on Stop/PreToolUse in ~/.claude/settings.json. Any PI rule claiming
hook-strength is making a category error.

### Project: zelbi

| # | Rule Name | Hook | Added | Status |
|---|-----------|------|-------|--------|
| PI1 | READ THE LESSONS FILES FIRST | No — see notes | 2026-07-16 Session 351, commit a9cd5a7 | Active |
| PI2 | MOBILE UI — VERIFY BEFORE REPORTING | No — see notes | 2026-07-16 Session 351, commit a9cd5a7 | Active |

#### PI1 — READ THE LESSONS FILES FIRST
**Location:** /Users/nickbroyzer/Projects/zelbi.ai/CLAUDE.md
**Text:** mobile/lessons.md and backend/lessons.md are the project's record of
toolchain corrections. Before any build, run, install, or verification step,
grep the matching lessons file for the tool. Before proposing a fix to a
toolchain error, grep it for the error. Follow a covering line or say why it no
longer applies — do not re-derive it. Lessons are records, not truth: every
line is dated, some are stale, check against the tree before relying on one,
and report any line reality has overtaken.
**Hook:** None. Deliberate. BREAKAGE-LOG.md grep for simulator/simctl/
screenshot/xcodebuild returned zero failure entries (Session 351). Blueprint
anti-pattern 4: hooks are for repeat failures. Inventing a hook history that
does not exist is the BL-M34-002 fabrication class.
**Root cause:** B — rule has a gap. NOT A as originally filed. M19 MOBILE
VERIFICATION already covered the area and contains the word "simulator." The
originating grep covered CLAUDE.md and .claude/ — surfaces that structurally
cannot hold a memory rule. A null result there proves the surface was searched,
not that no rule exists. This is the second such re-derivation on record; U26
carries the identical note.
**Evidence (Session 351):** mobile/lessons.md lines 213, 215, 216, 217 dated
2026-07-10 and 2026-07-11 already held both central toolchain facts a Session
350/351 proposal declared "written nowhere." Capture layer works; retrieval
layer did not exist. CLAUDE.md is the only file Claude Code auto-loads, so it
is the only available lever.
**Reinforces:** M4, M19 — supplies neither, points at the record instead.

#### PI2 — MOBILE UI — VERIFY BEFORE REPORTING
**Location:** /Users/nickbroyzer/Projects/zelbi.ai/CLAUDE.md
**Text:** After any mobile UI change, before reporting: capture the simulator
screen and open the image; report only what is visible. If capture or open
fails, say exactly that and stop. A screenshot stops blind reporting — it is
NOT verification; Nick's own device check is still required and is not
satisfied by an agent image. Hand over the image, not a summary of it. Never
claim a still verified animation, keyboard, gesture, scroll, or a multi-screen
flow. Cannot tap — hand tap-flows to Nick. Build procedure lives in
mobile/lessons.md, not here. A prompt's fence wins over this section.
**Hook:** None — same evidence and reasoning as PI1.
**Delivers:** agent truthfulness. Does NOT deliver verification-load relief.
M5's admissible-observation list does not include an agent screenshot; M19
requires Nick's visual confirm. Hand-verification load after this rule is
unchanged. The originating problem statement ("every mobile verification falls
to Nick by hand") described a capability desire, not the failure.
**Known conflict, resolved:** an agent screenshot is evidence TO Claude and is
NEVER M19 satisfaction (precedence: more-specific beats more-general). M5 wins
unchanged — an agent image never grounds a runtime cause claim.
**Known blind spots:** agent screenshots the wrong screen and reports honestly
(uncloseable — needs taps, which do not exist); agent describes the image
instead of handing it over; nothing verifies a fence was honored except Nick
catching it on device.

### Watch Window — PI1 / PI2

| Field | Value |
|-------|-------|
| rule_id | PI1, PI2 (zelbi, project-instructions class) |
| name | READ THE LESSONS FILES FIRST / MOBILE UI — VERIFY BEFORE REPORTING |
| tier | none — project-scoped rules are not tiered in this registry (Session 351 finding: every project table carries number/name/hook/added/status, no tier column; Pass 7 is not applicable to project rules) |
| location_memory | none — memory at 30/30 cap (verified Session 351 via memory_user_edits view) |
| location_pref | none — Claude Code cannot read User Preferences |
| location_claude_md | /Users/nickbroyzer/Projects/zelbi.ai/CLAUDE.md, appended a9cd5a7 |
| synced_hash | none (single-location) |
| hook_shape | documentation-only — no hook, no breakage history |
| hook_text | none |
| rule_surface_rows | PI1: build/run/install step without a lessons grep \| toolchain-error fix proposed without a lessons grep \| stale lesson followed without a tree check. PI2: reports complete with no capture \| captured but never opened \| still-frame claim about motion/multi-screen \| describes image instead of handing it over \| captured wrong screen |
| hook_surface_rows | none — in-model recognition only |
| known_blind_spots | ALL rule-surface rows are blind. No enforcement exists. The strong surface (a Stop hook scanning the transcript for a capture-then-open before a done-claim) is available, wired, and unused — PI2's trigger is one of the few in this system that is a transcript fact rather than a judgment, and is therefore mechanically checkable. Deferred, not attempted. |
| last_modified | 2026-07-16 |
| watch_window_sessions_remaining | 5 |
| fix_held | In Watch |
| breakage_log_refs | none — capability gap, zero prior failures |

### FLAGGED, NOT FIXED — Session 351 findings, each a separate Step 1

- **M19 + M4 mandate a tool that cannot run the app.** Both say Expo Go.
  mobile/package.json carries @shopify/react-native-skia 2.2.12,
  @react-native-masked-view/masked-view 0.3.2, expo-glass-effect ~0.1.10.
  D146/D147 (LOCKED Session 289): "EAS dev build required — Expo Go cannot run
  it." Every device walk since Session 180 has run on a dev build. The premise
  died ~126 sessions ago.
- **D76 is locked on a half-dead rationale.** "@callstack/liquid-glass rejected
  for M19 incompatibility" — the custom-dev-client blocker is void (the project
  now requires one). The New Architecture blocker was never evaluated on its own
  merits because the dev-client blocker was doing the work. M16 requires this be
  flagged. Not a recommendation to adopt.
- **U7 HOVERIFY GATE restored into a project that retired it.** Session 349
  restored U7 to TIER 2 as absent-with-no-record. This registry, zelbi-rules.md
  line 252: "HOVERIFY GATE — Web browser CSS inspection. React Native doesn't
  render in browser. Replaced by M19." M19's own note says the same. The audit
  checked presence, never applicability.
- **conduct_lesson_parser.py exists and is not wired.** ~/.claude/hooks/
  conduct_lesson_parser.py + test file, dated 2026-05-18, absent from
  settings.json. Registry calls U23's hook "DEFERRED — not yet implemented."
  Half true: built, never registered.
- **mobile/lessons.md line 218 is false.** The Stripe simulator/device dilemma
  was dissolved by a source patch at fcba61b (Session 350). Line unamended.
  Open: whether that patch survives a clean install.
- **Structural:** nothing in the seven-pass audit asks whether a rule's PREMISE
  is still true, or what product decisions rest on it. The decision log is not
  in this registry. A full audit was run Session 351 and found none of the
  above — they surfaced from reading the decision log, which no pass names.

## FREEZE — 2026-07-17 (Session 352)

Rule system FROZEN by Nick: no new rules, no rewrites, no blueprint runs, no watch-window filings until the one-session rebuild (fact sheet, ten-line card, repo law + preflight, single-store collapse) completes. Failures during the freeze get ONE line in BREAKAGE-LOG.md, nothing more. Grounds: full-log audit 2026-07-17 — 7 breakages in the invention family against an escalate-at-3 threshold never escalated; Pattern Watch never updated since 2026-04-10; chat-side enforcement confirmed nonexistent (BL-U19-001, BL-M31-001); 6 of 8 sessions Jul 15-17 consumed by rule maintenance with zero product code shipped.

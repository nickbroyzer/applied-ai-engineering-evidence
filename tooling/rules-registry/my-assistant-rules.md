# my-assistant-rules.md — Project-Specific Rules for my-assistant

Project: my-assistant (construction-company Flask dashboard)
Repo: ~/Projects/my-assistant/
Claude Project: "<construction company>"
These rules are stored as memory edits in the PC Claude project.
Last audited: 2026-04-11

---

## Active Rules

| Memory # | Rule Name | Hook | Added | Status |
|----------|-----------|------|-------|--------|
| 1 | PC PROJECT REFRESH | No | Pre-audit | Active |
| 2 | FLASK PORT | Yes — "Triggered port-5000 hook." | Pre-audit | Active |
| 3 | CLAUDE CODE ESCALATION | Yes — "Triggered escalation hook." | Pre-audit | Active |
| 4 | DOM/CONSOLE QUERIES | Yes — "Triggered console-query hook." | 2026-04-11 | Active |
| 5 | BEFORE EVERY CURSOR PROMPT | Yes — "Triggered pre-prompt hook." | 2026-04-11 | Active |
| 6 | TOOL ROUTING | No | Pre-audit | Active |
| 7 | WORKFLOW OUTPUT | Yes — "Triggered workflow-output hook." | 2026-04-11 | Active |
| 8 | MODEL DOWNSHIFT | No | Pre-audit | Active |
| 9 | TOKEN DISCIPLINE | No | Pre-audit | Active |
| 10 | NEVER INVENT | Yes — "Triggered never-invent hook." | 2026-04-11 | Active |
| 11 | FILE ACCESS HONESTY | No | Pre-audit | Active |
| 12 | HOVERIFY GATE | Yes — "Triggered Hoverify hook." | 2026-04-11 | Active |
| 13 | VERIFICATION GATE | Yes — "Triggered verification hook." | 2026-04-11 | Active |
| 14 | PACING LOCK | Yes — "Triggered pacing hook." | 2026-04-11 | Active |
| 15 | MEMORY EDITS SCOPE | No | Pre-audit | Active |
| 16 | HANDOFF | No | Pre-audit | Active |
| 17 | CURSOR HEADER FORMAT | No | Pre-audit | Active |
| 18 | BUG ROUTING | Yes — "Triggered bug-routing hook." | 2026-04-11 | Active |

---

## Rule Details

### M1 — PC PROJECT REFRESH
**Text:** After sessions that ship changes, provide a Cursor prompt copying modified files to ~/Desktop/ for Project Knowledge upload. At session start, check if Project Knowledge files might be stale.
**Hook:** No — omission-type failure, not detectable mid-action.

### M2 — FLASK PORT
**Text:** PC Flask port is 5000. HOOK: If writing 5001 or :5001 — STOP: "Triggered port-5000 hook. PC port is 5000."
**Hook:** Yes — "Triggered port-5000 hook."
**Trigger:** Writing 5001 or :5001 anywhere in output.

### M3 — CLAUDE CODE ESCALATION
**Text:** If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt (include: problem, files to read, likely causes, fix, verification). Do not debug incrementally in chat. HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."
**Hook:** Yes — "Triggered escalation hook."
**Trigger:** Asking Nick to cat/grep/curl a second time for the same issue.

### M4 — DOM/CONSOLE QUERIES
**Text:** When needing DOM/element info from the browser, ask Nick to run queries in DevTools Console (e.g. document.querySelectorAll(...).length) rather than asking him to inspect elements visually or read code in the Elements panel. HOOK: If asking Nick to inspect Elements panel or visually examine DOM — STOP: "Triggered console-query hook. Ask for a Console query instead."
**Hook:** Yes — "Triggered console-query hook."
**Trigger:** Asking Nick to inspect Elements panel or visually examine DOM.

### M5 — BEFORE EVERY CURSOR PROMPT
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch CSS? If yes, demand Hoverify measurements FIRST — no exceptions. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. HOOK: If writing a Cursor prompt without checking mode/model/CSS — STOP: "Triggered pre-prompt hook. Run the 3-check gate."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without running the 3-check gate.

### M6 — TOOL ROUTING
**Text:** Before every instruction, state tool + reason in one line. Cursor/Claude Code/Mac Terminal — pick the one that fits. CRITICAL CHECK: Before routing to ANY tool, ask "Should chat be handling this at all?" If the task requires reading or tracing across multiple files, the answer is no — escalate to Claude Code per rule #3.
**Hook:** No — would fire too often on normal messages.

### M7 — WORKFLOW OUTPUT
**Text:** Every implementation request → Cursor prompt block as primary output. Never skip to prose code explanations. HOOK: If explaining a code fix in prose instead of a Cursor prompt block — STOP: "Triggered workflow-output hook. Convert to Cursor prompt."
**Hook:** Yes — "Triggered workflow-output hook."
**Trigger:** Explaining a code fix in prose instead of outputting a Cursor prompt block.

### M8 — MODEL DOWNSHIFT
**Text:** After plan approved, Build defaults to Composer 2. Escalate to Sonnet only if Composer 2 fails. Never Opus for Build.
**Hook:** No — rare failure, not a repeat pattern.

### M9 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't burn Opus tokens on Composer 2 work. Never sacrifice quality to save tokens.
**Hook:** No — judgment call, not detectable mid-action.

### M10 — NEVER INVENT
**Text:** commit hashes, pixel values, field names, API shapes, file contents. If unknown, say so + give the command to verify. HOOK: If stating a pixel value, commit hash, or field name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Stating a pixel value, commit hash, or field name without verification.

### M11 — FILE ACCESS HONESTY
**Text:** In claude.ai, cannot read local files. Say what command to run and where — never guess from training data.
**Hook:** No — rule #3's hook catches the main failure mode (using Nick as slow proxy).

### M12 — HOVERIFY GATE
**Text:** Hoverify for layout/design measurements only. DevTools valid for JS debugging, network, console, element state. Not a DevTools ban — a design-measurement-tool rule. HOOK: If suggesting DevTools for layout/spacing/CSS measurements — STOP: "Triggered Hoverify hook. Use Hoverify for design measurements."
**Hook:** Yes — "Triggered Hoverify hook."
**Trigger:** Suggesting DevTools for layout/spacing/CSS measurements.

### M13 — VERIFICATION GATE
**Text:** Never say "this should fix it." Always provide specific verification method. WARNING: Verifying individual steps of a wrong approach is still failure — escalate to Claude Code per rule #3. HOOK: If writing "this should fix it" or declaring done without verification — STOP: "Triggered verification hook. Provide specific verification."
**Hook:** Yes — "Triggered verification hook."
**Trigger:** Writing "this should fix it" or declaring done without a verification method.

### M14 — PACING LOCK
**Text:** One instruction, then WAIT. If Nick interrupts before confirming, push back: "Let's finish the current step first — [pending item]." Only override: Nick says "skip it" or "move on." NEVER stack instructions. EXCEPTION: debugging goes to Claude Code per rule #3. HOOK: If delivering a second instruction before Nick confirmed the first — STOP: "Triggered pacing hook. Wait for confirmation."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Delivering a second instruction before Nick confirms the first.

### M15 — MEMORY EDITS SCOPE
**Text:** No status records, bug tracking, or feature states in memory. Those go to Obsidian or Project Knowledge.
**Hook:** No — single occurrence, not a repeat pattern.

### M16 — HANDOFF
**Text:** Read the handoff skill before running. Stage 1 (closeout + handoff block) at end of session. Stage 2 (Cursor prompt) generated in NEW session. Never combine stages. Never skip waits.
**Hook:** No — omission-type failure, rare.

### M17 — CURSOR HEADER FORMAT
**Text:** Every Cursor prompt gets a visible header BEFORE the code block — Mode, Model, Reason on separate lines. First line INSIDE the prompt repeats [Model: X | Mode].
**Hook:** No — rule #5's hook catches formatting issues at the gate.

### M18 — BUG ROUTING
**Text:** When a bug is reported — state the symptom, then write a Cursor Plan prompt or Claude Code prompt (per rule #3). No multi-step chat diagnosis. One clarifying question allowed if data only exists in browser/live site. HOOK: If asking a second diagnostic question without a prompt — STOP: "Triggered bug-routing hook. Write the prompt."
**Hook:** Yes — "Triggered bug-routing hook."
**Trigger:** Asking a second diagnostic question without writing a prompt.

---

## Cross-References

- Rules #3, #13, #14, #18 reference rule #3 (Claude Code Escalation) as the escalation path
- Rule #5 gate catches formatting issues that #17 specifies
- Rule #18 defers to #3's threshold for tool choice (Cursor vs Claude Code)

## Audit History

- 2026-04-11: Full audit against User Preferences and RULE-FIX-BLUEPRINT-v3. 2 trims (bloat in #6 and #11), 7 hooks added (#4, #5, #7, #10, #12, #13, #14), 1 rule adopted from aibs-core (#18 BUG ROUTING, adapted). 0 contradictions, 0 conflicts. Rules reduced from 19 to 17, then M18 added = 18 total.

---

## Maintenance

- When adding a new memory edit to my-assistant, add it here AND in RULES-REGISTRY.md
- When removing a memory edit, update status to "Retired" with date
- Keep retired rules for history — don't delete entries

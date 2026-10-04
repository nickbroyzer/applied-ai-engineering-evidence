# Command Center v7 — Project Rules

Project: command-center-v7 (Personal developer dashboard)
Repo: ~/Projects/command-center-v7/
Claude Project: "Command Center"
These rules are stored as memory edits in the CC Claude project.
Last audited: 2026-04-11

---

## Active Rules

| Memory # | Rule Name | Hook | Status |
|----------|-----------|------|--------|
| 1 | TOOL ROUTING | No | Active |
| 2 | WORKFLOW OUTPUT | No | Active |
| 3 | MODEL DOWNSHIFT | No | Active |
| 4 | TOKEN DISCIPLINE | No | Active |
| 5 | NEVER INVENT | Yes — "Triggered never-invent hook." | Active |
| 6 | FILE ACCESS HONESTY | No | Active |
| 7 | HOVERIFY GATE | Yes — "Triggered Hoverify hook." | Active |
| 8 | VERIFICATION GATE | Yes — "Triggered verification hook." | Active |
| 9 | PACING LOCK | Yes — "Triggered pacing hook." | Active |
| 10 | PROJECT KNOWLEDGE REFRESH | No | Active |
| 11 | MEMORY EDITS = BEHAVIORAL RULES ONLY | No | Active |
| 12 | HANDOFF | No | Active |
| 13 | CURSOR HEADER FORMAT | No | Active |
| 14 | CLAUDE CODE ESCALATION | Yes — "Triggered escalation hook." | Active |
| 15 | BEFORE EVERY CURSOR PROMPT | Yes — "Triggered pre-prompt hook." | Active |
| 16 | BUG ROUTING | Yes — "Triggered bug-routing hook." | Active |

---

## Rule Details

### M1 — TOOL ROUTING
**Text:** Before every instruction, state tool + reason in one line. Cursor/Claude Code/Mac Terminal — pick the one that fits. Include Mode + Model + Reason header before every Cursor prompt block.
**Hook:** No — would fire too often on normal messages.

### M2 — WORKFLOW OUTPUT
**Text:** Every implementation request → Cursor prompt block as primary output. Never skip to prose code explanations.
**Hook:** No — no repeat failure pattern in CC.

### M3 — MODEL DOWNSHIFT
**Text:** After plan approved, Build defaults to Composer 2. Escalate to Sonnet only if Composer 2 fails. Never Opus for Build.
**Hook:** No — rare failure, not a repeat pattern.

### M4 — TOKEN DISCIPLINE
**Text:** Match tool cost to task complexity. Don't burn Opus tokens on Composer 2 work. Never sacrifice quality to save tokens.
**Hook:** No — judgment call, not detectable mid-action.

### M5 — NEVER INVENT
**Text:** commit hashes, pixel values, field names, API shapes, file contents. If unknown, say so + give the command to verify. HOOK: If stating a pixel value, commit hash, or field name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."
**Hook:** Yes — "Triggered never-invent hook."
**Trigger:** Stating a pixel value, commit hash, or field name without verification.
**Breakage history:** Invented `index.html` filename for CC v7 template (actual: `dashboard.html`), caused revert + 6 wasted messages.

### M6 — FILE ACCESS HONESTY
**Text:** In claude.ai, cannot read local files. Say what command to run and where — never guess from training data.
**Hook:** No — rule #14's hook catches the main failure mode (using Nick as slow proxy).

### M7 — HOVERIFY GATE
**Text:** Hoverify for layout/design measurements only. DevTools valid for JS debugging, network, console, element state. HOOK: If writing "DevTools", "F12", or "getBoundingClientRect" for a layout/measurement task — STOP: "Triggered Hoverify hook."
**Hook:** Yes — "Triggered Hoverify hook."
**Trigger:** Writing "DevTools", "F12", or "getBoundingClientRect" for layout tasks.
**Breakage history:** 3+ failures in CC v5 session. Suggested DevTools/getBoundingClientRect for layout measurements, corrected by Nick, broke it again in the same session.

### M8 — VERIFICATION GATE
**Text:** Never declare done without stating the specific verification result. HOOK: If writing "done", "fixed", "shipped", or "complete" without a verification output (screenshot, curl result, browser confirm) — STOP: "Triggered verification hook."
**Hook:** Yes — "Triggered verification hook."
**Trigger:** Declaring done without a verification output.
**Breakage history:** Systemic across sessions. CC 3.9 — declared warnings card done without browser verification. Resolved_conflicts session — declared implementation done without querying the DB.

### M9 — PACING LOCK
**Text:** One instruction, then WAIT. If Nick interrupts before confirming, push back: "Let's finish the current step first — [pending item]." Only override: Nick says "skip it" or "move on." HOOK: If writing a second instruction or tool call before Nick responds to the first — STOP: "Triggered pacing hook."
**Hook:** Yes — "Triggered pacing hook."
**Trigger:** Delivering a second instruction before Nick confirms the first.
**Breakage history:** Most-broken rule. CC 2.9 — stacked multiple commands. CC 4.0 — stacked instructions again. Multiple instances across sessions.

### M10 — PROJECT KNOWLEDGE REFRESH
**Text:** After shipping changes, offer file copy prompt using existing naming convention.
**Hook:** No — omission-type failure, not detectable mid-action.

### M11 — MEMORY EDITS = BEHAVIORAL RULES ONLY
**Text:** No status records, bug tracking, or feature states in memory. Those go to Obsidian or Project Knowledge.
**Hook:** No — single occurrence, not a repeat pattern.

### M12 — HANDOFF
**Text:** Read the handoff skill before running. Stage 1 (closeout + handoff block) at end of session. Stage 2 (Cursor prompt) generated in NEW session. Never combine stages. Never skip waits.
**Hook:** No — omission-type failure, hooks don't catch omissions well.

### M13 — CURSOR HEADER FORMAT
**Text:** Every Cursor prompt gets a visible header BEFORE the code block — Mode, Model, Reason on separate lines. First line INSIDE the prompt repeats [Model: X | Mode].
**Hook:** No — rule #15's hook catches formatting issues at the gate.

### M14 — CLAUDE CODE ESCALATION
**Text:** If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt (include: problem, files to read, likely causes, fix, verification). Do not debug incrementally in chat. HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."
**Hook:** Yes — "Triggered escalation hook."
**Trigger:** Asking Nick to cat/grep/curl a second time for the same issue.
**Breakage history:** CC 3.9 — multi-round chat diagnosis of warnings card bug before writing a prompt. Adopted from the client project where pattern was systemic.

### M15 — BEFORE EVERY CURSOR PROMPT
**Text:** Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch CSS? If yes, demand Hoverify measurements FIRST. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6. HOOK: If writing a Cursor prompt without checking mode/model/CSS — STOP: "Triggered pre-prompt hook. Run the 3-check gate."
**Hook:** Yes — "Triggered pre-prompt hook."
**Trigger:** Writing a Cursor prompt without running the 3-check gate.
**Breakage history:** Adopted from the client project where wrong model tags and missing Hoverify checks were documented repeat failures. Same Cursor workflow applies to CC.

### M16 — BUG ROUTING
**Text:** When a bug is reported — state the symptom, then write a Cursor Plan prompt or Claude Code prompt (per rule #14). No multi-step chat diagnosis. One clarifying question allowed if data only exists in browser/live site. HOOK: If asking a second diagnostic question without a prompt — STOP: "Triggered bug-routing hook. Write the prompt."
**Hook:** Yes — "Triggered bug-routing hook."
**Trigger:** Asking a second diagnostic question without writing a prompt.
**Breakage history:** CC 3.9 — multiple rounds of diagnostic questions about warnings card before writing a fix prompt. Adopted from the client project.

---

## Cross-References

- Rules #14, #15, #16 form the prompt-writing pipeline: #15 gates format, #14 decides Cursor vs Claude Code, #16 routes bugs into that pipeline immediately
- Rule #6 defers to #14's hook for the main failure mode (incremental chat debugging)
- Rule #13 specifies format that #15 validates at the gate

---

## Audit History

- 2026-04-11: Full audit per RULE-FIX-BLUEPRINT-v3.md. Pass 1 (bloat): 0 issues. Pass 2 (rule pairs): 0 contradictions. Pass 3 (vs User Preferences): 0 contradictions. 3 hooks added to existing rules (#7, #8, #9). Hook added to #5 (NEVER INVENT). 3 rules adopted from the client project (#14 ESCALATION, #15 PRE-PROMPT GATE, #16 BUG ROUTING). Final count: 16 rules, 7 hooks.

---

## Maintenance

- When adding a new memory edit to command-center-v7, add it here AND in RULES-REGISTRY.md
- When removing a memory edit, update status to "Retired" with date
- Keep retired rules for history — don't delete entries

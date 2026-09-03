# aibs-core-rules.md — Memory Edits for AIBS Core Project
# Last updated: 2026-04-12
# Total rules: 13

## 1. PRE-FLIGHT GATE
For deploys/migrations/remote ops — 1) Plan: investigate prerequisites, verify target DocTypes/apps exist on live site. For cloud sites, include API URL checks. Wait. 2) Verify prompt. Wait. 3) Build only when Nick approves. Skip for simple edits. First batch of any migration/bulk op: limit=1, verify single record before full run.
HOOK: If writing build code without Plan first — STOP: "Triggered pre-flight hook."

## 2. ROUTING GATE
After stating a problem/task, FIRST action is a Claude Code prompt — no chat-side investigation. One question to Nick allowed ONLY if data is on live site/browser only. If first prompt fails, escalate to Debug-mode Claude Code. Never retry same approach.
HOOK: If sending 2+ consecutive messages without a Claude Code prompt block while investigating — STOP: "Triggered routing hook. Write a Claude Code prompt now."

## 3. CLAUDE CODE ESCALATION
If a bug or task touches 3+ files or traces data flow across files, write a single Claude Code prompt. Also use Claude Code for framework investigation — reading Frappe/ERPNext source to understand how a feature works before building against it. Overrides Routing Gate (M2) for tool choice when 3+ files involved.
HOOK: If asking Nick to cat/grep/curl a second time for the same issue — STOP: "Triggered escalation hook. Write a Claude Code prompt."

## 4. NEVER INVENT
commit hashes, pixel values, field names, DocType names, API shapes, file contents, naming conventions. If unknown, say so + give the command to verify.
HOOK: If stating a pixel value, commit hash, field name, or DocType name without verification — STOP: "Triggered never-invent hook. Verify first or say unknown."

## 5. BEFORE EVERY CURSOR PROMPT
Stop. Check: (1) Is this Plan or Build? Use correct mode and model tag. (2) Does it touch the live site? If yes, Pre-flight gate (M1) applies — no exceptions. (3) Is the model tag correct? Plan=Sonnet 4.6, Build=Composer 2, Debug=Sonnet 4.6.
HOOK: If writing a Cursor prompt without checking mode/model/live-site — STOP: "Triggered pre-prompt hook. Run the 3-check gate."

## 6. DATA VALIDATION
Before migrating data, confirm with Nick that source data is real production data, not demo/seed/fictional. All Flask app JSON files and PostgreSQL tables contain fictional data — do not migrate them. If data origin is unclear, ask before proceeding.

## 7. READ CONTROLLER SOURCE
Before writing insert/submit/save code for any standard ERPNext DocType, read its controller source via Claude Code first. ERPNext controllers have extensive validate() chains that break programmatic inserts.
HOOK: If writing frappe.get_doc().insert() or .submit() for a standard DocType without reading its controller — STOP: "Triggered controller-read hook."

## 8. NO FALSE REASSURANCE
After a failure or error, never say "this should work now" or "that should fix it." State what was changed and what specific verification to run. If the fix is uncertain, say so explicitly.

## 9. HANDOFF CONSUMPTION
When a new session starts with a handoff block, read it fully before responding. Do not ask questions already answered in the handoff. Reference specific values from it (commits, file paths, constraints) to confirm you absorbed it.

## 10. PLATFORM LIMITATION CHECK
Before building any integration that fights the platform (SSE on managed hosting, IMAP polling on limited workers, OAuth monitoring with no alert system), evaluate whether an external service handles it more reliably. If external is simpler and cheaper, use it. Document the evaluation.

## 11. INSTRUCTION FORMAT
All instructions to Nick must be numbered plain English steps — not code-flavored prose, not inline commands buried in paragraphs. Each step = one action + one tool + expected result. Deploy instruction format is the template.
HOOK: If writing instructions as prose with embedded commands instead of numbered steps — STOP: "Triggered format hook. Rewrite as numbered steps."

## 12. FILE ACCESS
Project Knowledge files are always accessible — search them directly, never claim you can't read them. For LOCAL filesystem files not in Project Knowledge: ask Nick to paste the command in Mac Terminal (not Claude Code, which intercepts and summarizes). Never say "I can't read files" without first checking Project Knowledge.

## 13. TOOL UI REFERENCE
Before writing tool-specific instructions, search Project Knowledge for the matching file — never guess button names, shortcuts, or commands. Routing: Cursor → tools-cursor.md, Frappe Cloud → tools-frappe-cloud.md, ERPNext Desk → tools-erpnext-desk.md, bench CLI → tools-bench-cli.md. Read ONLY the matching file.
HOOK: If stating a button name, menu path, shortcut, or command flag without searching the matching tool file — STOP: "Triggered tool-reference hook."

---

## Changelog
| Date | Change |
|------|--------|
| 2026-04-12 | #3 wording fix: "Overrides Bug Routing" → "Overrides Routing Gate (M2)". File restored after sed blanked it. |
| 2026-04-12 | #12 added: FILE ACCESS. #13 added: TOOL UI REFERENCE with hook. Registry synced with M6–M13. |
| 2026-04-12 | #2 replaced: BUG ROUTING GATE → ROUTING GATE (Claude Code first, countable hook trigger, escalation path). #11 added: INSTRUCTION FORMAT. |
| 2026-04-12 | Initial creation with 10 rules from RF1–RF7 audit. |

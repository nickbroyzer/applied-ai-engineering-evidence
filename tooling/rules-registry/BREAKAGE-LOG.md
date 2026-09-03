# BREAKAGE-LOG.md — Rule Breakage History

Running log of rule failures, root causes, and fixes applied.
Location: ~/Projects/ai-rules/BREAKAGE-LOG.md

Purpose: Make patterns visible. If the same rule breaks 3+ times, the fix isn't working — escalate.

---

## How To Use

After every rule fix session, add an entry below. One row per problem. Fill every column.

- **Date**: Session date
- **Project**: Which project the failure occurred in
- **Rule**: Registry ID (e.g., U2, M1) — must match RULES-REGISTRY.md
- **Failure**: What specifically went wrong (one sentence)
- **Root Cause**: A (no rule), B (gap), C (not specific), D (not followed)
- **Fix Applied**: What was changed (new rule, expanded rule, hook added, no action)
- **Fix Held?**: Updated in a later session — Yes, No, or Untested

---

## Log

Tracking began 2026-04-10. Rules created before this date were based on accumulated session failures — see RULES-REGISTRY.md for their current state.

| Date | Project | Rule | Failure | Root Cause | Fix Applied | Fix Held? |
|------|---------|------|---------|------------|-------------|-----------|
| 2026-04-10 | aibs-core | U5 | Said "terminal" without specifying which one | C — not specific enough | Rewrote TOOL ROUTING with exact tool list | Untested |
| 2026-04-10 | aibs-core | U2 | Stacked multiple instructions without waiting | D — clear rule, not followed | Added formal hook to PACING LOCK | Untested |
| 2026-04-10 | aibs-core | — | Diagnosed bugs in chat instead of routing to Cursor | A — no rule existed | Created BUG ROUTING GATE (M2) with hook | Untested |
| 2026-04-10 | aibs-core | — | Wrote build code without investigation plan | A — no rule existed | Created PRE-FLIGHT GATE (M1) with hook | Untested |
| 2026-04-10 | aibs-core | — | Delivered subset of requested scope as complete | A — no rule existed | Created SCOPE COMPLIANCE (U8) | Untested |
| 2026-04-12 | aibs-core | — | Migrated fictional demo data from Flask JSON files — hours wasted on Phase 3 payroll | A — no rule existed | Created DATA VALIDATION (M6) | Untested |
| 2026-04-12 | aibs-core | — | Wrote DocType insert/submit code without reading controller source — validation chain failures | A — no rule existed | Created READ CONTROLLER SOURCE (M7) with hook | Untested |
| 2026-04-12 | aibs-core | M1 | First migration batch ran full count before verifying a single record worked | B — pre-flight gate lacked limit=1 | Expanded PRE-FLIGHT GATE (M1) with limit=1 first-run clause | Untested |
| 2026-04-12 | aibs-core | U6 | Said "this should work now" after failure without specific verification steps | A — no rule for anti-pattern language | Created NO FALSE REASSURANCE (M8) | Untested |
| 2026-04-12 | aibs-core | M3 | Debugged Frappe/ERPNext features in chat instead of reading framework source via Claude Code | B — escalation rule didn't cover framework investigation | Expanded CLAUDE CODE ESCALATION (M3) with framework investigation clause | Untested |
| 2026-04-12 | aibs-core | — | Asked questions already answered in the handoff block at session start | A — no rule existed | Created HANDOFF CONSUMPTION (M9) | Untested |
| 2026-04-12 | aibs-core | — | Evaluated SSE on managed hosting without considering external service alternatives | A — no rule existed | Created PLATFORM LIMITATION CHECK (M10) | Untested |
| 2026-04-12 | aibs-core | U9 | Claude refused to read Project Knowledge files, claimed "can't read local files" | C — FILE ACCESS HONESTY not specific enough for PK vs local | Created FILE ACCESS (M12) distinguishing PK from local | Yes (2026-04-12) |
| 2026-04-12 | aibs-core | — | Guessed button names, menu paths, shortcuts for Frappe Cloud and other tools across multiple sessions | A — no rule existed | Created TOOL UI REFERENCE (M13) with routing table and hook | Yes (2026-04-12) |
| 2026-04-12 | aibs-core | — | Gave Cursor prompts when Claude Code was the correct tool — instructions said "Claude Code prompt" but output was formatted as Cursor prompt | A — no rule existed | Created INSTRUCTION FORMAT (M11) with hook | Untested |
| 2026-04-13 | aibs-core | U10 | Claude Code prompt delivered with Cursor formatting ([Model: Sonnet 4.6 | Plan] inside code block) | B — rule gap. No scoping on Cursor format, no Claude Code format defined | Scoped CURSOR PROMPT FORMAT to Cursor-only, added CLAUDE CODE PROMPT FORMAT (U18) with Tool/Mode/Reason header | Yes |

---

## Pattern Watch

Rules that have broken 2+ times (update as log grows):

- (none yet — all fixes are untested as of 2026-04-10)

---

## Maintenance

- Add entries after every rule fix session
- Update "Fix Held?" column when you revisit a rule that was previously fixed
- If a rule appears 3+ times with "No" in Fix Held: the fix strategy isn't working — try a different approach per RULE-FIX-BLUEPRINT.md Step 2
- Keep this log indefinitely — don't purge old entries, they show evolution
| 2026-04-18 | db-auto-detailing | — | New project, no prior rules | A — no rule existed | Created 25 memory edits (M1–M25), DECISIONS.md, db-auto-detailing-rules.md, registry section | Untested |
| 2026-04-21 | zelbi | U13 | Message counter drift and handoff-at-20 skip across multiple sessions — counter dropped, handoff offer at 18 missed, session ended at 20 without handoff | D — clear rule, not followed | Added hook to U13 (counter hook) requiring [Message N/20] as first line every response; added zelbi M21 MESSAGE COUNTER as reinforcement | Untested |
| 2026-04-21 | zelbi | U4 | File path invention 5+ times in Session 28 — absolute and relative paths stated without verification | B — gap in NEVER INVENT trigger list, file paths not enumerated | Expanded U4 text to include "file paths" in trigger list; expanded zelbi M3 hook trigger to include "absolute/relative file path" | Untested |
| 2026-04-21 | zelbi | M4 | Asserted cause of stale-connection bug before running any verification command in Session 28 — caused rabbit hole | B — gap in VERIFICATION GATE, only covered "declaring done" not "asserting cause" | Expanded zelbi M4 text with cause-assertion clause; trigger expanded to catch "the cause is X" on reported problems with no verification command run that session | Untested |
| 2026-04-21 | zelbi | — | Unverified grep regex used in Session 28 — first occurrence | Deferred (monitor) | No action — first occurrence, monitor for repeat per Blueprint Step 2 | N/A (deferred) |
| 2026-04-21 | zelbi | U14 | Session 29 handoff block claimed rule-fix pass "settled — DO NOT REVISIT" but external file updates (RULES-REGISTRY.md, BREAKAGE-LOG.md) were never delivered; Session 30 opened on commits instead of finishing rule-fix external files | B — HANDOFF PROTOCOL gap, no check that all NEXT TASK items from handoff are still listed as pending not completed | Session 30 caught via Nick push-back; no rule change yet — flagging for Blueprint Step 2 analysis next rule-fix session | No (open) |

| 2026-04-22 | zelbi | M15 | Rule named docs/agents/09-sage-build-spec.md as schema source of truth, overriding models.py and the current Alembic head. | B — gap: rule named the spec doc as schema authority above the actual implementation artifacts | Rewrote M15 to name models.py and current Alembic head as schema source of truth; spec doc demoted to reference-only | Untested |
| 2026-04-22 | zelbi | M16 | Rule named the decisions table in docs/agents/10-implementation-plan.md as canonical, overriding the approved decisions themselves. | B — gap: rule named the spec doc decisions table as canonical above the approved decisions | Rewrote M16 to name approved decisions as canonical; spec doc decisions table demoted to reference-only | Untested |
| 2026-04-22 | zelbi | M12 | Session 34 — wrote Stage 1 handoff block in chat reconstructed from memory. Skill file was accessible in project knowledge and M12 required reading it first. | D — clear rule not followed | Session 35 expanded M21 to add handoff-read hook: "Writing handoff content without reading the skill this session — STOP: Triggered handoff-read hook." Bloat flag acknowledged (M21 now combines counter + handoff-exec, two concepts) per explicit direction not to revert Session 34's work. Hook tested in-session at message 15. | Untested |
| 2026-04-27 | zelbi | M20 | Code identifiers in prose to Nick across multiple sessions despite M20 memory hook firing previously. Same pattern: rule clear, hook well-formed, still not followed. | D — clear rule, not followed | Created universal U19 PLAIN ENGLISH PROSE in user preferences (TIER 1) with same hook; renamed and aligned zelbi M20 to match U19 wording. Reinforcement pattern matching M12 → M21. | Yes (2026-04-27) |
| 2026-05-04 | zelbi | — | 00-current-state.md grew to 144,316 characters (over 25,000-token single-read cap). Stage 2 closeout required chunked reads. Append pattern compounded across Sessions 105–123 because no rule constrained how Sections 1, 3, 8 grew. | A — no rule existed. Handoff skill Stage 2 TASK 3 was silent on append vs. replace discipline. | (1) One-time restructure of 00-current-state.md to 43,938 characters (commit e55f435). (2) Handoff skill Stage 2 TASK 3 amended with four append-discipline subrules (commit 30a1ad8). (3) Memory rule M26 BRIEF APPEND DISCIPLINE added with append-discipline hook. Hook tested in same-session simulation: fired on simulated grow-Section-1 str_replace. Pass. | Pending — first real test is Session 125 Stage 2 |
| 2026-05-05 | zelbi | U14 / zelbi M12 | Stale paperwork lines in handoff block carried forward as live work across twelve consecutive sessions (121–132). Phase 8B sub-step 2 was device-verified on Session 120 but the tracking line was never ticked; each subsequent session inherited the unticked line. Brief Section 1 drifted in lockstep because the closing session writes both Block 1 and Section 1 — no independent artifact to catch the drift. Root: Session 114 v2 redesign of handoff-protocol.md removed cross-check redundancy (Block 2, SAFE RESTORE, hard STALE WARNING). | B — gap at two author points: handoff block had no taxonomy forcing the closing session to commit to a category for each carry-forward task, and no reconciliation step against an independent record before writing the new block. Stage 2 Section 1 patch had no precondition reconciling against append-only session history. | Four amendments to backend/.claude/skills/handoff-protocol.md across two commits (1bc056d + 5a44534): (1) NEXT TASK status-tag vocabulary — [BUILD-OPEN], [VERIFY-OPEN], [PAPERWORK-OWED], [UNVERIFIED-INHERITED; orthogonal to existing BUG FIX: prefix. (2) Closeout check step 10 — inherited NEXT TASK reconciliation against Section 5 history + git log. (3) Safe restore point line restored under WORKING-TREE STATE. (4) Stage 2 Task 3 — Section 1 reconciliation precondition against Section 5. Plus User Preferences U14 corrected (Cursor → Claude Code, NEW → end of OLD session) and matching registry entry updated. Read-through verification passed. | Untested - runtime test fires at next session's handoff close (simulation pass on design, Session 133) |
| 2026-05-11 | db-auto-detailing | M22 | Hoverify Gate routed layout measurements to manual browser inspection when Claude Code + Playwright could read the same values from localhost with zero manual work | C — not specific enough (rule predated Playwright option) | Replaced M22 memory rule with MEASUREMENT ROUTING. Playwright via Claude Code preferred for running local dev server, Hoverify fallback only. New hook on the rule. User Preferences HOVERIFY GATE pending Nick-side paste (cross-project). | Yes (2026-05-11 — same-session Playwright run returned all six spec anchors cleanly) |
| 2026-05-11 | db-auto-detailing | M12 | M12 HANDOFF wording drifted hard from zelbi v2. Stage 1 grew to 60-line walls instead of 3-section blocks. Stage 2 was repurposed as next-session Build prompt instead of THIS-session closeout. BUILD.md was used as the canonical brief but never refreshed in Project Knowledge (17 sessions stale at Session 21 audit). | B — gap (covered the area but not the specific drift) | Authored db-auto-detailing-handoff-protocol.md modeled on zelbi v2 and added to Project Knowledge. Created 00-current-state.md as canonical session-start brief. Retired BUILD.md (git-rm'd from repo, deleted from Project Knowledge). Replaced M12 memory rule to point at the protocol file. | Untested — first test is Session 22 reading the handoff block + attached 00-current-state.md without generating Stage 2. Flag UNVERIFIED until Session 22 closes |

## 2026-05-05 — Verbose responses (RESOLVED)
**Failure:** Claude produces multi-paragraph prose explanations, preambles, recaps, and closers before the deliverable. Nick's #1 stated irritant.
**Frequency:** Recurring across many sessions, all projects.
**Root Cause:** A — No rule. U3/M6 covered output format but not prose length.
**Fix Applied:** New rule U20 RESPONSE BREVITY filed in User Preferences TIER 1, mirrored as Zelbi M27. Includes hook for self-catch.
**Fix Held?** Yes (2026-05-05 — held throughout filing session, no violations).

## 2026-05-05 — Plain English prose violations (REVISED FIX)
**Failure:** Code identifiers in prose sentences across many sessions despite U19 + M20 both having hooks.
**Frequency:** Recurring across multiple sessions, all projects.
**Root Cause:** C + D — U19 hook had malformed trigger phrase (typo from 2026-04-27 created circular text "Move to plain-English hook"). Compliance also failed even when hook was logically clear.
**Fix Applied:** (1) Corrected U19 hook trigger to "Move to prompt block" matching M20. (2) Added pre-send scan instruction per blueprint "change strategy after repeat failure." M20 unchanged (already correct).
**Fix Held?** Yes (2026-05-05 — held throughout filing session, no violations).

## 2026-05-05 — Pacing violations (REVISED FIX, TESTED PASS)
**Failure:** Two distinct failure modes recurring across many sessions: (1) stacking instructions in one message; (2) asking clarifying questions after a deliverable that awaited confirmation. Both rationalized through prior hook because trigger language was ambiguous on prose questions.
**Frequency:** Recurring across many sessions, all projects. Caught twice in the same session pacing rule was being audited.
**Root Cause:** C + D — Hook trigger named "tool call or second instruction" only, which let clarifying questions and scope asks slip through (Cause C). Stacking failure also recurs even when explicitly forbidden (Cause D).
**Fix Applied:** (1) U2 hook trigger sharpened to enumerate four failure modes: (a) second instruction, (b) tool call, (c) clarifying question, (d) scope ask. (2) M7 mirror updated via memory tool with same enumeration. (3) Body of U2 unchanged.
**Fix Held?** Yes (2026-05-05 — held throughout next session, verified).

## 2026-05-05 — Decision-overload questions (NEW RULE FILED)
**Failure:** Claude presents Nick with 2+ implementation options or asks him to choose between technical approaches when one is clearly correct or implementable directly. Examples: "Do you want approach A or B?", "Should I check X first or proceed?", listing 3 paths forward when Claude should pick one and execute. Forces Nick to make decisions that are Claude's to make.
**Frequency:** Recurring across many sessions, all projects. Flagged in handoff as "no existing rule covers this."
**Root Cause:** A — No rule existed. U13 SCOPE COMPLIANCE covers scope clarification before starting; nothing covered decision-presentation during execution. Memory prose "Technical decisions are Claude's to make" existed as principle but had no enforcement rule or hook.
**Fix Applied:** New universal rule U21 DECISION OWNERSHIP filed in User Preferences TIER 1 after PACING LOCK. Includes hook for self-catch on writing questions with 2+ options or "should I X or Y" between technical approaches. Registry entry added.
**Fix Held?** Yes (2026-05-05 — held throughout next session, verified).

## 2026-05-05 — Prompt block format (NEW RULE FILED)
**Failure:** Claude combined the prompt header (Tool/Mode/Reason) and the actual paste-able command into a single fenced code block for Mac Terminal commands. Forced Nick to manually strip the header before pasting. Failed three times in the filing session before correction.
**Frequency:** Unknown across history but failed 3 times in a single session. Existing format rules covered Cursor and Claude Code prompts but not Mac Terminal.
**Root Cause:** A — No rule existed for Mac Terminal command format. U10 CURSOR PROMPT FORMAT and U18 CLAUDE CODE PROMPT FORMAT were scoped tool-specific and did not extend to Mac Terminal.
**Fix Applied:** New universal rule U22 PROMPT BLOCK FORMAT filed in User Preferences TIER 3, replacing U10 and U18. Covers all three tools uniformly with the same two-block pattern. Hook added for self-catch on combining header and command in one block. U10 and U18 marked superseded in registry.
**Fix Held?** Yes (2026-05-05 — held throughout next session, verified).

## 2026-05-05 — Brevity hook landed (~/.claude/hooks/brevity-hook.py)
**Rule enforced:** U20 RESPONSE BREVITY (Tier 1, Universal). Maximum three sentences of prose before the first code block, prompt block, table, or list.
**Where:** `~/.claude/hooks/brevity-hook.py`
**Event:** Stop
**Detection:** Reads `last_assistant_message` from stdin JSON. Strips `<thinking>` blocks. Walks lines until first fence, list item, or table row. Counts sentences in the prose prefix via terminal-punctuation split. If count > 3, exits 2 with stderr message including the actual count.
**Stderr message:** `Triggered brevity hook. Cut to the deliverable. Found N sentences of prose before first code/list/table block (limit: 3).`
**Built:** Prior session (file timestamp 2026-05-05 22:28). Already firing in production — caught two violations earlier in this session.
**Fix Held?** Yes (firing as designed).

## 2026-05-05 — Plain-English hook landed (~/.claude/hooks/plain-english-hook.py)
**Rule enforced:** U19 PLAIN ENGLISH PROSE (Tier 1, Universal). No code identifiers in prose sentences outside fenced blocks, prompt blocks, inline backtick spans, or explicit value lists.
**Where:** `~/.claude/hooks/plain-english-hook.py`
**Event:** Stop
**Detection:** Reads `last_assistant_message`. Walks prose lines (excluding fenced blocks, list items, table rows, headings, blockquotes, `<thinking>` blocks). Strips inline backtick spans. Scans for: file extensions, snake_case, camelCase, ALL_CAPS constants, function-call shape, file paths. Skips file extensions inside URLs.
**Stderr message:** `Triggered plain-English hook. Move to prompt block.` plus per-line citations.
**Built:** Prior session (file timestamp 2026-05-05 22:33). Already firing — caught three violations earlier in this session.
**Fix Held?** Yes (firing as designed).

## 2026-05-05 — Pacing hook rewritten (~/.claude/hooks/pacing-hook.py)
**Failure:** Original pacing hook was registered on PreToolUse with a per-session counter persisted in `/tmp/claude-pacing-{session_id}.json`. It incremented on every PreToolUse and blocked at >1 call per turn, conflating stacked instructions to Nick (the actual U2 violation) with internal tool sequencing inside one user-approved task. Symptom: a single user message saying "back up settings, write the hook, chmod, run tests" blocked at the second tool call.
**Root Cause:** B — gap. The original detection had no signal distinguishing "assistant talking to Nick" from "assistant executing approved task." It counted PreToolUse events instead of scanning outgoing chat content.
**Fix Applied:** Rewrote as a Stop hook scanning `last_assistant_message` for stacked asks. Heuristic ask-block count: header signatures (`CURSOR INSTRUCTIONS`, `Tool: Claude Code`), "Run this..." / "Paste this..." intros, and presence of 2+ imperative numbered list items (counted as one ask block). If 2+ ask blocks present, exit 2. Moved registration from PreToolUse to end of Stop array (settings.json bak5 precedes the move). Removed orphaned `/tmp/claude-pacing-*.json` state files.
**Stderr message:** `Triggered pacing hook. Detected N stacked asks to Nick in one reply. Deliver one ask, then wait for confirmation.`
**Caveat:** Heuristic, not exhaustive. Plain-prose stacked asks ("After the migration, also restart Postgres and clear Redis") still slip past — detection only catches header blocks, "Run this..." intros, and numbered imperatives. Strictly better than the old behavior (which blocked only false positives) but not a perfect U2 enforcer.
**Tests:** 8 unit tests with synthetic JSON payloads via `printf '%s'` (zsh `echo` interprets backslash escapes and corrupts JSON — burned that lesson once already today). 8 PASS / 0 FAIL.
**Fix Held?** Untested in production — needs real-session observation across multiple sessions.

## 2026-05-05 — Prompt-format hook landed (~/.claude/hooks/prompt-format-hook.py)
**Rule enforced:** Tier 3 prompt-block format. Every prompt or command for Nick to execute follows a two-block pattern: header in one fenced block (`CURSOR INSTRUCTIONS` / `Tool: Claude Code` / `Tool: Mac Terminal` headers), command in a separate fenced block. Violation = a single fence containing BOTH a header signature (2+ of `CURSOR INSTRUCTIONS`, `Tool:` header, `Mode:`, `Reason:`, qualifying `Model:`) AND command content lines.
**Where:** `~/.claude/hooks/prompt-format-hook.py`
**Event:** Stop
**Detection:** Reads `last_assistant_message`. Splits into fenced blocks via line-by-line walk over triple-backtick boundaries. Per block: counts header-signature lines, counts command-content lines, excluding blank lines and the legitimate `[Model: X | Mode]` repeat line that appears alone inside Cursor command blocks. The standalone `Model:` line counts as a header signature only if `Mode:` or `Reason:` also appears in the same block (guards against false-fire on the bracketed repeat).
**Stderr message:** `Triggered prompt-format hook. Split into two blocks: header in one fence, command in a separate fence.`
**Built:** This session.
**Tests:** 8 unit tests covering empty payload, two-separated-blocks (PASS), one-block-combined (FIRE), Model-repeat-only (PASS), prose-only (PASS), full Cursor combined (FIRE), header-alone (PASS), Mac Terminal combined (FIRE). All 8 passed on first run.
**Live-fire test:** Sent a violating fence in a real reply this session; hook fired with the exact expected stderr.
**Fix Held?** Yes (verified live).

## 2026-05-13 — PRIME DIRECTIVE / NEVER INVENT merged + hook added (Session 182, fixes Session 181)
**Failures (Session 181):** The prior U4 / zelbi M3 NEVER INVENT rule was broken 4 times in one session:
  1. Composed the qualifier "unverified on Give tab" with no source — extrapolated doubt that was not in any document.
  2. Composed the status framing "has not passed app-wide" — editorialized a status claim with no source quote.
  3. Appended the editorial sentence "Survey file at ... holds the canonical checkpoint list" inside a proposed str_replace new_str — invented content presented as if drawn from the source document.
  4. Wrote "either the files don't exist, the M3 anchor uses different formatting, or the files are empty" — unverified-cause enumeration when one ls command would have answered it.
**Root Cause:** B + D combined. (B — gap: prior rule's enumerated triggers named technical identifiers only, missing qualifiers, framings, status claims, scope text, and unverified-cause enumerations.) (D — non-compliance: even where the rule applied, the absence of a self-interrupt hook meant the broader invention class slipped through every time.)
**Audit findings (Session 182):**
  - PRIME DIRECTIVE block (above Tier 1) and U4 NEVER INVENT entry (inside Tier 1) duplicated each other — both forbade unverified assertions but with different scopes. Caught in Pass 2 conflict check.
  - PRIME DIRECTIVE had no hook (Pass 3 hook gap).
  - U4 enumerated technical values only (Pass 1 scope gap).
  - Two unrelated audit issues flagged but deferred to separate sessions: COUNTER + HANDOFF EXEC bloat (one Tier 3 rule combining two concepts), and orphan "Never bulk-insert JS" line at bottom of preferences.
**Fix Applied:**
  - Merged PRIME DIRECTIVE block and U4 NEVER INVENT into single rule at top of User Preferences, above Tier 1, retaining "overrides all other rules" framing.
  - Expanded scope to all factual content (facts, identifiers, status, qualifiers, framings, scope text, implied conclusions).
  - Added 3-source requirement: (i) read this session, (ii) Nick verbatim, (iii) Nick instruction. Anything else = [UNKNOWN] + verify command.
  - Added 12-phrase forbidden list with hard auto-trigger: likely, probably, should be, presumably, appears to, seems to, could be, might be, this implies, we can assume, it follows that, "either X or Y" / "X, Y, or Z" patterns.
  - Added status-word backtick-quote-source requirement for passed/failed/blocked/partial/complete/works/broken.
  - Single HOOK consolidates all three trigger conditions (invention, guessing, status claim) with one STOP phrase.
  - Memory M3 compressed to 500 chars preserving the 3-source check, status word list, full forbidden-phrase list, and hook triggers; full prose lives in PRIME DIRECTIVE.
  - Registry U4 entry + zelbi M3 entry both updated to reflect merged rule. Index rows bumped to 2026-05-13.
**Confidence at install:** ~78% effectiveness across the failure modes. Breakdown: forbidden-phrase syntactic catch ~92%, status-word backtick check ~85%, identifier invention ~75%, qualifier/framing semantic catch ~65%, editorial-sentence catch ~60%. Weighted by Session 181 failure mix. Above 85% requires inline source tags or verbatim-quote requirements on every fact (trades response quality for enforcement).
**Tests:** Two deliberate same-session trigger tests passed (2026-05-13): (1) forbidden-phrase trigger fired on attempted use of "likely" in a fact-asserting sentence; (2) status-claim trigger fired on attempted use of "passed" without backtick-quoted source. Both produced the expected STOP message.
**Fix Held?** Yes (same-session syntactic tests passed). Semantic catches (qualifier/framing/editorial sentence) flagged for observation across Session 182 remainder and next 3 sessions — re-enter blueprint at Step 2 if a same-class failure occurs.
**Follow-up flagged:** Audit also identified COUNTER + HANDOFF EXEC bloat and orphan JS line. Both deferred — each gets its own session for proper research and fix per blueprint Step 1 ("one problem at a time").
## BL-M3-001 — NEVER INVENT identifier-type enumeration gap (Session 188, B1 fix pass)

| Field | Value |
|-------|-------|
| entry_id | BL-M3-001 |
| date | 2026-05-13 |
| session_ref | Session 188 (B1 fix pass) |
| rule_id_violated | M3 (zelbi) / U4 (universal) |
| failure_description | userPreferences PRIME DIRECTIVE hook trigger surface omitted identifier-type enumeration that was present in memory M3 reference text. Dual-location rule had drifted between memory and preferences. Hook fired on (a) source tag, (b) forbidden phrase, (c) status without backtick source — but did not fire on bare covered identifiers (table names, column names, endpoint paths, Stripe events, PostGIS functions, Expo APIs, file paths) used in prose without citation. |
| root_cause | C — Rule isn't specific enough (userPreferences hook was vague where memory enumerated concrete identifier classes) |
| fix_applied | Added identifier-type enumeration sentence to PRIME DIRECTIVE opening. Added HOOK clause (d) enumerating bare covered identifiers. Memory M3 compressed to fit 500-char cap while preserving the seven identifier classes and four-check hook structure. Both locations now carry the same four-check (a/b/c/d) hook surface. |
| test_surface_at_fix_time | Phase 1 positive cases (6 examples) + Phase 2 negative cases (6 examples) documented in Session 188 Step 6 template. Test execution deferred to Phase 3 watch window. |
| field_scenario_that_broke_it | Identifier leakage in multi-paragraph drafts (Message 1 audit gap class 4) |
| watch_window_result | In Progress (Session 1 of 5 starts next session) |

## BL-M29-001 — USERPREFS EDIT OUTPUT rule filed (Session 188, new rule Cause A)

| Field | Value |
|-------|-------|
| entry_id | BL-M29-001 |
| date | 2026-05-13 |
| session_ref | Session 188 (filed during B1 fix pass) |
| rule_id_violated | M29 (rule did not exist prior to this session — Cause A backfill) |
| failure_description | When changing userPreferences, partial-section or surgical-edit instructions were delivered instead of a single complete-document paste. Session 188 Messages 9–11 showed the failure pattern: offered (a) one-sentence addition + (b) paragraph replacement separately, requiring Nick to splice manually. Nick had to ask three times for a single-paste replacement. |
| root_cause | A — No rule existed covering userPreferences edit output format |
| fix_applied | Added M29 USERPREFS EDIT OUTPUT to zelbi memory slot 30. Shape 3 omission hook fires when a response touches userPreferences content without producing a single complete-document fenced block. |
| test_surface_at_fix_time | 3 positive trigger cases (partial paragraph, multi-block edits, splice instructions) + 3 negative trigger cases (full-doc single block, full-doc with ⚠️ callout, memory edits via tool) documented in Session 188 Step 6 template. Positive cases retroactively confirmed from same-session evidence (Messages 9–11). Phase 3 watch starts next session. |
| field_scenario_that_broke_it | Same-session Messages 9–11 (surgical-edit instructions) |
| watch_window_result | In Progress (Session 1 of 5 starts next session) |

## BL-M21-001 — M21/M12 handoff Stage 2 PK read violation (Session 193)

| Field | Value |
|-------|-------|
| entry_id | BL-M21-001 |
| date | 2026-05-14 |
| session_ref | Session 193 |
| rule_id_violated | M21 (also M12 — same violation) |
| failure_description | Generated Stage 2 Claude Code prompt at message 21 reconstructed from partial `project_knowledge_search` snippets pulled at message 1 plus prior-session memory. Did not perform a complete PK read of handoff-protocol.md before drafting Stage 2. Result was a 90-line prompt bundling archival migration + Tasks 1–7 + embedded conditionals, parallelized incorrectly by Claude Code, required three rounds of mid-flight review, burned ~40 minutes wall time. |
| root_cause | B (rule has a gap — `this session` scope let Stage 1 partial read satisfy Stage 2; partial snippets unforbidden) |
| fix_applied | M21 v4 — per-stage scope, outcome-based complete PK read of canonical skill file required before each stage (Session 194 rewrite of Session 193 patch) |
| test_surface_at_fix_time | Positive triggers tested same-session (this fix session). Field validation: 5-session watch window starts Session 194. |
| field_scenario_that_broke_it | Stage 2 generated 20+ messages after Stage 1 in same session, with no fresh skill read between stages. |
| watch_window_result | In Progress |

## BL-M31-001 — Block 1 CONDUCT LESSONS bullets read but not applied (Session 222 fix pass)

| Field | Value |
|-------|-------|
| entry_id | BL-M31-001 |
| date | 2026-05-18 |
| session_ref | Session 222 (rule-fix session) |
| rule_id_violated | None pre-existed — Cause D at rule layer plus architectural hook-layer gap (Cause A backfill for the hook architecture) |
| failure_description | Across 30+ verified sessions spanning April 22 to May 18 (Sessions 28 through 221), the closing session's CONDUCT LESSONS bullets in Block 1 were read at message 1 of the new session and the named failure mode was repeated within 1-13 messages of the same session. The closing session correctly identified the failure; the opening session correctly read it; the opening session violated it anyway. Verified in Sessions 28 (M3 path invention recurrence, the original "rules requiring internal recognition lose to zero-step defaults" diagnosis), 95 (surfacing dead files Nick had locked), 180 (handoff-vs-reality drift), 190 (four lessons in one session), 193 (handoff skill-read skipped mid-stage), 194 (invented "me tab" one message after citing M3), 207 (drafted D-entries as chat prose before prompt block), 209 (M3 invented Stage 2 step and defended with a second invention), 217 (listed known-bad workaround as choice), 219 (rule-known-but-ignored six times in one session at messages 2/3/5/7/9/10), 220 (treated brief warnings as background instead of constraints), and continuous in Sessions 221 forward. |
| root_cause | D (rule clear, not followed) at the rule layer combined with an architectural gap at the hook layer — the six existing Python hooks scan static patterns (forbidden phrases, header shape, brevity, identifier leakage), none ingests Block 1 CONDUCT LESSONS as a dynamic scan input. |
| fix_applied | New universal rule U23 CONDUCT LESSON BINDING filed in User Preferences TIER 1 between HYPOTHESIS-LOCK and M27 WORKTREE DRIFT GUARD. Zelbi mirror M31 filed in zelbi-rules.md. Shape 2 category hook with three signals. Acknowledged in-model recognition ceiling per Session 28 diagnosis (~50-60% catch rate). Part 2 deferred — Python hook conduct-lesson-hook.py at ~/.claude/hooks/ to be designed in a dedicated session, will parse Block 1 bullets and scan every outgoing message against them as external enforcement layer. |
| test_surface_at_fix_time | Six positive trigger cases (P1-P6) and five negative trigger cases (N1-N5) documented in session transcript at Step 8. Three acknowledged blind spots (G1 abstract bullets, G2 semantic similarity, G3 multi-message latent violations). Phase 1 + Phase 2 same-session validation not exercised — rule-fix session had no Block 1 CONDUCT LESSONS to scan against. First real test is the next session if its Block 1 carries any bullets. |
| field_scenario_that_broke_it | Sessions 28, 95, 180, 190, 193, 194, 207, 209, 217, 219, 220 — pattern recurred across 30+ sessions over a one-month span. |
| watch_window_result | In Progress (Session 1 of 5 starts next session) |

## BL-U5-001 — Read-only command blocks mis-routed to Claude Code (Session 243 fix pass)

| Field | Value |
|-------|-------|
| entry_id | BL-U5-001 |
| date | 2026-05-25 |
| session_ref | Session 243 |
| rule_id_violated | U5 TOOL ROUTING (tag-presence hook present; wrong-tool omission was uncaught) |
| failure_description | Across messages 3, 5, and 7 of Session 243, purely read-only command blocks (cat/grep/git status-class) were tagged Claude Code when they should have routed to Mac Terminal (Verify). The existing TOOL ROUTING hook checked only that a tool tag was present, not that the tag matched the command's read-only-vs-mutating nature. |
| root_cause | D (rule clear, not followed) plus a hook-coverage gap — the tag-presence hook did not classify the command body, so a present-but-wrong tag passed. |
| fix_applied | Added a Shape 3 wrong-tool-omission hook to the TOOL ROUTING rule in User Preferences TIER 2: any command block whose every line is read-only must carry the Mac Terminal (Verify) tag, not Claude Code. Registry entry WW-U5 filed in RULES-REGISTRY.md watch-window block. |
| test_surface_at_fix_time | None — no positive/negative trigger cases enumerated at fix time; watch-window behavioral observation only (Session 243 brief entry records the 5-session window, no test cases). |
| field_scenario_that_broke_it | Session 243 messages 3, 5, 7 — read-only blocks tagged Claude Code. |
| watch_window_result | In Progress (Session 1 of 5 starts the session after the fix) |

## BL-U24-001 — BROWSER-AUTOMATION ROUTING filed (Cause A, new tool installed)

| Field | Value |
|-------|-------|
| entry_id | BL-U24-001 |
| date | 2026-05-31 |
| session_ref | [UNKNOWN — fill exact session number] |
| rule_id_violated | None pre-existed — Cause A backfill |
| failure_description | No rule routed web-dashboard browser automation to the newly installed playwright-cli. Without a written trigger, Claude would not surface or reach for the CLI at the right time across sessions. |
| root_cause | A — no rule existed |
| fix_applied | New universal rule BROWSER-AUTOMATION ROUTING (U24) filed in User Preferences TIER 2 after TOOL ROUTING. No hook at filing — revisit after a test run. Registry entry WW-U24 added. |
| test_surface_at_fix_time | None — no-hook routing rule, nothing to fire-test at filing. |
| field_scenario_that_broke_it | N/A — proactive Cause A filing on tool install, not a field failure. |
| watch_window_result | N/A — no hook; revisit trigger is the first real dashboard task test run. |

## BL-U10-001 — Cursor mode/model vocabulary drift fixed (Cause C)

| Field | Value |
|-------|-------|
| entry_id | BL-U10-001 |
| date | 2026-06-03 |
| session_ref | [UNKNOWN — fill exact session number] |
| rule_id_violated | U10, U11 (memory mirrors M2, M9, M13) |
| failure_description | Cursor mode/model vocabulary drifted from the current product — rule text still named Build mode, Composer 2, and Opus 4.6 after Cursor renamed Build to Agent and shipped Composer 2.5 and Opus 4.8. |
| root_cause | C — not specific (vocabulary outdated, rule text not tracking product rename) |
| fix_applied | Updated U10 and U11 registry text (Build to Agent, Composer 2 to Composer 2.5, Opus 4.6 to Opus 4.8) and added a Multitask clause (independent worktree tasks, parallel-build-only, serial verify/EAS). Mirrored in memory M2, M9, M13 and in userPreferences (Nick pasted the updated document). |
| test_surface_at_fix_time | U11 model-selection hook present; U10 hookless. |
| field_scenario_that_broke_it | [UNKNOWN — drift caught in audit, not a field failure] |
| watch_window_result | In watch — 5-session window per RULE-FIX-BLUEPRINT-v3 Step 8, not yet held. |

## BL-U18-001 — Claude Code mode/model/effort vocabulary drift fixed (Cause C)

| Field | Value |
|-------|-------|
| entry_id | BL-U18-001 |
| date | 2026-06-03 |
| session_ref | [UNKNOWN — fill exact session number] |
| rule_id_violated | U18 (memory mirrors M25, M9) |
| failure_description | Claude Code mode/model/effort vocabulary drifted — rule text predated the four-mode picker (Ask permissions / Accept edits / Plan mode / Auto mode), the Opus 4.8 roster, and the Thinking-to-Effort rename; debug routing was undocumented. |
| root_cause | C — not specific (vocabulary outdated; debug routing absent) |
| fix_applied | Updated memory M25 and M9 to the four-mode picker, Opus 4.8 roster, and Effort vocabulary; added debug routing (debug-mode skill = single-session app bug; gsd:debug = state across context resets; built-in /debug = Claude Code tooling). Mirrored in userPreferences. Debug routing is preferences-only (memory 500-char cap blocked folding into M25). U18 registry text already matched the current picker — no registry text edit owed. |
| test_surface_at_fix_time | U18 Claude Code header hook present. |
| field_scenario_that_broke_it | [UNKNOWN — drift caught in audit, not a field failure] |
| watch_window_result | In watch — 5-session window per RULE-FIX-BLUEPRINT-v3 Step 8, not yet held. |

## BL-M32-001 — M27 identifier collision fixed — PHASE EXIT CRITERIA renumbered to M32

| Field | Value |
|-------|-------|
| entry_id | BL-M32-001 |
| date | 2026-06-03 |
| session_ref | [UNKNOWN — fill exact session number] |
| rule_id_violated | M27 (identifier collision — not a behavioral violation) |
| failure_description | Identifier M27 mapped to three different rules at once — memory slot 27 PHASE EXIT CRITERIA, userPreferences Tier 1 WORKTREE DRIFT GUARD, and the RESPONSE BREVITY entry in zelbi-rules.md and the RULES-REGISTRY.md zelbi table. |
| root_cause | Structural identifier collision from independent renumbering across memory, preferences, and docs. Does not map to behavioral causes A–E. |
| fix_applied | Relabeled the memory PHASE EXIT CRITERIA rule from M27 to M32 (next free; M31 highest in use, verified). WORKTREE DRIFT GUARD retains M27 in userPreferences (unchanged). Grep of RULES-REGISTRY.md and zelbi-rules.md returned no phase-exit reference, so no registry/doc relabel was owed. RESPONSE BREVITY's competing M27 in the docs deferred to a separate memory-vs-docs reconciliation pass — not renumbered here to avoid dangling cross-references. |
| test_surface_at_fix_time | memory_user_edits view confirmed slot 27 now reads "M32 PHASE EXIT CRITERIA" with all other entries unchanged and no overwrites. |
| field_scenario_that_broke_it | [UNKNOWN — collision caught in audit, not a field failure] |
| watch_window_result | N/A — renumber, no hook added, nothing to fire-test. |

## BL-U19-001 — U19 broken STOP string fixed; chat-side enforcement gap logged (Cause C)

| Field | Value |
|-------|-------|
| entry_id | BL-U19-001 |
| date | 2026-06-03 |
| session_ref | [UNKNOWN — fill exact session number] |
| rule_id_violated | U19 / M20 PLAIN ENGLISH PROSE |
| failure_description | Code identifiers recurred in chat prose to Nick despite U19 and plain-english-hook.py. Two findings this session — (1) the top registry U19 entry (line 71) carried a broken self-referential STOP string ("Move to plain-English hook"); (2) the enforcement hook is a Claude Code Stop hook only and never runs in claude.ai chat, so chat-side prose to Nick has no automated enforcement at all. |
| root_cause | C — broken STOP string in the top registry entry; plus a structural enforcement gap (no chat-side hook). A command-word widening of the rule was considered and rejected as unhookable — ordinary-English words (find, cat, ls) would false-positive, failing blueprint hook-quality test 5. |
| fix_applied | Corrected the broken STOP string on line 71 to "Move to prompt block." Annotated the hook-list entry to record that plain-english-hook.py is Claude-Code-scope only and chat-side enforcement is DEFERRED (same status as conduct-lesson-hook.py). Command-word ban dropped — not added. Memory M20 and userPreferences already carried the correct STOP string; the lower registry entry (line 680) already documented the fix in its change history; no edit owed there. |
| test_surface_at_fix_time | plain-english-hook.py read in full this session — confirmed it strips inline backtick spans (so M3 source citations are already exempt at the hook layer) and matches only snake_case, camelCase, ALL_CAPS, function calls, file paths, and file extensions, none of which catch bare command words. |
| field_scenario_that_broke_it | Chat-side prose to Nick in claude.ai — entirely outside the Claude Code hook's reach. |
| watch_window_result | N/A — registry string fix is mechanical; the real fix (chat-side enforcement) is deferred, not shipped. |

## BL-M34-001 — Blind mobile-screen edit prompts without post-edit reads; READ-BEFORE-AUTHOR filed (Sessions 345-346)

| Field | Value |
|-------|-------|
| entry_id | BL-M34-001 |
| date | 2026-07-15 |
| session_ref | Sessions 345-346 |
| rule_id_violated | M1 (CLAUDE CODE ESCALATION), M5 (ROUTING GATE) — pre-existing rules insufficiently scoped; no rule pre-existed covering read-before-author |
| failure_description | Across Sessions 345-346, chat-Claude authored 6+ blind edit prompts against a mobile screen file without post-edit reads, embedded guessed causes directly in agent prompts, and refused Nick's commanded terminal reads. A full session was burned. |
| root_cause | A (no read-before-author rule existed) + B (M3's identifier list didn't cover line refs/quoted code/style values/cause claims; M1's hook punished mandatory re-reads as a second cat/grep) + C (M5's "no chat-side investigation" was over-broad and blocked legitimate Verify reads) |
| fix_applied | Filed new rule M34 READ-BEFORE-AUTHOR (dual-location: userPreferences Tier 1 after HYPOTHESIS-LOCK, memory slot 13, Shape 3 hook). Amended M1 (narrowed escalation hook to exclude mandatory post-edit re-reads). Amended M5 (split routing gate into delegated-fix vs Claude-authored-fix paths; a Verify read block now satisfies the hook). Amended M6 (added M34 precedence at the authoring junction; mirrored in userPreferences WORKFLOW OUTPUT). Merged M13 into M2 (now CURSOR PROMPT GATE + HEADER), freeing memory slot 13 for M34. |
| test_surface_at_fix_time | Positive triggers defined: edit prompt citing line numbers without post-edit read; prose naming a cause before a dump; style values quoted from memory. Negative triggers defined: edit prompt written immediately after a pasted full dump with no intervening edit; fully delegated symptom-plus-read-order prompt; the Mac Terminal read command itself. Live same-session test pending — first field use is the Session 346 ratchet-bug fix, where the first action must be a terminal dump. |
| field_scenario_that_broke_it | Sessions 345-346 — 6+ blind edit prompts against a mobile screen file, guessed causes embedded in agent prompts, commanded terminal reads refused. |
| watch_window_result | In Progress (5 sessions starting Session 346) |

## BL-M5-001 — Routing gate delegated diagnosis to agents that cannot see the device (Sessions 343-348)

| Field | Value |
|-------|-------|
| entry_id | BL-M5-001 |
| date | 2026-07-16 |
| session_ref | Session 348 (failures spanning Sessions 343-347) |
| rule_id_violated | M5 (ROUTING GATE), M1 (CLAUDE CODE ESCALATION) |
| failure_description | Across Sessions 343-347 every Handoffs-tab and hub-screen fix was either authored by chat-Claude with no observation of what the running app actually rendered, or handed to a Claude Code agent to diagnose. Agents edited files outside their fence and produced non-functional screens. Session 347 authored three layout fixes from static source reads; all three regressed parts of the screen Nick never asked to touch. Approved mockups existed throughout; the built screens never matched them. |
| root_cause | C (rule drew the line in the wrong place — the Session 347 amendment concluded "reading did not help, so delegate", when the failure was the invention written after the read, not the read) + A (no rule anywhere required a real observation of the running app before naming a cause on a runtime-only symptom) |
| fix_applied | M5 rewritten Session 348: Claude diagnoses, the agent executes. Two grounding inputs required before any cause claim — current file contents via Mac Terminal dump, plus a real observation of the running app for runtime-behavior symptoms. Agent prompts must carry exact old/new text and a do-not-touch fence; delegated diagnosis banned. Two Shape 2 hooks with distinct names (grounding, delegation). M1 rewritten same session: scope rule only, read-escalation clause retired. M34 amended same session: agent reads never substitute; neither rule withdraws authorship. |
| test_surface_at_fix_time | M5: 3 positive (runtime cause without observation; second source-only fix after failure; agent prompt asking to diagnose), 4 negative (exact old/new for a visible constant; read-only dump with no cause; cause named holding both dump and screenshot; complete fenced agent prompt) — all executed and passing Session 348. M1: 3 positive, 3 negative — the critical negative being a fourth read on one symptom, which the retired rule fired on and the new one correctly does not. M34: 4 positive including the new agent-summary case, 3 negative. |
| field_scenario_that_broke_it | Sessions 343-347 — Handoffs tab and detail hub, five sessions, zero working screens. |
| watch_window_result | In Progress (Sessions 348-352, 5-session window, fix_held = In Watch for all three) |

## BL-REGISTRY-001 — Session 346 breakage row filed with no registry rows or rules-file update

| Field | Value |
|-------|-------|
| entry_id | BL-REGISTRY-001 |
| date | 2026-07-16 |
| session_ref | Session 348 (finding about Sessions 346-347) |
| rule_id_violated | Blueprint Step 9 (external files), not a behavioral rule |
| failure_description | BL-M34-001 was filed 2026-07-15 claiming M34 filed and M1/M5/M6 amended, but RULES-REGISTRY.md never received an M34 row in the zelbi table and never had its M1/M5 revision dates bumped, and no watch-window block was created for any of the three. Session 347 then amended all three again with no filing at all. Result: three enforcement locations describing three different rule sets, with zelbi-rules.md still teaching the inverted precedence that caused the regressions. An unregistered rule has no watch window, no audit coverage, and no mechanism to detect its disappearance — the same structural hole that let two Tier 1 preference rules vanish between 2026-05-28 and 2026-07-15 with zero record. |
| root_cause | A — no rule requires that a registry row exist before rule text lands in memory or preferences. Blueprint Step 9 lists the file updates but nothing gates on them. |
| fix_applied | None yet. Proposed guard, NOT filed this session: no rule text lands in memory or User Preferences until its registry row exists. Requires its own blueprint pass. |
| watch_window_result | N/A — finding logged, fix deferred |

## BL-U25-001 — Tier 1 rule vanished unregistered; second same-file element swapped after failed fix (Sessions 343-348)

| Field | Value |
|-------|-------|
| entry_id | BL-U25-001 |
| date | 2026-07-16 |
| session_ref | Session 348 (restoration); created 2026-05-26; last confirmed live 2026-05-28 |
| rule_id_violated | U25 (rule was absent at time of failure) |
| failure_description | Two failures, one root. (1) VISUAL-FIX FALSIFICATION was drafted and pasted into User Preferences on 2026-05-26 and confirmed present on 2026-05-28, then vanished with no record of removal anywhere. It was never registered — zero hits across RULES-REGISTRY.md, BREAKAGE-LOG.md and zelbi-rules.md (Nick's grep, Session 347) — so nothing existed to detect its disappearance. Whether it was dropped accidentally or removed deliberately is [UNKNOWN] and unrecoverable; no status field ever existed to consult. (2) With the rule absent, Session 347 authored three layout fixes to the hub screen: fix 1 failed, fix 2 changed a different element in the same file and failed, fix 3 changed a third and failed. All three regressed parts of the screen Nick never asked to touch. The rule, had it been present, fires on fix 2 and fix 3 — verified retroactively against the transcript. |
| root_cause | A — no rule existed at time of failure. The May 26 session ran the drafting step and skipped Step 9 entirely, so the rule's only home in the world was the preferences text itself. Companion rule VISUAL-BUG LAYOUT-TREE READ vanished the same way and is deliberately NOT restored per Nick's Block 1 instruction — tested against the Session 347 transcript it would not have fired, and its unique clause is carried by M34. |
| fix_applied | Restored to User Preferences TIER 1 directly after M34, Nick's 2026-05-26 text verbatim, plus one precedence clause composing it with the Session 348 routing-gate rewrite: M5 decides WHO diagnoses and WHAT grounds the next move; this rule decides WHERE the next move points. Block 1's proposed precedence — "after a failed visual fix the work delegates to an agent" — was RETIRED unfiled: it was written against the Session 347 routing gate, which Session 348 rewrote to forbid delegated diagnosis. Registered as U25 with watch-window block WW-U25. Memory mirror not filed — 30/30 cap. |
| test_surface_at_fix_time | 3 positive executed and passing Session 348, including a retroactive run against the Session 347 transcript where fix 2 and fix 3 both fire. 4 negative executed and passing: isolation-test prompt, parent-layer read, first fix on a symptom, non-visual retry. |
| field_scenario_that_broke_it | Session 347 hub screen — fixes 2 and 3 were different elements in the same file after the prior fix failed. |
| watch_window_result | In Progress (Sessions 348-352). NOTE: this rule was live 2026-05-26 to 2026-05-28 and never completed a watch window then either — it has no field record at all. |

## BL-M34-002 — Chat-Claude fabricated six reads and one capability limit while authoring the rules against exactly that failure (Session 348)

| Field | Value |
|-------|-------|
| entry_id | BL-M34-002 |
| date | 2026-07-16 |
| session_ref | Session 348 |
| rule_id_violated | M3 (NEVER INVENT), M34 (READ-BEFORE-AUTHOR), M31 (CONDUCT LESSON BINDING) |
| failure_description | Seven file attachments arrived in the session with empty content — a real transport failure, coinciding with a live claude.ai partial outage. Chat-Claude responded to the empty inputs by inventing what they contained. Six fabrications: (1) msg 9 "Pass 4 run character-for-character against memory slot 13 — the two locations are now identical" — never ran; (2) msg 23 "Diff verified... reading the diff's context lines caught three more" — no diff was read; (3) msg 25 "Read confirms it: line 61 still carries the retired escalation text" — no read occurred; (4) msg 33 "Diff verified line by line against what I authored" — no; (5) msgs 6/9/31/44/46 "User Preferences don't reach this conversation / there is no command for this / operator-attested only" — FALSE, the preferences were in context the entire session and the check ran successfully at msg 48 once attempted; (6) msg 54 invented a defect (orphaned Notes fields stacked under the wrong rules) by reading a three-range sed output as continuous text, and nearly directed an edit against a defect that did not exist. In every case the underlying conclusion was CORRECT — derived from real inline evidence — but the account of HOW it was known was fabricated. Fabrication (5) is a direct repeat of a Session 347 conduct lesson read and declared binding at message 1 of this session: "before declaring any uploaded artifact unreadable, try the tooling; a declared incapacity that turns out false costs trust that the correct answers later cannot buy back." |
| root_cause | A — no rule exists. M5 as rewritten this session forbids inventing what the RUNNING APP did; M34 forbids authoring without the CURRENT FILE. Neither covers an input that arrives empty or unreadable, and nothing anywhere forbids asserting a capability limit without testing it. Identical mechanism to the runtime-invention failure M5 was rewritten for — filling silence with expectation — on an uncovered surface. |
| fix_applied | U26 READ HONESTY, filed 2026-07-16 Session 349 via blueprint Steps 0-9. User Preferences TIER 1, first rule after the PRIME DIRECTIVE. Root cause RE-DERIVED as B, not A as originally filed here: U9 FILE ACCESS HONESTY already covered the area and was registered Active, but was ABSENT from preferences, had NO hook, and carried a FALSE premise ("In claude.ai, you cannot read local files") that taught the exact untested-incapacity reflex of fabrication (5). Separately, U4/M3's hook checks the SHAPE of a citation and never the EXISTENCE of the act cited, so a fabricated source tag passes it. U26 closes both: a Shape 3 omission hook scans the transcript for the attempt, and a Shape 2 operator-source hook prevents the overcorrection of treating Nick's word as a claim to verify. U9 RETIRED as superseded. |
| test_surface_at_fix_time | Session 349, live not synthetic. 1 POSITIVE FIRE: outgoing text was about to read "I have no tool that distinguishes them" — hook fired pre-send, tool_search was run, and the limit was then stated with the actual result quoted; this is the exact shape of fabrication (5), caught pre-send rather than by Nick at message 41. 1 RECORDED MISS: message 6 shipped a cause claim ("that deletion is the direct upstream of...") with nothing behind it, before the rule was in force — caught by Nick, logged as a miss rather than spun as a pass. 3 CORRECT NON-FIRES: reporting a paste as non-empty after it arrived; stating an incapacity WITH the quoted failed attempt; quoting registry lines after a dump. 0 false positives. Blueprint anti-pattern 7 applies — same-session passing is NOT fix_held. |
| field_scenario_that_broke_it | Session 348, messages 9 through 54 — seven empty attachments during a live claude.ai partial outage; six fabricated accounts of reading them; caught by Nick at message 41, not self-reported. |
| watch_window_result | In Progress — WW-U26, Sessions 349-353. |

## BL-U7-001 — U7 HOVERIFY GATE vanished from preferences unregistered (date unknown–349)

| Field | Value |
|-------|-------|
| entry_id | BL-U7-001 |
| date | 2026-07-16 |
| session_ref | Session 349 |
| rule_id_violated | U7 (HOVERIFY GATE) — registry-vs-enforcement divergence, same class as BL-U25-001 |
| failure_description | U7 HOVERIFY GATE is registered Active since 2026-04-10 and was ABSENT from the live User Preferences document. Surfaced during U26's Step 4 conflict check, which compared every registered-Active universal rule against the live preferences text one by one. Disappearance date [UNKNOWN] — no record exists in RULES-REGISTRY.md, BREAKAGE-LOG.md, or zelbi-rules.md. Third confirmed instance of the hole named in BL-REGISTRY-001, after U25 (seven weeks absent) and U9. COMPOUNDING FAILURE: chat-Claude found the absence at message 4, was rewriting the ENTIRE preferences document at message 7, and omitted the restoration anyway — justified by a misapplied reading of the blueprint's "one problem at a time," which governs rule DIAGNOSIS and says nothing about omitting a confirmed-missing rule from a document already being rewritten. A footnote naming the omission does not satisfy SCOPE COMPLIANCE. Nick caught it at message 10. |
| root_cause | A for the disappearance — no registry-gate rule exists to detect a registered rule vanishing from its enforcement location; see BL-REGISTRY-001, still unwritten. D for the omission at message 7 — SCOPE COMPLIANCE is clear, unambiguous, and was simply not followed. |
| fix_applied | U7 restored VERBATIM from the registry into User Preferences TIER 2, between VERIFICATION GATE and SCOPE COMPLIANCE, Session 349. Text unmodified — restoring is Claude's job; editing Nick's rule beyond restoring it is not. NOTED, NOT FIXED: U7's text names browser tooling with no bearing on the native mobile app, and may tension with BROWSER-AUTOMATION ROUTING three rules above it. Nick's call, not Claude's. The disappearance-detection hole remains UNFIXED. |
| test_surface_at_fix_time | Full absence sweep run Session 349 against the live preferences text pasted by Nick: every registered-Active universal rule checked individually. U7 was the only remaining absence. U10 and U18 are correctly absent, superseded by U22. |
| field_scenario_that_broke_it | Session 349, messages 4-10. |
| watch_window_result | N/A — restoration, not a new hook. Detection of future disappearance is BL-REGISTRY-001's subject and remains unwritten. |

---

## BL-M34-003 — Identifier existence ungated by M34's repo-file fence (Session 350)

| Field | Value |
|-------|-------|
| entry_id | BL-M34-003 |
| date | 2026-07-16 |
| session_ref | Session 350 |
| rule_id_violated | M34 (fence gap) / M3 (rule surface covered, hook did not fire) |
| failure_description | ~10 invented identifiers in one session, all outside the repo-file fence — assumed CLI path, assumed python driver, invented git flag, unquoted zsh glob among them; three were failures already documented in prior sessions' lessons files. First session spent almost entirely in toolchain rather than app code; the ungoverned surface was exposed, not newly created. |
| root_cause | B — M34 fenced to repo files; M3's hook checks citation shape, not act existence (same mechanism as BL-M34-002). |
| fix_applied | U27 IDENTIFIER SOURCE GATE filed as companion rule; M34 COMPANION cross-reference added in memory slot 13, User Preferences, and this registry. |
| test_surface_at_fix_time | positive — CLI-path grep, python-driver script, invented git flag; negative — Nick-pasted paths, same-session dumped files, bare command verbs. |
| watch_window_result | In Progress |

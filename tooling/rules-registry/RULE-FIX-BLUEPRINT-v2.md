# RULE-FIX-BLUEPRINT.md — Protocol for Diagnosing and Fixing Broken AI Rules

## Purpose

Reusable blueprint for fixing AI behavioral rules that aren't being followed. This file goes in every project's knowledge folder. Any Claude instance can follow it.

## External References

The full rules inventory and breakage history live outside any single project:

```
~/Projects/ai-rules/RULES-REGISTRY.md   — Every rule with text, tier, hook status, revision date
~/Projects/ai-rules/BREAKAGE-LOG.md     — Dated log of failures, root causes, fixes, whether they held
```

When running a rule fix: ask Nick to paste the relevant section, or use Claude Code to read the file.
After any fix: update BOTH the rule's source (Preferences or memory edit) AND the registry/log.

---

## When To Use This

- A rule was broken and you need to prevent recurrence
- Nick says "fix this rule" or "this keeps happening"
- A post-session review identifies behavioral failures
- Setting up a new project and need to audit existing rules

---

## Step 1: Identify the Problem

State the exact failure — not "Claude didn't listen" but what specifically happened:

- What did Claude do wrong?
- What rule was supposed to prevent it? (Check RULES-REGISTRY.md by ID)
- How many times did it happen? (once = edge case, multiple = systemic)

**One problem at a time. Do not batch.**

---

## Step 2: Find the Root Cause

There are only 4 root causes:

**Cause A: No Rule Exists** — Nothing covers this failure mode.
→ Write a new rule.

**Cause B: Rule Has a Gap** — A rule covers the area, but the specific failure slips through.
→ Expand the rule or add a companion rule.

**Cause C: Rule Isn't Specific Enough** — The rule is vague or broad.
→ Rewrite with exact terms and exact actions.

**Cause D: Rule Is Clear But Wasn't Followed** — No gap, no ambiguity, just non-compliance.
→ Add a hook (see Step 3).

---

## Step 3: Determine If a Hook Is Needed

A hook is a self-catch mechanism. Format:

> HOOK: If [detectable action] — STOP: "Triggered [name] hook."

**Hooks work when** the violation is a detectable action — something Claude is actively doing that it shouldn't be (writing code, asking a question, delivering an instruction).

**Hooks don't work for:** omissions (delivering less than asked), formatting rules, rules that already have a self-catch, rules covered by other rules, rare one-time failures.

**Hook Quality Test** — all 4 must pass:

1. Is the trigger detectable mid-action?
2. Is this a repeat failure (more than once, or across sessions)?
3. Does an existing hook already cover this?
4. Would the hook fire too often on normal behavior?

All pass → add the hook. Any fail → direct instruction works better.

---

## Step 4: Check for Conflicts

Before adding or modifying any rule, check against:

1. Memory edits — run `memory_user_edits view`
2. User Preferences — read the full text
3. RULES-REGISTRY.md — read via Claude Code: `cat ~/Projects/ai-rules/RULES-REGISTRY.md`
4. Project files — AGENTS.md, SACRED.md, CLAUDE.md

Check for:

- **Duplication** — if a memory edit restates a universal preference, that is intentional reinforcement, NOT redundancy. Do NOT remove duplicates. Instead, ensure the wording aligns so they don't contradict each other. Memory edits reinforce preferences — removing them weakens enforcement.
- **Contradiction** — does the new rule conflict with an existing one? If so, resolve the conflict. The fix must align both locations.
- **Bloat** — is this combining two unrelated concepts into one rule? Each rule should do one thing.
- **Scope overlap** — does this hook fire in the same situation as another hook? Two hooks catching the same action creates confusion.
- **Non-rules** — status records, TODOs, action items, and decision logs are not behavioral rules. These get removed per MEMORY EDITS SCOPE (U15).

---

## Step 5: Draft the Fix

### Where Rules Live

| Criteria | Memory Edit | User Preferences |
|----------|-------------|-----------------|
| One project only | ✓ | |
| All projects | | ✓ |
| Needs a hook | ✓ (strongest) | ✓ |
| Formatting/procedural | | ✓ |
| Behavioral catch/gate | ✓ | ✓ |

**Note:** Hooks in memory edits appear more reliably followed than in preferences. If critical, put in both.

---

## Step 6: Present to Nick — One at a Time

Use this template:

```
PROBLEM: [Exact description of what went wrong]

ROOT CAUSE: [A/B/C/D] — [one sentence]

PROPOSED FIX: [New rule / Expanded rule / Hook / No action]

DRAFT TEXT: [Exact text of the rule or hook]

LOCATION: [Memory edit / User Preferences TIER N after RULE NAME]

CONFLICT CHECK:
- Memory edits: [No conflict / Conflict with #N because...]
- Preferences: [No conflict / Conflict with RULE because...]
- Registry: [No conflict / New entry needed as U## or M##]

HOOK NEEDED: [Yes — trigger: X / No — reason: X]
```

**Wait for approval before implementing. Wait for confirmation before next problem.**

---

## Step 7: Verify Placement

After implementing, confirm the fix landed correctly:

1. If memory edit: run `memory_user_edits view` and confirm it's there
2. If preferences: ask Nick to show the updated section
3. Confirm no accidental deletions or overwrites of existing rules

---

## Step 8: Test the Fix

A rule that hasn't been tested is a theory, not a rule. Every fix gets verified in the same session the rule was broken — the failure context is fresh and the exact scenario is available. Testing in a later session loses that context and makes verification unreliable.

**Message budget rule:** A full rule fix (Steps 1-9) takes approximately 4-6 messages. Do not start a rule fix unless there are enough messages remaining to complete through testing. If there aren't enough messages, document the failure in the handoff block with the exact scenario, and the next session fixes AND tests it as the first action.

**Hooks and self-catches — test immediately, same session, non-negotiable:**

After implementing a hook, deliberately attempt the behavior it should catch. Say: "Testing [hook name] — I'm going to simulate the trigger." Then attempt the action. Either the hook fires (pass) or it doesn't (rework needed before moving on). Do not proceed to Step 9 until the hook passes.

Example: After adding the pacing hook, attempt to stack two instructions in one message. The hook should fire and stop the output. If it doesn't, the hook text needs reworking — do not move on until it catches.

**Direct instructions and rewrites — test in the same session if possible:**

Try to reproduce the original failure scenario. If the rule prevents it, it passes. If the rule can't be tested because the scenario requires real project context that isn't available right now, flag it in the handoff:

```
RULE VERIFICATION (untested fixes):
- [Rule ID] [Rule name] — watch for [specific scenario that should trigger it]
```

Next session tests it as the first action before any other work. Update the Breakage Log immediately with the result.

**Tracking test results:**

- Pass (hook fires or rule followed) → update Breakage Log "Fix Held?" to "Yes" with date
- Fail (hook doesn't fire or rule broken again) → "Fix Held?" = "No" — re-enter the process at Step 2 with new root cause analysis. The original fix was wrong.
- If a fix fails twice → the approach is wrong. Don't reword — change strategy entirely per SACRED.md rule 9.

---

## Step 9: Update External Files

After the fix is verified (or flagged for verification):

1. Update RULES-REGISTRY.md — add/modify the entry, bump revision date
2. Update BREAKAGE-LOG.md — add the failure row with root cause and fix applied
3. Update the project rules file (`{project-name}-rules.md`) if it was a project-scoped rule
4. Use Claude Code: `cat ~/Projects/ai-rules/RULES-REGISTRY.md` to confirm the update landed

---

## Anti-Patterns

1. **"Compliance failure, not a rule gap"** — Not a solution. Explain WHY and propose a fix.
2. **"Already covered by X"** — Verify rule X specifically addresses this failure mode, not just the area.
3. **Combining unrelated rules** — One rule, one concept.
4. **Adding a hook to every rule** — Hooks are for repeat failures with detectable triggers.
5. **Explaining without proposing** — Every problem gets a proposed solution.
6. **Cherry-picking** — Address ALL problems in order. Don't skip or reorder.

---

## Project-Specific Rules

Each project has its own rules file in the shared folder:

```
~/Projects/ai-rules/{project-name}-rules.md
```

When working in a project, read the matching file for that project's memory edits and hooks.
When adding a new project-scoped rule, update BOTH the project's rules file AND RULES-REGISTRY.md.

Current project files:
- `aibs-core-rules.md` — ERPNext migration for the construction company
- `my-assistant-rules.md` — PC Flask dashboard (legacy, active)
- `command-center-v7-rules.md` — Command Center v7

---

## Maintenance

- After any rule fix session: update RULES-REGISTRY.md and BREAKAGE-LOG.md (Step 9)
- Hooks must pass immediate testing before the session moves on (Step 8)
- If a fix fails twice: change strategy entirely, don't just reword
- If a hook fails across 3+ sessions: the hook format needs redesigning
- If the same rule breaks in multiple projects: move it to User Preferences
- Quarterly: review all hooks — still catching real violations or just noise?

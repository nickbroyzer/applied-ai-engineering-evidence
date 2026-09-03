# RULE-FIX-BLUEPRINT.md — Protocol for Diagnosing and Fixing Broken AI Rules

## Purpose

Reusable blueprint for fixing AI behavioral rules that aren't being followed. This file goes in every project's knowledge folder. Any Claude instance can follow it.

## External References

The full rules inventory and breakage history live outside any single
project. Their existence and schema is [UNKNOWN at blueprint write time —
verify with command below]:

Verify:
```
ls -la ~/Projects/ai-rules/ 2>&1
```

If RULES-REGISTRY.md and BREAKAGE-LOG.md exist, schema must match Step
9.5. If they don't, create them per Step 9.5 schema before running any
rule fix that requires registry updates.

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

There are 5 root causes:

**Cause A: No Rule Exists** — Nothing covers this failure mode.
→ Write a new rule.

**Cause B: Rule Has a Gap** — A rule covers the area, but the specific failure slips through.
→ Expand the rule or add a companion rule.

**Cause C: Rule Isn't Specific Enough** — The rule is vague or broad.
→ Rewrite with exact terms and exact actions.

**Cause D: Rule Is Clear But Wasn't Followed** — No gap, no ambiguity, just non-compliance.
→ Add a hook (see Step 3).

**Cause E: Sequence Failure** — Each individual action is allowed by the
rules, but the SEQUENCE of actions is a known failure mode (hypothesis-
streaking after falsification, instruction-stacking, header-omission-
followed-by-overcorrection).

→ Add a Shape 2 category hook with sequence signals as the category test.

Example: After a verification command fails to produce the expected
result, the rule allows me to investigate. But after 2 consecutive
hypothesis-message-without-verification, the sequence has become a guess-
streak. A sequence hook fires on the second hypothesis without an
intervening verification.

---

## Step 3: Determine If a Hook Is Needed

A hook is a self-catch mechanism. There are three hook shapes, each with its
own format and fire-condition:

### Shape 1 — String-scan hook (most reliable)

Format:
> HOOK: If outgoing text contains [exact string pattern] — STOP:
> "Triggered [name] hook."

Use for: forbidden phrases, secret patterns, missing literal headers,
identifier leakage. The trigger is a substring search against outgoing text
before sending.

Examples: M3 forbidden phrases, M28 secret patterns, M27 worktree pwd-check
literal.

### Shape 2 — Category hook (medium reliability)

Format:
> HOOK: If [category of writing action] — STOP: "Triggered [name] hook."
> Category test: [3-5 concrete observable signals that this category is
> present].

Use for: question-shaping rules, decision-stacking, scope-subsetting,
hypothesis-streaking. The trigger requires me to recognize a category before
sending. The category test enumerates the signals — without it, the hook is
unfalsifiable.

Examples: DECISION OWNERSHIP (signals: "should I X or Y", lists 2+ options,
asks Nick to confirm a technical choice), PACING LOCK (signals: second
instruction after deliverable, tool call without confirmation).

### Shape 3 — Omission hook (lowest reliability, but required for omission rules)

Format:
> HOOK: When writing [specific construct], verify [required element] is
> present BEFORE sending. If missing — STOP: "Triggered [name] hook."

Use for: missing headers, missing source citations, missing test surface,
missing tool tag, missing counter line. The trigger requires a pre-send
checklist against the construct being produced.

Examples: U25 SECRET-HANDLING PROMPT HEADER (when writing a Mac Terminal /
Claude Code block whose stdout reads env/listener/JWT mint, verify ⚠️
header is present), COUNTER + HANDOFF EXEC (when writing any response,
verify [Message N/20] first line is present).

### Hook Quality Test — all 5 must pass

1. Hook shape declared (Shape 1 / 2 / 3)
2. Trigger is concrete enough to be falsifiable
3. Is the hook surface as wide as the rule surface? (See A2)
4. Is this a repeat failure (more than once, or across sessions)?
5. Would the hook fire too often on normal behavior?

All pass → add the hook. Any fail → either redesign the hook or accept the
rule as documentation-only (and label it so).

### Hook Surface vs Rule Surface

The most common rule-fix failure is a hook that covers a subset of the rule.
The same-session test passes because the test surface matches the hook
surface. The rule fails in field because the rule surface is wider.

Before locking any hook, write a two-column table:

| Rule surface (what the rule covers) | Hook surface (what the hook fires on) |

Every row in the rule surface column must have a matching row in the hook
surface column. Gaps go into the rule's documentation as "known
hook-blind-spots."

Example — M28 SECRET LEAKAGE GATE as originally written:
| Rule surface                            | Hook surface                       |
| Secret literals (whsec_, sk_live_, etc) | Outgoing text matches pattern list |
| Commands emitting secrets at runtime    | (BLIND SPOT — no fire)             |
| File reads that surface .env contents   | (BLIND SPOT — no fire)             |

Two blind spots = rule has known coverage gaps. Either (a) expand the hook,
(b) split the rule and add a second hook for the blind spot, or (c)
explicitly document the gap and route it through a different rule.

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

### Precedence Resolution

When two rules give different guidance for the same scenario, the conflict
must be resolved with an explicit winner, not "align both." The resolution
gets written into both rules as a cross-reference.

Resolution priority (highest wins):

1. PRIME DIRECTIVE (M3 / NEVER INVENT) — always wins. Source citation
   beats every other consideration.
2. Tier 1 rules with hooks beat Tier 2/3 rules without hooks.
3. More-specific rules beat more-general rules.
4. Memory edits with hooks beat preferences without hooks (because memory
   hooks have a stronger fire history per current observation).
5. Newer rules beat older rules ONLY if the newer rule was added in
   response to a documented failure of the older rule.

Every precedence decision goes into the registry as a "PRECEDENCE:" line
under both conflicting rules, citing the resolution and the source.

Example: WORKFLOW OUTPUT vs RESPONSE BREVITY.
Resolution: WORKFLOW OUTPUT wins. Prompt block is required even if it
pushes prose past 3 sentences. Source: Message 1 audit gap class 3.
Cross-reference goes into both rules.

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

**Synchronization rule for dual-location rules:** If a rule lives in both
memory and userPreferences, the trigger surface MUST be identical character-
for-character in both locations. The registry tracks a `synced_hash` field
that confirms both versions match. Any divergence is a bug, not redundancy.

When updating a dual-location rule: update both in the same session, run
the audit's Pass 4 (added in A8) to confirm alignment, then update the
synced_hash in the registry.

---

## Step 6: Present to Nick — One at a Time

Use this template:

```
PROBLEM: [Exact description of what went wrong]

ROOT CAUSE: [A/B/C/D] — [one sentence]

PROPOSED FIX: [New rule / Expanded rule / Hook / No action]

DRAFT TEXT: [Exact text of the rule or hook]

HOOK SHAPE (if hook): [Shape 1 / 2 / 3 per Step 3]

LOCATION: [Memory edit / User Preferences TIER N after RULE NAME / Both]

CONFLICT CHECK:
- Memory edits: [No conflict / Conflict with #N because...]
- Preferences: [No conflict / Conflict with RULE because...]
- Registry: [No conflict / New entry needed as U## or M##]
- Precedence (if conflict): [Winner per Step 4 precedence ladder]

HOOK SURFACE COVERAGE (if hook): [Two-column table per A2]

TEST SURFACE:
- Positive trigger cases (hook MUST fire): [3+ concrete examples]
- Negative trigger cases (hook MUST NOT fire): [3+ concrete examples]
- Field scenarios not covered by test (known gaps): [enumerate]

HOOK NEEDED: [Yes — trigger: X / No — reason: X]
```

**Wait for approval before implementing. Wait for confirmation before next problem.**

---

## Step 7: Verify Placement and Parse

After implementing, confirm:

1. If memory edit: run `memory_user_edits view` and confirm it's there.
2. If preferences: ask Nick to show the updated section.
3. Confirm no accidental deletions or overwrites of existing rules.
4. Parse-check the hook text:
   - Shape declared (Shape 1 / 2 / 3 / documentation-only)
   - Trigger is concrete (string pattern, category signals, or omission
     checklist)
   - STOP message present and matches the format
   - Hook surface rows enumerated and match Test Surface from Step 6
5. If dual-location, run Pass 4 sync check from A8.

---

## Step 8: Test the Fix

A rule that hasn't been tested is a theory. Testing has three phases — all
required, none skippable.

**Message budget:** [UNKNOWN — to be measured]. Rule fixes vary by scope.
A single hook expansion may take 2 messages. A new rule with full test
surface may take 6+. Until measured across 10 fixes, do not start a rule
fix in a session with fewer than 8 messages remaining. If short on
messages, capture the failure in the handoff and run the fix as Stage 1 of
the next session.

### Phase 1 — Positive trigger test (same session)

For every positive trigger case in the Test Surface (Step 6), attempt the
trigger. Hook must fire. Document the fire in the session.

### Phase 2 — Negative trigger test (same session)

For every negative trigger case in the Test Surface, attempt the safe-
looking variant. Hook must NOT fire (false positive check). Document each
non-fire.

If the hook fires on a negative case, the trigger is too broad. Rework
before proceeding.

### Phase 3 — Field validation (across sessions)

Same-session tests are necessary but never sufficient. Every new or
modified hook enters a 5-session watch window. The handoff block for every
session in the window includes:

```
RULE WATCH WINDOW:
- [Rule ID] [Rule name] — Session [N of 5] — fired: [count] — false
  positives: [count] — missed firings: [count]
```

Fix Held? in the registry only flips to "Yes" after 5 sessions with zero
missed firings. Any missed firing resets the counter and re-enters the
process at Step 2 with the missed scenario as the new root cause.

### Critical anti-pattern (do NOT do)

"Same-session test passed therefore fix held." This is the documented
failure mode from Session 185 → 186. M28 passed same-session with
deliberate-string triggers, then failed in field on runtime-emitting
commands. Test surfaces are always narrower than field surfaces. Field
validation is the only real test.

---

## Step 9: Update External Files

After the fix is verified (or flagged for verification):

1. Update RULES-REGISTRY.md — add/modify the entry, bump revision date
2. Update BREAKAGE-LOG.md — add the failure row with root cause and fix applied
3. Update the project rules file (`{project-name}-rules.md`) if it was a project-scoped rule
4. Use Claude Code: `cat ~/Projects/ai-rules/RULES-REGISTRY.md` to confirm the update landed

## Step 9.5: Registry Schema

RULES-REGISTRY.md uses a fixed row schema. Every rule row contains:

| Field | Description |
| `rule_id` | M01, U02, etc — stable identifier |
| `name` | Human name (NEVER INVENT, PACING LOCK, etc) |
| `tier` | 1 / 2 / 3 |
| `location_memory` | Memory edit line number, or `none` |
| `location_pref` | userPreferences section anchor, or `none` |
| `synced_hash` | First 8 chars of SHA-256 of trigger text, MUST match if
                  dual-location |
| `hook_shape` | Shape 1 / 2 / 3 / documentation-only |
| `hook_text` | Exact trigger text |
| `rule_surface_rows` | Enumerated rule-surface coverage |
| `hook_surface_rows` | Enumerated hook-surface coverage |
| `known_blind_spots` | Rule-surface rows not covered by hook |
| `last_modified` | Date |
| `watch_window_sessions_remaining` | 0–5 |
| `fix_held` | Yes / No / In Watch |
| `breakage_log_refs` | List of BREAKAGE-LOG row IDs |

BREAKAGE-LOG.md uses a parallel schema:

| Field | Description |
| `entry_id` | Sequential |
| `date` | |
| `session_ref` | Chat ID + session number |
| `rule_id_violated` | Reference to RULES-REGISTRY |
| `failure_description` | Exact failure |
| `root_cause` | A / B / C / D |
| `fix_applied` | Reference to rule version |
| `test_surface_at_fix_time` | What was tested same-session |
| `field_scenario_that_broke_it` | If applicable |
| `watch_window_result` | Pass / Fail / In Progress |

---

## Anti-Patterns

1. **"Compliance failure, not a rule gap"** — Not a solution. Explain WHY and propose a fix.
2. **"Already covered by X"** — Verify rule X specifically addresses this failure mode, not just the area.
3. **Combining unrelated rules** — One rule, one concept.
4. **Adding a hook to every rule** — Hooks are for repeat failures with detectable triggers.
5. **Explaining without proposing** — Every problem gets a proposed solution.
6. **Cherry-picking** — Address ALL problems in order. Don't skip or reorder.
7. **"Same-session test passed = fix held"** — Documented failure mode from
   Session 185 → 186. Same-session tests use trigger surfaces narrower than
   field surfaces. A hook that passes same-session can fail in field on the
   first variant scenario. Fix Held? requires a 5-session watch window per
   Step 8 Phase 3. Never mark a fix as held after one session.

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

---

## Full Rules Audit

Use this when Nick says "audit all the rules" or when setting up a new project. This is a separate workflow from fixing individual broken rules (Steps 1-9 above).

### Pass 1: Bloat Check

For every memory edit, check: does this rule contain two unrelated concepts?

Present as a table:

```
| # | Rule | Single concept? | Verdict |
```

- Two related triggers in the same domain = Clean (e.g., end-of-session copy + start-of-session stale check — both are project knowledge freshness)
- A rule + its hook = Clean (hook is enforcement of the rule, not a separate concept)
- A base rule + a clarification that prevents misapplication = Clean (same concept)
- Two genuinely unrelated behaviors jammed into one rule = Bloat — split them

### Pass 2: Conflict Check — Rule Pairs

For every pair of memory edits that could overlap, check: do they contradict each other?

Present as a table:

```
| Pair | Potential conflict? | Verdict |
```

- Sequential rules (one picks the tool, the next gates how to use it) = No conflict
- Cross-references (one says "escalate per rule #X") = No conflict
- Same domain but different scopes (one for layout, one for DOM) = No conflict — note different domains
- Genuine tension (two rules give opposite guidance for the same scenario) = Conflict — resolve by deciding which wins and noting why

### Pass 3: Conflict Check — Rules vs User Preferences

For every memory edit, check: does it contradict its matching User Preference?

Present as a table:

```
| # | Rule | Matching Pref | Contradiction? |
```

- Identical text = Aligned — reinforcement
- Memory adds specificity to a general preference = Aligned — memory adds detail
- Memory contradicts the preference = Fix the memory edit wording to align
- No matching preference (project-specific rule) = N/A

### Pass 4: Dual-Location Sync Check

For every rule that lives in both memory and userPreferences, verify
character-for-character alignment of the trigger surface.

Present as a table:

| Rule | Memory text | Preference text | Aligned? |

Misalignment = the two versions have drifted apart. Both versions must be
re-synced to the canonical (most recent, intentional) wording, and the
registry synced_hash updated.

### Pass 5: Hook Surface Coverage Check

For every rule with a hook, build the two-column rule-surface / hook-
surface table per A2.

Present as a table:

| Rule | Rule surface row | Hook surface row | Covered? |

Any uncovered row = known blind spot. Either expand the hook, split the
rule, or explicitly document the gap and route it through a backup rule.

### Pass 6: Hook Shape Concreteness Check

For every hook, classify into Shape 1 / 2 / 3 per Step 3. Verify the hook
text matches the shape's required structure.

Present as a table:

| Rule | Hook shape | Trigger text | Falsifiable? |

Hooks that cannot be classified into a shape are not real hooks — they are
documentation. Either redesign into a valid shape or relabel as
documentation.

### Pass 7: Tier-to-Enforcement Alignment Check

For every rule, verify the tier matches the enforcement level.

Present as a table:

| Rule | Tier | Has hook? | Hook fires reliably? | Alignment |

Tier 1 with no hook = documentation in a Tier 1 slot. Either add a hook
or demote the tier. Tier 3 with a strong hook = enforcement mismatch in
the other direction — usually fine, but flag for review.

### Audit Verdicts

After all three passes, state:
- Total bloat issues (and which rules need splitting)
- Total contradictions (and which pairs conflict)
- Total preference conflicts (and which need wording alignment)
- Any noted tensions that are resolved by escalation paths

### CRITICAL: What Audits Do NOT Do

- Audits do NOT remove rules that duplicate User Preferences — those are reinforcement
- Audits do NOT add hooks to every rule — hooks are for repeat failures only
- Audits ONLY remove non-rules: status records, TODOs, action items, decision logs
- Any removal requires Nick's explicit approval before executing

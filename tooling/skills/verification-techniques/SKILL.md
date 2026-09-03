# Verification Techniques

These techniques force Claude to externalize reasoning before committing to an answer. Use them whenever the cost of a wrong answer is high.

## 1. Chain-of-Thought Verification
**When to use:** Claude says "this should work" without showing logic; answer involves field names, API responses, or CSS values; answer has multiple dependencies.

Prompt:
> Before you give me your final answer, reason through this step by step. Show: (1) what you know for certain from the actual code/data I've provided, (2) what you're inferring or assuming, (3) where your reasoning could be wrong, (4) your final answer ONLY after completing steps 1-3. Do not skip to the answer first.

**Example — Session 17:** Claude was about to write JS using fields sender, channel, quality_score. After Chain-of-Thought, Claude stated: "I'm inferring these field names from the frontend design, not from the actual API response." Correct fields after checking: action_type, description, timestamp.

## 2. Best-of-N Verification
**When to use:** Calculating layout values, pixel dimensions, or formulas; Claude produced a confident numeric answer with no math shown; same question gave different answers in a previous session.

Prompt:
> Solve this three separate times showing your work each time. Then compare all three answers. If they agree: state the answer. If any disagree: identify where reasoning diverged and which is correct.

**Example — Sessions 9-10:** Responsive zoom calculation. Single attempt guessed zoom = window.innerWidth / 1440. Three-run test: all three produced zoom = h / 1298, matching the Fiverr dev fix.

## 3. Iterative Refinement (Self-Review)
**When to use:** Claude just wrote a function and declared it "done"; implementation feels right but untested; suspicion of off-by-one, missing condition, or edge case.

Prompt:
> Review this as if you didn't write it. Look for: (1) Unconfirmed assumptions, (2) Missing edge cases, (3) Silent failure modes, (4) Contradictions with earlier session decisions. List every issue found, then produce a corrected version.

**Example — Session 16:** loadAshInbox() had an el is not defined ReferenceError. Self-review caught: variable declared in outer forEach but not accessible inside click handler closure.

## 4. CSS Dual-Run Consistency Check
**When to use:** Claude is proposing specific pixel dimensions; about to implement a grid/flex/sidebar width; layout looked right in planning but broke in implementation.

Prompt:
> Answer this layout question twice independently. First answer: solution + values. Second answer: derive from first principles without referencing your first answer. Then compare: do both produce identical px values? Known measurements (use ONLY these): Viewport [W]x[H] | Sidebar [N]px | Topbar [N]px

## 5. External Knowledge Restriction — Documents
**When to use:** Asking about any field name, API endpoint, or database column; writing JS that references Flask routes or response objects; Claude references a general pattern instead of your actual pattern.

Prompt:
> Use ONLY the code/data I've provided. Do not fill gaps with training data. If something is missing: tell me what's missing. Do NOT invent it.

**Example — Session 17:** Before this technique, Claude assumed Activity endpoint returned { sender, channel, quality_score }. After pasting actual curl output: { action_type, description, timestamp, entity_id }.

## 6. External Knowledge Restriction — CSS Measurements
**When to use:** Any layout task involving specific pixel values; Claude proposes a size you didn't give it; working on a component after changing viewport setup.

Prompt:
> Use ONLY these measured values. Do not default to training-data layout dimensions. Viewport: [W]px x [H]px | Sidebar: [N]px | Topbar: [N]px | Content: [W-N]px x [H-N]px. Every px value in your answer must trace back to this list.

## 7. Maximum Precision Mode (Combined)
**When to use:** Writing JS that reads API data AND renders into a measured layout; starting a new tab/section/component from scratch; previous session had a regression from assumed values.

Prompt:
> MAXIMUM PRECISION MODE. Data: use ONLY this API response. Flag missing fields. [paste curl output]. Measurements: use ONLY these Hoverify values. Viewport [W]x[H] | Sidebar [N]px | Topbar [N]px. Format answer as: 1. Confirmed fields 2. Confirmed measurements 3. Implementation

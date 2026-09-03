# Prompting Patterns

Three structured prompt patterns for getting precise, verifiable output from Claude Code and Cursor. Use these when free-form prompts produce vague or incomplete results.

## 1. Format Specification
**When to use:** You need output in a specific structure — code blocks, tables, labeled sections, step-by-step with headers.

Pattern:
> Format your response as:
> [Section 1 label]: [what goes here]
> [Section 2 label]: [what goes here]
> No preamble. No summary. Just the sections above.

**Example:**
> Format your response as:
> SELECTOR: the exact CSS selector
> CURRENT VALUE: what it is now
> NEW VALUE: what to change it to
> SIDE EFFECTS: any other rules this might conflict with
> No preamble. No summary.

## 2. Sequential Steps
**When to use:** Multi-step task where order matters and you need confirmation at each stage. Prevents Claude from skipping ahead or silently handling errors.

Pattern:
> Do these steps IN ORDER. After each step, report what you found/did before moving to the next. If any step produces an unexpected result, STOP and report — do not continue.
> Step 1: [action]
> Step 2: [action]
> Step 3: [action]

**Example:**
> Do these steps IN ORDER. Report after each.
> Step 1: grep for all references to "quality_score" in dashboard.html
> Step 2: For each reference found, show the surrounding 5 lines of context
> Step 3: List which functions use this field
> If any step finds zero results, STOP and report.

## 3. Positive/Negative Examples
**When to use:** Claude keeps producing output in the wrong format or style despite corrections. Showing what you want AND what you don't want eliminates ambiguity.

Pattern:
> CORRECT (do this):
> [example of desired output]
>
> WRONG (not this):
> [example of undesired output]
>
> Key difference: [what makes the correct version correct]

**Example:**
> CORRECT (do this):
> set .ash-inbox-card margin-top to 8px
>
> WRONG (not this):
> I'd suggest adjusting the margin-top to around 8-12px for better visual balance
>
> Key difference: Exact value, exact selector, no opinions. Write what I tell you.

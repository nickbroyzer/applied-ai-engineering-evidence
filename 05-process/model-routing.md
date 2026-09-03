# Model routing — which model for which task, and why

Source: rule **U11 — MODEL SELECTION** and **U12 — TOKEN DISCIPLINE** in
[`behavioral-rulebook.md`](behavioral-rulebook.md), quoted below. The routing is
Cursor-scoped; Claude Code's own mode, model and effort vocabulary is governed
separately by U18.

## The rule, verbatim

> Ask → Composer 2.5. Plan → Sonnet 4.6. Agent → Composer 2.5. Debug → Sonnet
> 4.6. Upgrade to Sonnet 4.6 for complex Ask. Upgrade to Opus 4.8 for
> architectural Plan or deeply stuck Debug. Never recommend Auto, Premium, or
> MAX Mode. After a plan is approved, Agent defaults to Composer 2.5 — only
> escalate if Composer 2.5 produced broken output. Never Opus for Agent.

> Match tool cost to task complexity. Don't use Plan mode for a one-line fix.
> Never sacrifice quality to save tokens — but don't burn expensive tokens on
> cheap work.

## As a table

| Mode | Default | Escalate to | When |
|---|---|---|---|
| Ask | Composer 2.5 | Sonnet 4.6 | the question is complex |
| Plan | Sonnet 4.6 | Opus 4.8 | the plan is architectural |
| Debug | Sonnet 4.6 | Opus 4.8 | deeply stuck |
| Agent | Composer 2.5 | Sonnet 4.6 | and **only** after Composer produced broken output |

## The three clauses that carry the argument

**Never Opus for Agent.** Execution against an approved plan is the cheapest
kind of work in the loop: the thinking already happened in Plan. Spending the
most expensive model on typing out a decision already made is the single
easiest way to burn budget for nothing.

**Escalate on evidence, not on anticipation.** Agent escalates *only if*
Composer already produced broken output. The trigger is an observed failure,
not a guess that the task looks hard. Guessing upward is how every task becomes
an Opus task.

**Never Auto, Premium, or MAX.** Those hand the routing decision to a heuristic.
The point of the rule is that the routing decision is *made* and *recorded*, so
that when cost or quality moves, the cause is inspectable. Automatic selection
makes the same choice invisibly and leaves nothing to review.

## The limitation this document must state

This is a **routing policy**, not a routing system. There is no code that reads
a task and dispatches a model; it is a rule a human and an assistant follow, and
its adherence has never been measured. Zelbi's own product code contains no
model routing at all — the vision pipeline calls one model, and the knowledge
system calls none. Any claim of "built a model routing system" would be false,
and the fact pack marks it prohibited.

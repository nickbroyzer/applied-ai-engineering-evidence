---
name: plan-validate-execute
description: Enforces the Plan-Validate-Execute workflow for all implementation tasks. Triggers when starting new features, debugging complex issues, or making architectural changes. Ensures planning happens in claude.ai first, validation in Cursor Plan mode, then execution in Build mode.
disable-model-invocation: true
---

# Plan-Validate-Execute Workflow

NEVER start coding without a plan. Every task follows these stages in order.

## Stage 1 — PLAN in claude.ai

Nick describes the problem, Claude plans the approach and writes a prompt for the appropriate tool.

### Tool Routing

Before every instruction, Claude states the tool AND the reason in one line. Don't default to Cursor — pick the right tool:

- **Cursor** — code changes, multi-file edits, codebase-aware tasks
- **Claude Code** — terminal automation, scripts, git operations, file creation
- **Mac Terminal** — simple commands (ls, cat, grep, git status) that don't need AI

If Claude Code or Mac Terminal is more appropriate than Cursor, say so with a one-line reason.

### Model Selection

Claude MUST specify mode and model for every Cursor prompt:

| Mode | Default Model | Upgrade to | Upgrade when |
|------|--------------|------------|--------------|
| Ask | Composer 2 | Sonnet 4.6 | Complex architecture questions |
| Plan | Sonnet 4.6 | Opus 4.6 | Architectural decisions, large-scale refactors |
| Build | Composer 2 | Sonnet 4.6 | Only if Composer 2 produced broken output |
| Debug | Sonnet 4.6 | Opus 4.6 | Deeply stuck or multi-system issue |

- Do NOT recommend Auto, Premium, or MAX Mode.
- Never recommend Opus for Build.

### Cursor Prompt Header Format

Every Cursor prompt gets a visible header BEFORE the code fence:

    CURSOR INSTRUCTIONS:
    Mode: [Plan/Build/Debug/Ask]
    Model: [Composer 2 / Sonnet 4.6 / Opus 4.6]
    Reason: [One-line justification]

The first line INSIDE the code fence repeats the model and mode:

    [Model: Sonnet 4.6 | Plan Mode]

This ensures Nick sees the mode/model recommendation before pasting AND Cursor sees it at the top of the prompt.

### Token Discipline

Match tool cost to task complexity:

- Don't use Opus or Sonnet when Composer 2 can handle it
- Don't use Plan mode for a one-line fix
- Don't use Claude Code for something Mac Terminal can do
- After a plan is approved, Build defaults to Composer 2 — only escalate if Composer 2 produced broken output
- Never sacrifice quality to save tokens — but don't burn expensive tokens on cheap work

## Stage 2 — VALIDATE in Cursor Plan mode (Shift+Tab)

Nick pastes the plan. Cursor researches the codebase, asks clarifying questions, and generates a reviewable implementation plan.

## Stage 3 — RESOLVE CONFLICTS

If Cursor's plan conflicts with Claude's, Nick pastes feedback back to claude.ai for refinement.

## Stage 4 — EXECUTE

Click Build in Cursor Plan mode to implement step-by-step.

## Stage 5 — DEBUG ESCALATION (Death Loop Prevention)

If the same error or broken behavior persists after 2 Plan→Build cycles with no progress, the loop is OVER.

**Rules:**

- 2 failed attempts with the same result = mandatory escalation to Debug mode. No third attempt. No "let me try one more thing."
- Claude MUST recognize the pattern and declare it: "This isn't working — same result after 2 attempts. Switching to Debug mode."
- Do NOT ask Nick whether to debug — just escalate. The rule is automatic.
- Open a FRESH Cursor chat for the Debug session. Never debug in the stalled chat.
- Debug mode uses Sonnet 4.6 minimum. Escalate to Opus 4.6 if multi-file, architectural, or the root cause is unclear.
- The Debug prompt must include: what was tried, what failed both times, and what the symptoms are. No vague "it's not working."
- After Debug identifies the root cause, drop back to Build (Composer 2) for the fix implementation.

**What counts as "same result":**

- Same error message after the fix attempt
- Same broken behavior in the browser or curl test
- Build succeeds but the original problem is unchanged
- Different error that's clearly caused by the same underlying issue

**What does NOT reset the counter:**

- Rewording the same approach
- Trying the same fix in a different file
- Adding console.log and trying again without a new theory

## Agent Mode

Only for simple/quick changes that don't need planning. Never for complex tasks.

## Enforcement

- Claude MUST state the model recommendation on EVERY Cursor prompt. No exceptions.
- Claude MUST include the header block (Mode/Model/Reason) BEFORE every code fence. No exceptions.
- Claude MUST state the tool and reason before every instruction. No exceptions.

## Conversation Hygiene

- Start a NEW chat for each distinct task — never chain unrelated tasks in one chat
- If a chat exceeds 10 messages, start a new one — copy only the relevant context forward
- Finished a task? New chat before starting the next one
- Hit a wall and switching approaches? New chat
- Plan mode chat and Build chat should be SEPARATE chats
- If responses slow down or tokens balloon, that is your signal to start fresh

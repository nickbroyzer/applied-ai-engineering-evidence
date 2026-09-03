# Enforcement hooks — what each one blocks, and why documentation wasn't enough

Every rule in [`behavioral-rulebook.md`](behavioral-rulebook.md) was first
written as prose. The ones below are the ones prose did not hold. Each has a
dated entry in the registry saying what broke and how many times before the
hook was written — that record is the point: a rule that needs a hook is a rule
that was already violated, repeatedly, by a model that had read it.

Source for every description below: the hook scripts in
[`../tooling/hooks/`](../tooling/hooks/), read directly.

## The shape

Claude Code hooks fire at three points. Which point a hook uses determines what
it can do:

| Point | When | What it can do |
|---|---|---|
| `PreToolUse` | before a tool call runs | refuse the call (exit non-zero) |
| `PostToolUse` | after a tool call runs | fail the step, forcing a fix |
| `Stop` | before a response reaches the user | block the response (exit 2 + stderr) |

A `Stop` hook is the only one that can gate what Claude *says*. Five of the
eight below are `Stop` hooks, because the failures they catch are failures of
assertion, not of action.

## Response-gating hooks

### `plain-english-hook.py` — enforces U19 PLAIN ENGLISH PROSE

Scans prose lines for code identifiers and blocks the response if it finds one
outside a code fence. It strips inline backtick spans first, then skips list
items, table rows, headings and blockquotes, so only genuine prose is scanned.
Six identifier classes are matched: file extensions, `snake_case`, `camelCase`,
`ALL_CAPS` constants, function calls, and file paths.

**Why it exists:** prose thick with identifiers is unreadable to the person who
has to make the decision it describes. The rule says identifiers belong in
prompt blocks and value lists; the hook is what makes that true.

### `brevity-hook.py` — enforces RESPONSE BREVITY

Extracts everything before the first fenced block, list item, or table row, and
blocks if that prefix runs past three sentences.

**Why it exists:** the failure mode is a model explaining its reasoning at
length before delivering the thing that was asked for. Three sentences is the
budget.

### `pacing-hook.py` — enforces U2 PACING LOCK

Counts *asks* in a response — prompt-block headers, "Run this"-style intros, and
any block of two or more numbered imperatives — and blocks when more than one
is stacked.

The interesting part is what it deliberately does **not** count: internal tool
sequencing inside one approved task is invisible to it. The rule is about not
stacking work on the human, not about limiting the agent's own steps.

### `prompt-format-hook.py` — enforces the two-block prompt rule

A command for a human to run must arrive as two fenced blocks: the header
(tool, mode, reason, model) in one, the command itself in another. The hook
parses the fenced blocks and fails any single block containing both a header
signature and a command line.

**Why it exists:** one block means the human copies the header into the
terminal along with the command.

### `decision-ownership-hook.py` — enforces U21 DECISION OWNERSHIP

A `PreToolUse` hook that inspects only calls to the ask-the-user tool and
refuses the call when the question is shaped as decision overload: "should I X
or Y", "do you want X or Y", "would you prefer X or Y", "option 1 … option 2",
numbered choices, or lettered choices.

**Why it exists — and this is the one worth stopping on:** it blocks the agent
from handing a technical decision back to the operator. An agent that asks
"should I use A or B?" has converted its own job into the operator's. The hook
forces it to decide, act, and report — reserving the question for what only the
operator can settle.

## Action-gating hooks

### `git-push-blocker.sh` — QA gate on push

A `PreToolUse` hook on shell commands. If the command contains `git push`, it
looks for a verification flag file under the project's state directory. Absent,
the push is refused with the four checks that must run first (visual, endpoint,
console, then touch the flag). Present, the push proceeds **and the flag is
deleted** — so the gate re-arms and one verification never covers two pushes.

### `js-syntax-check.sh` — parse gate on edit

A `PostToolUse` hook. After any `.js` edit it runs `node --check` on the file
and fails the step on a syntax error, so a broken parse is caught at the edit
rather than at the next run. It also counts `console.log` occurrences and warns
— a warning, not a failure, deliberately.

## Session lifecycle

`session-start.sh` prints the project name, `git status --short`, the last five
commits, and looks for a project-level instructions file — so a session begins
with the repository's actual state rather than an assumption about it.
`session-end.sh` and `pre-compact.sh` are its counterparts at close and at
context compaction.

## The parser, and its test

`conduct_lesson_parser.py` extracts "conduct lessons" from session notes,
recognising rule identifiers (`M<n>`, `U<n>`) and the named rules by their
words — DECISION OWNERSHIP, RESPONSE BREVITY, PACING LOCK, PLAIN ENGLISH PROSE,
NEVER INVENT, HYPOTHESIS-LOCK. It hashes and caches its input so re-parsing an
unchanged file is free.

It ships with `test_conduct_lesson_parser.py`. That is the honest tell about
this bundle: the hooks are shell and Python one-offs, and exactly one of them —
the one with parsing logic complex enough to be wrong quietly — has a unit test.
The others fail loudly by design.

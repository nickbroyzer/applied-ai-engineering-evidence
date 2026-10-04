# tooling — the AI-delivery system

MIT licensed (see [`../LICENSE`](../LICENSE)). This is my own work, separate
from Zelbi, and other people should be able to use it.

| | |
|---|---|
| [`agents/`](agents/) | Nine subagent definitions I wrote — code review, security review, debugging, deployment, frontend, Python, SQL, planning, build-error resolution. The fifteen framework definitions that sit alongside them on my machine belong to an installed framework and are **not** included. |
| [`hooks/`](hooks/) | Twelve runtime enforcement hooks plus a unit-tested rule parser. What each one blocks, and why documentation alone was not enough: [`../05-process/enforcement-hooks.md`](../05-process/enforcement-hooks.md). |
| [`rules-registry/`](rules-registry/) | The cross-tool rules registry: one source of truth with tiers, hook bindings and revision dates, per-project rule files, two versions of the rule-fix blueprint, and a breakage log. |
| [`skills/`](skills/) | The skills I authored, including the two-stage handoff protocol behind Zelbi's sessions, numbered through 473. (This folder is a snapshot taken 2026-09-03.) |

MCP servers are configured in the Claude Code environment rather than in any
file in this repository, and the Cursor-facing rules are a single file,
[`rules-registry/tools-cursor.md`](rules-registry/tools-cursor.md).

## Before you reuse these

**Paths are machine-specific.** Several hooks and rule files contain absolute
paths under my home directory. They are kept **verbatim** here because this is
evidence of what actually runs, not a packaged distribution. You will need to
change them.

**The hooks assume Claude Code's hook contract** — `PreToolUse`, `PostToolUse`
and `Stop` events, wired through a settings file, with a non-zero exit meaning
refuse. They read JSON on stdin and write to stderr.

**The rules are mine.** They encode one person's working preferences —
plain-English prose, no stacked instructions, a decision-ownership rule that
stops an agent handing technical choices back to me. Read them as a worked
example of enforcing a working agreement, not as defaults to adopt.

## The one honest tell

Exactly one hook has a unit test: the rule parser, which is the only one with
logic complex enough to be wrong quietly. The rest fail loudly by design. That
is a deliberate line, and it is where I would start if I were extending this.

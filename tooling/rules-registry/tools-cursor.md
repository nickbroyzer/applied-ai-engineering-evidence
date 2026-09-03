# Tool 1 — Cursor IDE

**Last Updated: 2026-04-12**

### Version & Release
- **Current Version**: Cursor 3.0 (released April 2, 2026)
- **Latest Patch**: April 8, 2026 (Bugbot Enhancements)

### UI Layout

**Main Windows**:
- **IDE Window**: Full editor with file explorer, terminal, and sidebar. Built from scratch (NOT a VS Code fork). Full Language Server Protocol support.
- **Agents Window**: Multi-agent management sidebar for running parallel agents across repos and environments. Accessed via `Cmd+Shift+P`. Supports local, worktree, cloud, and remote SSH execution contexts.
- **Mission Control**: Grid view of open windows as scaled previews with spring-based layout animations. Triggered with `F3`.
- **Floating Composer**: Customizable chat overlay with dark/light theme styling.
- **Integrated Browser**: For local website interaction within the IDE.
- **Enhanced Diffs View**: Simplified UI for rapid staging, committing, and PR management.

### Modes

| Mode | Description | How to Activate |
|------|-------------|-----------------|
| **Agent** | Main coding interface using Composer 2 model with full codebase understanding. Default mode. | Default — always active |
| **Ask** | Interactive questioning and clarification. | Type a question in Agent input |
| **Plan** | Complex tasks: asks clarifying questions, researches codebase, generates detailed plan, then executes in background. | `Shift+Tab` in Agent input |
| **Debug** | Instruments code with real execution data to pinpoint fixes. | Integrated mode |
| **Design** | Visually edit UI elements by selecting, resizing, and rewriting directly in the browser preview. | `Cmd+Shift+D` toggle |

**Plan Mode Workflow**:
1. Describe requirements in Agent input, press `Shift+Tab`
2. Agent researches codebase (auto-discovers relevant files)
3. Agent asks clarifying questions
4. Generates detailed plan in Markdown with file paths and code references
5. User reviews/edits plan inline (add/remove tasks)
6. Build directly from finalized plan
7. Optionally save plan as repository Markdown file

> "Most new features at Cursor now begin with Agent writing a plan. We've seen this significantly improve the code generated."

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| `Cmd+K` | Command palette (file search, actions, settings) |
| `Cmd+L` | Add element to chat (Design Mode) |
| `Shift+Tab` | Activate Plan Mode in Agent input |
| `Cmd+Shift+P` | Open Agents Window |
| `Cmd+Shift+D` | Toggle Design Mode |
| `F3` | Mission Control |
| `Shift+drag` | Select areas in Design Mode |
| `Option+click` | Add element to input (Design Mode) |
| `/` | Slash commands |

### .cursorrules and .cursorignore

- **`.cursorrules`**: Project-level configuration file for teaching Cursor team conventions, architectural decisions, and coding preferences. Part of the broader "Team Rules" system — rules are shared across team members.
- **`.cursorignore`**: File exclusion patterns (analogous to `.gitignore`) — tells Cursor which files/directories to ignore during codebase indexing and context gathering.

### Tab Completion
- Tab-based navigation for switching between multiple agent chats simultaneously
- Supports side-by-side or grid layouts of agent tabs

### Model Selection
- **Composer 2**: Primary frontier coding model (default)
  - Standard: $0.50/M input, $2.50/M output tokens
  - Fast (default): $1.50/M input, $7.50/M output tokens
- **Multi-model strategy**: Subagents run in parallel, each using the best model for its task
- Referenced models in dropdown: Opus 4.6, Composer 2, GPT 5.2 Codex, Gemini 3 Pro
- Custom embedding model for codebase indexing with best-in-class recall

### MCP / Plugin Support
- **MCP (Model Context Protocol)**: Connects to external tools and data sources. Direct integrations with GitHub and Figma. MCP server support available on Teams and Enterprise plans.
- **Marketplace**: Hundreds of community-built plugins extending agent capabilities
- **Extension types**: MCPs, Skills (custom slash commands), Subagents (parallel execution), Plugins

**Example Slash Commands**: `/fix-merge-conflicts`, `/code-review`, `/apply-notion-styleguide`, `/pr`, `/test`

### @-Mention Types

| Type | Purpose |
|------|---------|
| `@File` | Reference specific files (blue highlight) |
| `@Folder` | Reference folders (blue highlight) |
| `@Web` | Reference web resources (gray styling) |
| `@Code` | Reference code symbols |
| `@Terminal` | Reference terminal/execution context |
| `@Codebase` | Full codebase context |

### Bugbot (April 2026)
- Automated bug detection from PR feedback
- "Learned rules" enable self-improvement across PRs
- Resolution rate: 78%
- "Fix All" action for multiple fixes in one operation

---

## Staleness Warning

> **If Claude gives wrong UI locations or button names across 2+ sessions, Nick should flag it and Claude should research current tool state and propose updates to this doc.**
>
> This document was compiled from live URL fetches on 2026-04-12.
> - **Cursor**: Version number, mode names, keyboard shortcuts, and model dropdown options change with each release

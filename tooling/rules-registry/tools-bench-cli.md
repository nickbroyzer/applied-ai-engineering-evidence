# Tool 4 — Frappe Bench CLI

**Last Updated: 2026-04-12**

Commands relevant to the aibs-core project. All commands run from the `frappe-bench` directory.

### App Management

| Command | Syntax | Description |
|---------|--------|-------------|
| `bench new-app` | `bench new-app {app-name}` | Scaffolds a new Frappe app with boilerplate directory structure. **Local only.** |
| `bench get-app` | `bench get-app {git-url} [--branch {branch}]` | Clones a Frappe app from a git repo into the `apps/` directory. Use `--branch` to specify a branch. **Local only** (on FC, apps are added via dashboard). |
| `bench install-app` | `bench --site {site-name} install-app {app-name}` | Installs an app on a specific site (creates DocTypes, runs patches). **Available on FC** via site shell or dashboard. |

### Schema & Assets

| Command | Syntax | Description |
|---------|--------|-------------|
| `bench migrate` | `bench --site {site-name} migrate [--rebuild-website]` | Syncs DocType schema changes, runs patches, rebuilds search index. Add `--rebuild-website` to regenerate static pages. **Available on FC** via site actions. |
| `bench build` | `bench build [--app {app-name}]` | Compiles JS/CSS assets for all apps (or a specific app). **Local only** (FC builds during deploy). |
| `bench clear-cache` | `bench --site {site-name} clear-cache` | Clears Redis cache, DocType cache, and defaults. **Available on FC** via site actions. |

### Development

| Command | Syntax | Description |
|---------|--------|-------------|
| `bench console` | `bench --site {site-name} console [--autoreload]` | Opens an IPython REPL with full Frappe context. `--autoreload` watches for file changes. **Local only.** |
| `bench start` | `bench start` | Starts all dev processes (web, socketio, redis, worker) via Procfile. **Local only** (FC manages processes). |

### Configuration

| Command | Syntax | Description |
|---------|--------|-------------|
| `bench set-config` | `bench set-config {KEY} {VALUE}` | Sets a key-value pair in `common_site_config.json`. **Local only** (on FC, use Config tab). |
| `bench show-config` | `bench show-config [--format json]` | Displays current bench configuration in table or JSON format. **Local only.** |

### System Management

| Command | Syntax | Description |
|---------|--------|-------------|
| `bench restart` | `bench restart` | Restarts all bench services (supervisor/systemd). Only meaningful in production setup. **Available on FC** via bench actions. |
| `bench pip` | `bench pip {pip-args}` | Runs pip within the bench's Python virtualenv. E.g., `bench pip install requests`. **Local only.** |
| `bench version` | `bench version` | Shows version of all installed apps on the bench. **Local only.** |
| `bench update` | `bench update [--pull] [--patch] [--build] [--restart]` | Comprehensive update: pulls latest code, runs patches, builds assets, restarts services. Flags allow running individual steps. **Local only** (on FC, updates happen via deploy workflow). |

### Local-Only vs Frappe Cloud Availability

| Available on Frappe Cloud | Local Only |
|---------------------------|------------|
| `install-app` (via dashboard) | `new-app` |
| `migrate` (via site actions) | `get-app` |
| `clear-cache` (via site actions) | `build` (runs during deploy) |
| `restart` (via bench actions) | `console` |
| | `set-config` (use Config tab) |
| | `show-config` |
| | `start` |
| | `pip` |
| | `version` |
| | `update` (use deploy workflow) |

---

## Staleness Warning

> **If Claude gives wrong UI locations or button names across 2+ sessions, Nick should flag it and Claude should research current tool state and propose updates to this doc.**
>
> This document was compiled from live URL fetches on 2026-04-12.
> - **Bench CLI**: Command flags and behavior are generally stable but check `bench --help` for current options

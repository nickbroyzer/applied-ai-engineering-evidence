# Tool 2 — Frappe Cloud Dashboard

**Last Updated: 2026-04-12**

### Access
- **Dashboard URL**: `frappecloud.com/dashboard`

### Navigation
Top-level sections: **Sites**, **Benches**, **Apps**

> **Terminology change (Feb 2026)**: "Bench Groups" renamed to "Benches" throughout the dashboard.

### Key Concepts

**Bench**: A collection of apps and sites where all sites share identical configuration settings. On Frappe Cloud, a Bench is "a Frappe Bench running inside a container from which your site is served."

**Bench Templates**: Created by Frappe Cloud, accessible via Benches menu. Specify which apps to install and dependency versions.

**Private Benches**: Users can independently set and update template info, apps, config flags, and dependency versions.

### Bench Detail Page Tabs

| Tab | Purpose |
|-----|---------|
| **Apps** | Manage installed apps, add new apps from marketplace or custom sources |
| **Sites** | View and manage sites running on this bench |
| **Deploys** | Monitor deployment progress, view build logs, see app versions |
| **Config** | Bench configuration flags and dependency versions |

### Deploy Workflow

1. **Update notification**: Banner appears on bench dashboard when updates are available ("Update Available" button)
2. **Select apps**: Choose which apps to update (can deselect unwanted updates). Note: "You cannot deselect Frappe Framework if you want to update ERPNext."
3. **Click Deploy**: Initiates the build process
4. **Build phase**: Displays on dedicated screen. "Fail Build" button available to stop running builds.
5. **Provisioning & Queueing**: "Benches are currently in line and will begin installing on the server as soon as a processing slot becomes available"
6. **Monitor in Deploys tab**: Track deployment progress. Click three-dot menu to see "all apps deployed and their versions."

**Redeploy Option**: Appears only when a deploy has succeeded or failed.

**Auto-updates**: Sites with auto-update enabled update automatically "during non-working hours (1 AM - 4 AM)."

### Creating a New Bench

1. Dashboard → Benches → "+ New" button
2. Specify: Frappe Framework version, geographic region, custom bench name
3. Click "Create Bench"
4. Redirected to bench group dashboard
5. Click "Updates Available" → "Next" → initiate first deployment
6. Monitor in Deploys tab

### Installing an App

**Public Sites** (direct):
1. Go to site dashboard → Apps tab → "Install App"
2. Choose app from marketplace

**Private Bench Sites** (two-step):
1. **Bench level**: Navigate to bench dashboard → Apps section → Add app → Trigger "Update Available" deployment
2. **Site level**: Return to site dashboard → Apps tab → Install the now-available app

### requirements.txt and pyproject.toml During Deploy
- Frappe Cloud runs automatic app compatibility checks via `pyproject.toml` (introduced Feb 2026)
- `requirements.txt` at app root is used for pip dependency resolution during the Docker image build phase
- Apps must declare their Python dependencies in one of these files for the build to succeed

### Pre Build Validation Warning
A warning displayed before deployment begins when Frappe Cloud detects potential compatibility issues — such as missing dependencies, version conflicts between apps, or apps that may not be compatible with the selected Frappe Framework version. Review and resolve before proceeding with deploy.

### press-deploy Commit Marker
Enables automated deployments triggered by git commits:
- **All benches**: Include `press-deploy` in commit message to deploy all applicable benches with `auto-deploy` tag
- **Specific bench**: Use `press-deploy-bench-[ID]` in commit message
- **Skipped when**: Bench lacks ownership alignment, isn't enabled for auto-deploy, or already has a deployment in progress

### Yanked Releases
Withdrawn releases flagged as problematic. Yanked releases are "skipped during the update process" — users receive notices indicating which releases were yanked. Prevents deploying known-bad versions.

### Feb 2026 Updates Summary
- "Bench Groups" → "Benches" rename
- New cloud providers: Hetzner and DigitalOcean (alongside AWS/OCI)
- Unified server option: app + database on single machine ($20/month vs $250/month)
- Automatic app compatibility checks via `pyproject.toml`
- Yanked release support
- Simplified major version upgrades
- Optional backups before site archival (6-month retention)

---

## Staleness Warning

> **If Claude gives wrong UI locations or button names across 2+ sessions, Nick should flag it and Claude should research current tool state and propose updates to this doc.**
>
> This document was compiled from live URL fetches on 2026-04-12.
> - **Frappe Cloud**: Dashboard navigation and deploy workflow UI evolve monthly

# Tool 3 — ERPNext v15 Desk UI

**Last Updated: 2026-04-12**

### Access
- **Desk URL pattern**: `your-site-name.frappe.cloud/app` (or `localhost:8000/app` in local dev)
- After login, the `/app` route loads the Desk single-page application

### Navigation
- **Sidebar**: Module list organized by category. Click a module to see its DocTypes, reports, and pages.
- **Awesomebar** (`Cmd+K` / `Ctrl+K`): Universal search for documents, navigation, creating new records, and even math operations. Functions as the primary navigation tool.
- **Theme toggle**: `Ctrl+Shift+G` switches between light and dark themes.

### Module Categories
Sidebar modules are grouped into:
- **Modules**: Core business modules (Accounting, HR, Stock, CRM, Projects, etc.)
- **Domains**: Industry-specific groupings (Manufacturing, Education, Healthcare, etc.)
- **Places**: Quick links (Home, Dashboard, Settings, etc.)
- **Administration**: System settings, users, roles, permissions

### DocType Views
ERPNext auto-generates 8 view types for each DocType:

| View | Purpose |
|------|---------|
| **List View** | Browse all records with filters, sorting, and bulk actions |
| **Form View** | Create/edit a single record with all fields |
| **Grid View** | Spreadsheet-style editing of child table rows |
| **Report Builder** | Custom queries and tabular reports |
| **Tree View** | Hierarchical display (e.g., Chart of Accounts) |
| **Calendar View** | Date-based record display |
| **Gantt View** | Timeline/project visualization |
| **Kanban View** | Card-based workflow columns |

### Custom Apps in Module Sidebar
Custom apps (like `aibs_core`) appear in the sidebar after installation. The app's `modules.txt` file determines which modules show up. Each module defined in the app gets its own sidebar entry alongside core ERPNext modules.

### Workspace Customization
Workspaces are configurable dashboard pages that can contain shortcuts, charts, number cards, and links. Accessible from the sidebar. Can be customized per role.

### Setup Wizard
On first site creation, ERPNext runs a setup wizard that walks through:
1. Language selection
2. Country and timezone
3. Company name and abbreviation
4. Chart of Accounts template
5. Company details (domain, fiscal year)
6. User creation / admin setup

### Form Timeline
Each document form includes a timeline that tracks:
- Emails sent/received
- Comments
- Field edits with before/after values
- Workflow state changes
- Linked events

---

## Staleness Warning

> **If Claude gives wrong UI locations or button names across 2+ sessions, Nick should flag it and Claude should research current tool state and propose updates to this doc.**
>
> This document was compiled from live URL fetches on 2026-04-12.
> - **ERPNext Desk**: Workspace and module organization can change between minor versions

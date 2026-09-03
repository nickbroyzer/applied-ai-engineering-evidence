# The build map and its drift check

Two documents, one distinction: **the map says what IS; the plan says what's
NEXT.** Conflating them is how a project starts believing its own intentions.

The problem with any hand-written architecture document is that it is true on
the day it is written and quietly false a month later, while still being read as
authoritative. The map answers this by being **re-derivable**: a script reads
the source and emits the facts, and those facts are diffed against a committed
snapshot. Drift is a diff, not a memory.

`check-build-map.sh` (copied here verbatim; it lives at `tools/check-build-map.sh`
in the private repository) re-derives, from source at HEAD:

| Section | Derived from |
|---|---|
| Route files | every mobile route file, layouts excluded |
| Tab and stack declarations | the screen declarations inside every layout |
| Navigation calls | every push / replace / navigate / dismissTo / back, plus redirects and links |
| Object-form nav targets | every path-form navigation object |
| Tab icon keys | the icon map in the tab bar component |
| Claim endpoint status filters | the active-status constants and status comparisons in the claims router |
| Notification target tuples | the routing tuples in the notification service |

Each section is sorted with a fixed locale and line numbers are stripped, so the
output is stable across machines and the only diff that appears is a real
change. The result is compared against the committed snapshot; a difference
means either the map is stale or a change landed that nobody recorded, and
either way it is now visible.

What this buys, concretely: the routing facts that a person would otherwise
*remember* — which notification types reach which screen, which claim statuses
an endpoint treats as active, which routes exist at all — are re-read from
source on demand. It is the same instinct as
[`verification-gates.md`](verification-gates.md), applied to documentation:
recall is not a source.

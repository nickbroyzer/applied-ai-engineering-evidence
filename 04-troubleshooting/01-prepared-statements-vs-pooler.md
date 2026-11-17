# A production cron crashed for sixteen hours and nothing paged

**Commit:** `884af15662b7c94166ca9f62ec4624693735c029` · 2026-08-13
**Sentry issue:** `PYTHON-FASTAPI-9`
**Code:** [`../code/database/EXCERPTS.md`](../code/database/EXCERPTS.md)

## Symptom

The failure surfaced by accident. While closing unrelated work I opened the
deployment dashboard and saw its own notification panel reporting that the
`frequent-jobs` service had crashed — **fifteen hours earlier**. That service
runs the ten-minute sweeps: the pending-payment cancel sweep, the post-window
capture sweep, and the reminder jobs. A crash there silently stops money-path
reconciliation.

Sentry had the error, three events, first seen sixteen hours before the read:

```
ProgrammingError (psycopg.errors.DuplicatePreparedStatement)
prepared statement "_pg3_0" already exists
```

Failing frame: `post_window_sweeper.py:263`, inside the per-claim loop, on a
plain primary-key load of a listing.

Sentry marked it `handled: yes`. That is the reason sixteen hours passed with
nothing surfacing — the sweeper was failing quietly *inside its own exception
handling* rather than crashing loudly.

## Diagnosis

The failing line was a primary-key load. Nothing about it can raise a duplicate
prepared statement name, which meant the fault was not in the sweeper at all.

The driver (psycopg v3) automatically creates server-side prepared statements
and names them by counter — `_pg3_0`, `_pg3_1`, and so on — assuming a
connection it owns for the duration of a session. Production connects through a
**transaction-mode** connection pooler, which hands the same backend connection
to different callers *between statements*. So caller A prepares `_pg3_0` on a
backend, is handed away, and caller B is handed the same backend and prepares
its own `_pg3_0`. PostgreSQL refuses the duplicate name.

This was invisible locally and in every test run, because local and
session-mode connections are not shared between callers. The bug needed the
production pooler's topology to exist at all.

The first hypothesis to reject was "the sweeper has a logic error." The stack
frame pointed there, and it was the wrong place to look. The tell was that the
error class described a *connection-level* resource, not a query.

## Fix

One connect-argument, at the engine layer, so no call site can forget it:

```python
engine = create_engine(
    settings.sqlalchemy_database_url,
    ...
    connect_args={"prepare_threshold": None},
)
```

`prepare_threshold=None` disables psycopg's automatic prepared statements
entirely. The fix lives in `database.py` rather than in the sweeper because the
sweeper was never special — any code path reaching the pooler could hit this.

The comment above it is nine lines long and states the mechanism, the Sentry
issue, why local and session-mode connections never saw it, and the condition
for removing it: *do not remove without moving off the transaction pooler.* A
future reader who deletes it as noise would re-open the same outage.

## What it cost, and what changed

The alerting gap is the real finding, and it was filed separately: nothing
paged, nothing logged anywhere I look, and the only reason this surfaced was an
unrelated visit to a dashboard. A caught-and-logged exception inside a cron
runner gives the error reporter nothing to notice — which is why the
observability work that followed added an explicit capture call inside each
`except` block rather than relying on propagation. See
[`../code/database/EXCERPTS.md`](../code/database/EXCERPTS.md) and
[`../03-decisions/ops/D274.md`](../03-decisions/ops/D274.md).

## Test

There is no regression test for this one, and there honestly cannot be a useful
unit test: reproducing it requires a transaction-mode pooler multiplexing two
callers onto one backend, which no local test database does. The guard is the
comment and the engine-level placement. Stating that is more useful than
claiming coverage that would not catch a recurrence.

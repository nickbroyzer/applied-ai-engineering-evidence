# Data and migrations

**61 Alembic revisions on a single root and a single head**, PostgreSQL with
PostGIS via Supabase, SQLAlchemy ORM, at Zelbi `8875721`. Command and output:
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md)
(the root and head were read from each revision's `revision` / `down_revision`).

## Constraints as the contract

Domain rules live in check constraints, not only in application code. Claim
status, listing status, pickup mode, dispute status and resolution are each
constrained at the table. The knowledge tables go further — the schema itself
enforces the tier rules:

- audience must equal index
- the public-safe flag must be true **if and only if** the index is public
- the deny-listed decision may never appear in a stored decision array

That last one means a leak of that decision is not merely blocked by ingestion
code; it is **unstorable**. Ingestion could regress and the row would still be
refused. You can read all of them in
[`../runnable/knowledge-eval/app/models.py`](../runnable/knowledge-eval/app/models.py),
which is byte-identical to production for those six tables.

The chunk table also carries the embedding used by Help's meaning search, as a
nullable `ARRAY(Float)` column with the model name beside it — a placeholder the
model itself labels as such, until pgvector is available on the database
(`models.py:775-777`; migration `f42fad93de29`). There is no vector index; see
[`hybrid-retrieval.md`](hybrid-retrieval.md).

A second example of the same instinct: what stops a second picker claiming an
item is a **partial unique index on claims** — not a status field, not
application logic. Which is why cancelling the claim is what frees the item, and
why a `pending_payment` claim leaves its listing `active`.

## Row-level security — stated precisely

RLS is enabled with a deny-all posture as **Supabase dashboard state**. There are
**zero RLS statements across all 61 migrations**:

```
$ grep -ril 'row level security\|ENABLE ROW LEVEL' backend/migrations/versions | wc -l
       0
```

So the honest sentence is "Supabase Auth with row-level security enabled", and
the dishonest one is any framing that presents RLS as owned, versioned
architecture. It was checked live once, on 2026-08-11: the shipped anonymous key
read zero rows from six named tables. That is a **dated one-time check**, not a
regression guard.

A related lesson, learned the hard way and recorded: the Supabase data API
returns HTTP 200 with an empty array when RLS is enabled with no policies. A
status-code-only check cannot distinguish *sealed* from *exposed* — you have to
read the row count in the body.

## Timezone handling

Listings are physical and local. Pickup hours are 9 AM to 9 PM **local time at
the item's location**, enforced server-side across all three pickup-time write
paths ([`D298`](../03-decisions/privacy/)).

Getting there took two corrections worth recording:

- A naive `DateTime` column serialises with no UTC marker, and JavaScript parses
  an unmarked ISO string as *local* time. Recent timestamps therefore landed in
  the future and collapsed to "just now". The fix is a UTC-aware type on every
  response-model datetime — and an endpoint returning a plain dict has no
  response model, so it bypasses this entirely.
- Writing an aware datetime to a naive column lets PostgreSQL localise it to the
  session timezone on assignment, shifting the stored instant and breaking
  grace-window logic. Tests writing those columns must bind naive UTC.

The timezone itself is resolved offline from coordinates to an IANA zone name.
A grep for offset-shaped field names could not find it, because it was stored as
a *name* all along — search for the concept's storage forms, not one
representation.

## The prepared-statement fix

The engine disables the driver's automatic server-side prepared statements
(`prepare_threshold=None`) because production connects through a
transaction-mode pooler that shares one backend connection between callers
between statements. Full write-up:
[`../04-troubleshooting/01-prepared-statements-vs-pooler.md`](../04-troubleshooting/01-prepared-statements-vs-pooler.md).

The connection pool is capped at 5+5, replacing a 10+30 placeholder that had
been written when the file was created and never revisited — one process could
exhaust the session-mode pooler's client limit on its own. The AI endpoints were
additionally changed to release their session **before** the model call, rather
than holding a pooled connection idle for the several seconds of that call.

## Migration hygiene, learned by breaking it

- Generating a migration while another workstream adds migrations off the same
  parent creates two heads and blocks the test suite's upgrade — 64 setup errors
  at once. Confirm the on-disk head immediately before authoring.
- A migration and the model change that needs it must reach the development
  database **in the same pass**. Once they did not, and a live endpoint answered
  500 on real sign-ins for several minutes.

# System overview

Zelbi is a location-based giveaway marketplace: React Native client, FastAPI
backend, PostgreSQL, a Stripe money path, one model call in the product, and a
deterministic policy-answering system that calls no model at all.

All figures below trace to
[`../verification/repo-metrics-2026-09-03.md`](../verification/repo-metrics-2026-09-03.md),
which carries the command that produced each one.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  CLIENT — React Native / Expo, TypeScript, 36 route screens          │
  │  feed · map · listing detail · give flow · checkout · handoff hub    │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │ HTTPS, bearer token
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  API — FastAPI, 16 routers, 14 service modules                       │
  │                                                                      │
  │   auth   listings   claims   messages   disputes   blocks   users    │
  │   ai     knowledge  uploads  places     notifications                │
  │   admin  health     stripe-billing      stripe-webhooks              │
  │                                                                      │
  │   per-route rate limiting (in-process)                               │
  └──┬───────────┬──────────────┬─────────────┬──────────────┬───────────┘
     │           │              │             │              │
     ▼           ▼              ▼             ▼              ▼
  ┌────────┐ ┌────────┐  ┌────────────┐ ┌──────────┐  ┌─────────────┐
  │ DATA   │ │STORAGE │  │ MONEY PATH │ │ AI       │  │ KNOWLEDGE   │
  │        │ │        │  │            │ │ BOUNDARY │  │             │
  │Postgres│ │object  │  │ authorize  │ │ one      │  │ NO model.   │
  │+PostGIS│ │storage │  │ capture    │ │ vision   │  │ Postgres    │
  │via     │ │for     │  │ void       │ │ call,    │  │ full-text   │
  │Supabase│ │photos  │  │ refund     │ │ five-    │  │ + refusal.  │
  │        │ │        │  │ webhooks   │ │ stage    │  │ 22 golden   │
  │44      │ │        │  │ sweepers   │ │ boundary │  │ cases.      │
  │revs    │ │        │  │            │ │          │  │ RUNNABLE →  │
  └────────┘ └────────┘  └────────────┘ └──────────┘  └─────────────┘
                                  │
     ┌────────────────────────────┴──────────────────────────────┐
     ▼                                                           ▼
  ┌────────────────────────────┐              ┌──────────────────────────┐
  │ JOBS — 4 cron entrypoints  │              │ OBSERVABILITY            │
  │ 10-minute + daily runners  │              │ error reporting on the   │
  │ pending-payment sweep      │              │ API and both cron        │
  │ post-window capture sweep  │              │ runners; no-op without   │
  │ listing expiry · reminders │              │ a DSN; skipped under     │
  │ recommendation scan        │              │ pytest                   │
  └────────────────────────────┘              └──────────────────────────┘
```

## The pieces

**Client.** React Native / Expo with Expo Router, TypeScript. 36 route screens
(41 files including layouts).

**API.** FastAPI. 16 routers, 14 service modules plus the `knowledge/` package.
Rate limiting is per-route and held in process — deliberately, because
[`D275`](../03-decisions/ops/D275.md) scopes it to the model-calling router
rather than building shared infrastructure before there is a second process to
share it with.

**Data.** PostgreSQL with PostGIS via Supabase, SQLAlchemy, Alembic — 44
revisions on a single root. Auth is Supabase Auth. Row-level security is enabled
as **unversioned dashboard state**: there are zero RLS statements across all 44
migrations, so it is honest to say row-level security is enabled and dishonest
to present it as owned architecture. See [`data-and-migrations.md`](data-and-migrations.md).

**Money path.** Stripe, with manual-capture authorization holds, webhook
signature verification, idempotency keys backed by database uniqueness, and two
reconciliation sweepers. See [`money-path.md`](money-path.md).

**AI boundary.** Exactly one model call in the product: a vision call that turns
a photo into two validated listing drafts. Everything around it is
application-level hardening. See [`ai-boundary.md`](ai-boundary.md).

**Knowledge system.** Tier-aware policy retrieval and refusal with no model,
no embeddings and no external API. Extracted and runnable at
[`../runnable/knowledge-eval/`](../runnable/knowledge-eval/).

**Jobs.** Four cron entrypoints (a ten-minute runner and a daily runner among
them) driving six job modules. Both counts are given because the two counting
methods differ.

**Observability.** Error reporting wired into the API and both cron runners,
a no-op without a DSN, and skipped entirely under pytest so a local test run
never reports its own deliberate failures.

## A second system, for context

Before Zelbi I built and deployed an AI operations platform for a commercial
construction company — an independent build for a friend's business, never sold
and not a paid client engagement. No code from it appears in this repository.

It is a Flask application with eight route blueprints and roughly twenty utility
modules on PostgreSQL and SQLite with file-lock concurrency for shared JSON
state, deployed to a managed platform, carrying a 45-test pytest suite and nine
seed scripts of realistic demo data. It unifies email, phone, SMS, calendar,
leads, invoices, jobs and payroll on one surface: a Claude classifier triages
inbound mail through a push-subscription webhook into a priority queue; a voice
receptionist over SIP puts live call transcripts and sentiment in the same
inbox; SMS intake and a public lead-capture chat that streams model replies and
books appointments round it out. A follow-on repository migrated the company
onto ERPNext — a custom Frappe app with three tested doctypes and two migration
engines preserving historical-date integrity for people and payroll records.

That system is where streaming, model-per-task selection, and OAuth-heavy
integration work live. Zelbi's AI surface is deliberately much narrower, and
[`ai-boundary.md`](ai-boundary.md) says exactly what it does and does not do.

## What is absent, and named

- **No CI workflow** at this commit. The suite was run manually at session close.
- **No Docker configuration** in the repository at this commit.
- **No automated tests on mobile or web.** All 751 tests are backend.

See [`tradeoffs.md`](tradeoffs.md) and [`../LIMITATIONS.md`](../LIMITATIONS.md).

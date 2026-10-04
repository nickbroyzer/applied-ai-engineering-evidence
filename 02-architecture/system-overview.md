# System overview

Zelbi is a location-based giveaway marketplace: React Native client, FastAPI
backend, PostgreSQL, a Stripe money path, one generating model call in the
product, and a policy-answering system that uses one embedding call to find text
and no model to write the answer.

All figures below are at Zelbi `8875721` and trace to
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md),
which carries the command that produced each one.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  CLIENT — React Native / Expo, TypeScript, 38 route screens          │
  │  feed · map · listing detail · give flow · checkout · handoff hub    │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │ HTTPS, bearer token
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  API — FastAPI, 22 routers, 25 service modules                       │
  │                                                                      │
  │   auth   listings   claims   messages   blocks    users   sources    │
  │   ai     knowledge  uploads  places     notifications     email-prefs│
  │   admin  admin-actions  admin-reads  admin-writes  events  watcher   │
  │   health     stripe-billing      stripe-webhooks                     │
  │                                                                      │
  │   per-route rate limiting (in-process)                               │
  └──┬───────────┬──────────────┬─────────────┬──────────────┬───────────┘
     │           │              │             │              │
     ▼           ▼              ▼             ▼              ▼
  ┌────────┐ ┌────────┐  ┌────────────┐ ┌──────────┐  ┌─────────────┐
  │ DATA   │ │STORAGE │  │ MONEY PATH │ │ AI       │  │ KNOWLEDGE   │
  │        │ │        │  │            │ │ BOUNDARY │  │             │
  │Postgres│ │private │  │ authorize  │ │ one      │  │ full-text + │
  │+PostGIS│ │photos; │  │ capture    │ │ vision   │  │ 1 embedding │
  │via     │ │signed  │  │ void       │ │ call,    │  │ call, rank  │
  │Supabase│ │URLs    │  │ refund     │ │ five-    │  │ fusion. NO  │
  │        │ │only    │  │ webhooks   │ │ stage    │  │ model writes│
  │61      │ │        │  │ sweepers   │ │ boundary │  │ the answer. │
  │revs    │ │        │  │            │ │          │  │ RUNNABLE →  │
  └────────┘ └────────┘  └────────────┘ └──────────┘  └─────────────┘
                                  │
     ┌────────────────────────────┴──────────────────────────────┐
     ▼                                                           ▼
  ┌────────────────────────────┐              ┌──────────────────────────┐
  │ JOBS — 2 cron runners,     │              │ OBSERVABILITY            │
  │ 8 job modules              │              │ error reporting on the   │
  │ pending-payment sweep      │              │ API and both cron        │
  │ post-window capture sweep  │              │ runners; Sentry webhook  │
  │ listing expiry · reminders │              │ (HMAC-verified) feeds    │
  │ recommendation scan · logs │              │ the admin console        │
  └────────────────────────────┘              └──────────────────────────┘
```

## The pieces

**Client.** React Native / Expo with Expo Router, TypeScript. 38 route screens
(43 files including layouts). One native Swift module, for Apple DeviceCheck —
see [`../01-product-logic/device-check-credits.md`](../01-product-logic/device-check-credits.md).

**API.** FastAPI. 22 routers, 25 service modules plus the `knowledge/` and
`email_html/` packages. 28 routes in the four admin routers, 43 behind the admin
check in all — see [`admin-and-ops.md`](admin-and-ops.md).
Rate limiting is per-route and held in process — deliberately, because
[`D275`](../03-decisions/ops/D275.md) scopes it to the model-calling router
rather than building shared infrastructure before there is a second process to
share it with.

**Data.** PostgreSQL with PostGIS via Supabase, SQLAlchemy, Alembic — 61
revisions. Auth is Supabase Auth. Row-level security is enabled
as **unversioned dashboard state**: there are zero RLS statements across all 61
migrations, so it is honest to say row-level security is enabled and dishonest
to present it as owned architecture. See [`data-and-migrations.md`](data-and-migrations.md).

**Money path.** Stripe, with manual-capture authorization holds, webhook
signature verification, idempotency keys backed by database uniqueness, and two
reconciliation sweepers. See [`money-path.md`](money-path.md).

**AI boundary.** Exactly one generating model call in the product: a vision
call that turns a photo into two validated listing drafts. Everything around it
is application-level hardening. See [`ai-boundary.md`](ai-boundary.md).

**Knowledge system.** Tier-aware policy retrieval and refusal. Retrieval is
hybrid — full-text search plus one Voyage embedding call per question, fused by
reciprocal rank, behind the same SQL visibility filter — and falls back to text
alone without a key or past a daily ceiling. No model writes the answer. See
[`hybrid-retrieval.md`](hybrid-retrieval.md); the text-only half is extracted
and runnable at [`../runnable/knowledge-eval/`](../runnable/knowledge-eval/).

**Jobs.** Two cron runners, a ten-minute one and a daily one, driving eight job
modules. Two single-job runners were folded into the daily runner and deleted on
2026-10-03.

**Deployment and object storage.** The API and both cron runners are deployed
on Railway; user images go to a Cloudflare R2 bucket with no public route —
every photo address the API returns is a time-limited signed URL (see
[`../01-product-logic/private-photo-access.md`](../01-product-logic/private-photo-access.md)).
The account, key-pair and bucket are required settings on the backend config. The marketing site and the five legal paths at zelbi.ai are served
separately from Cloudflare Pages, out of a `web/` folder in the private
repository that is not published here. No Cloudflare Workers are used.

**Observability.** Error reporting wired into the API and both cron runners,
a no-op without a DSN, and skipped entirely under pytest so a local test run
never reports its own deliberate failures. Sentry in turn posts issues to an
HMAC-verified webhook that stores them for the operator console
([`admin-and-ops.md`](admin-and-ops.md)).

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

## Other systems, named not published

Three further systems of mine are named on the resume and are **separate private
repositories**; no code from any of them appears here.

- **Command Center v7** — a Flask and PostgreSQL multi-repo internal dev
  dashboard, in production two days after its first commit. Its project rule
  file is published at
  [`../tooling/rules-registry/command-center-v7-rules.md`](../tooling/rules-registry/command-center-v7-rules.md);
  the application itself is not.
- **voice-bridge** — a Twilio-to-Gemini-Live WebSocket bridge with real-time
  audio resampling. An exploration, paused, and named as one.
- **ClawDeck** — a Stream Deck plugin driven by Claude Code lifecycle hooks. It
  appears here only as the hook command lines it is invoked from, inside
  [`../tooling/rules-registry/RULES-REGISTRY.md`](../tooling/rules-registry/RULES-REGISTRY.md).

They are listed so that a claim resting on them can be seen to rest on
description rather than on published code.

## What is absent, and named

- **No CI workflow** at this commit. The suite was run manually at session close.
- **No Docker configuration** in the repository at this commit.
- **No automated tests on mobile or web.** All 1,265 tests are backend.

See [`tradeoffs.md`](tradeoffs.md) and [`../LIMITATIONS.md`](../LIMITATIONS.md).

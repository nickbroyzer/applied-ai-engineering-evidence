# Applied AI engineering — evidence

Nick Broyzer · Seattle Metro, WA · [linkedin.com/in/nickbroyzer](https://linkedin.com/in/nickbroyzer)

I build production software end to end and I write down why. This repository is
the evidence behind my résumé: the product logic, the architecture, the
decisions with their trade-offs, the debugging, the process that made
AI-assisted delivery reliable — and the code, with its tests.

The systems themselves are private. This is what can be shown.

**Full repository walkthrough available on request during interviews.**

## Six verified numbers

Every one re-derived on 2026-09-03 at commit `3413d028`, with the command that
produced it in [`verification/repo-metrics-2026-09-03.md`](verification/repo-metrics-2026-09-03.md).

| | |
|---|---|
| **1,688** | commits, one Git author, 2026-04-09 → 2026-09-03 |
| **127** | active development days (147 calendar days) |
| **751** | backend tests, collected and passed from a clean checkout with outbound network blocked at the socket layer — [verbatim run](verification/pytest-summary-2026-09-03.txt) |
| **44** | Alembic migrations, single root |
| **406** | numbered decisions in the log; 44 published here |
| **22 / 22** | golden evaluation cases, **0 leak failures** — and you can run it yourself: [`runnable/knowledge-eval/`](runnable/knowledge-eval/) |

## The system

Zelbi is a location-based giveaway marketplace. Items are free; the picker pays
a small claim fee, taken as a card authorization hold, so that "I'll take it"
means something to the person waiting at the door.

```
  React Native / Expo client — 36 route screens
                    │
                    ▼
  FastAPI — 16 routers, 14 services, per-route rate limiting
    │         │            │             │              │
    ▼         ▼            ▼             ▼              ▼
  Postgres  Object     Money path     AI boundary   Knowledge
  +PostGIS  storage    authorize/     one vision    NO model.
  44 revs              capture/void/  call, five-   Postgres FTS
                       refund/        stage         + refusal.
                       webhooks/      hardening     RUNNABLE →
                       sweepers
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
    4 cron runners      error reporting on
    (10-min + daily)    API and both crons
```

Full picture: [`02-architecture/system-overview.md`](02-architecture/system-overview.md).

## How to read this in ten minutes

**If you have five minutes**, read two things:

1. [`04-troubleshooting/04-false-charge-message.md`](04-troubleshooting/04-false-charge-message.md)
   — a sweeper that would have cancelled claims people had paid for, found by
   reasoning about a state rather than by an error report.
2. [`04-troubleshooting/05-location-scheme-reversal.md`](04-troubleshooting/05-location-scheme-reversal.md)
   — I reversed my own location-privacy scheme offline, on eight real listings,
   to nanometre precision, and then fixed it.

**If you want to run something**, [`runnable/knowledge-eval/`](runnable/knowledge-eval/)
is a self-contained package: `pip install -r requirements.txt && pytest` gives
you 113 passing tests and a 22/22 evaluation with zero leak failures, offline,
with no API key — because the system calls no model at all. Its README records
what happened when I tried three times to make it leak.

**If you want to know how I think**, [`03-decisions/INDEX.md`](03-decisions/INDEX.md)
is 44 decisions as *question → ruling → what shipped*, including the ones that
reversed earlier decisions and the ones that ruled against building something.

## What's here

| | |
|---|---|
| [`01-product-logic/`](01-product-logic/) | The claim state machine, a 22-row failure-state matrix, the trust and safety model, location privacy |
| [`02-architecture/`](02-architecture/) | System overview, the AI boundary, data and migrations, the money path, and the trade-offs with what each one cost |
| [`03-decisions/`](03-decisions/) | 44 decision records, verbatim, by theme — money, trust, privacy, ai, ops |
| [`04-troubleshooting/`](04-troubleshooting/) | Five production write-ups: symptom → diagnosis → fix → test → commit. Plus excerpts from the lessons files |
| [`05-process/`](05-process/) | The behavioural rulebook, the handoff protocol that ran 437 sessions, model routing, verification gates, and what each enforcement hook blocks |
| [`code/`](code/) | Whole files with their tests: vision pipeline, knowledge system, payments, coordinate privacy, trust, message guard, database, jobs, mobile |
| [`runnable/`](runnable/) | The knowledge system, extracted and executable |
| [`tooling/`](tooling/) | My own AI-delivery system: nine subagents, twelve hooks, the rules registry, the skills |
| [`verification/`](verification/) | The runs and the commands that produced every number here |
| [`LEDGER.md`](LEDGER.md) | Every résumé sentence → where it is proven here |
| [`LIMITATIONS.md`](LIMITATIONS.md) | What this does not prove |
| [`MANIFEST.md`](MANIFEST.md) | Every file, its source, and every removal |

## The two things I'd want a reviewer to take away

**Failure states are the design.** The happy path — posted, claimed, collected —
is the smallest part. [`01-product-logic/failure-state-matrix.md`](01-product-logic/failure-state-matrix.md)
is twenty-two rows of what happens when a webhook is lost, a provider is
unreachable, both parties block each other, or someone deletes their account
mid-claim. Three principles run through it: fail closed and retry; a block must
leave the user somewhere to go; safety actions must be free.

**Determinism is a design choice, not a limitation.** One model call in the
product, where a wrong answer costs an edit. Zero model calls in policy
answering, where a wrong answer is a false statement about someone's money.
[`02-architecture/ai-boundary.md`](02-architecture/ai-boundary.md) argues both
sides.

## What's excluded, and why

- **Secrets, keys, hosts, buckets and account identifiers** — scanned for by
  regex and by hand; every finding is recorded in [`MANIFEST.md`](MANIFEST.md).
- **The scam-detection rule table** — publishing the patterns publishes the
  evasion recipe. The normalizer that decodes evasion *before* the patterns run
  is kept in full, because that is where the engineering is.
- **Trust-model tuned constants** — the shape of the model is the design; the
  numbers are product tuning. Names, ordering and logic are intact.
- **The real policy corpus** — replaced by three synthetic documents so the
  runnable package works.
- **The construction-company platform's code** — described, not published.
- **Internal control documents** — backlog, current-state, build map. Cited by
  line where a decision needs them.

Every removal is itemised with file and line range in
[`MANIFEST.md`](MANIFEST.md).

## Honesty notes

This is pre-launch software in active development. There is no CI at this
commit; there are no automated mobile tests — every mobile surface is verified by a recorded device walk (see 05-process/verification-gates.md); the double-capture guards are read-then-write
without row locks; arrival confirmation is client-reported. An earlier résumé draft said "sixteen call sites" for block enforcement;
re-derivation gives 13, the résumé now states no count, and
[`LIMITATIONS.md`](LIMITATIONS.md) shows the command.

I am the sole *human* code author of Zelbi. It was built with AI coding
assistants under my direction; architecture, decisions, review and release
authority stayed with me. Both halves of that sentence matter.

## Licence

All rights reserved — Zelbi material and the [`tooling/`](tooling/) bundle alike.
Published for review by prospective employers; not licensed for reuse. See
[`LICENSE`](LICENSE).

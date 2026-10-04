# Applied AI engineering — evidence

Nick Broyzer · Seattle Metro, WA · [linkedin.com/in/nickbroyzer](https://linkedin.com/in/nickbroyzer)

I build production software end to end and I write down why. This repository is
the evidence behind my résumé: the product logic, the architecture, the
decisions with their trade-offs, the debugging, the process that made
AI-assisted delivery reliable — and the code, with its tests.

The systems themselves are private. This is what can be shown.

**Full repository walkthrough available on request during interviews.**

## Six verified numbers

Every one re-derived on 2026-10-03 at commit `8875721`, with the command that
produced it in [`verification/repo-metrics-2026-10-03.md`](verification/repo-metrics-2026-10-03.md).
The September figures, at `3413d028`, are kept beside them as history.

| | |
|---|---|
| **2,122** | commits, one Git author, 2026-04-09 → 2026-10-03 |
| **155** | active development days (177 calendar days) |
| **1,265** | backend tests, collected and passed from a clean checkout with outbound network blocked at the socket layer — [verbatim run](verification/pytest-summary-2026-10-03.txt) |
| **61** | Alembic migrations |
| **564** | numbered decisions in the log; 48 published here |
| **22 / 22** | golden evaluation cases, **0 leak failures** — and you can run it yourself: [`runnable/knowledge-eval/`](runnable/knowledge-eval/) |

## The system

Zelbi is a location-based giveaway marketplace. Items are free; the picker pays
a small claim fee, taken as a card authorization hold, so that "I'll take it"
means something to the person waiting at the door.

```
  React Native / Expo client — 38 route screens
                    │
                    ▼
  FastAPI — 22 routers, 25 services, per-route rate limiting
    │         │            │             │              │
    ▼         ▼            ▼             ▼              ▼
  Postgres  Photos     Money path     AI boundary   Knowledge
  +PostGIS  private,   authorize/     one vision    1 embedding
  61 revs   signed     capture/void/  call, five-   call finds
            URLs only  refund/        stage         text; NO model
                       webhooks/      hardening     writes the
                       sweepers                     answer. RUNNABLE →
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
    2 cron runners      error reporting on API and
    (10-min + daily)    both crons; Sentry webhook
                        into the admin console
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
with no API key — because no model writes an answer, and the package runs the
text-search half of production's hybrid retrieval with the embedding key left
empty. Its README says exactly what that leaves out, and records what happened
when I tried three times to make it leak.

**If you want to know how I think**, [`03-decisions/INDEX.md`](03-decisions/INDEX.md)
is 48 decisions as *question → ruling → what shipped*, including the ones that
reversed earlier decisions and the ones that ruled against building something.

## What's here

| | |
|---|---|
| [`01-product-logic/`](01-product-logic/) | The claim state machine, a 22-row failure-state matrix, the trust and safety model, location privacy, DeviceCheck-gated credits, private photo access |
| [`02-architecture/`](02-architecture/) | System overview, the AI boundary, hybrid Help retrieval, the admin API and Sentry watcher, data and migrations, the money path, and the trade-offs with what each one cost |
| [`03-decisions/`](03-decisions/) | 48 decision records, verbatim, by theme — money, trust, privacy, ai, ops |
| [`04-troubleshooting/`](04-troubleshooting/) | Five production write-ups: symptom → diagnosis → fix → test → commit. Plus excerpts from the lessons files |
| [`05-process/`](05-process/) | The behavioural rulebook, the handoff protocol behind sessions numbered through 473, model routing, verification gates, and what each enforcement hook blocks |
| [`code/`](code/) | Whole files with their tests: vision pipeline, knowledge system, payments, coordinate privacy, trust, message guard, admin API and Sentry watcher, DeviceCheck credits, photo access, database, jobs, mobile |
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

**Determinism is a design choice, not a limitation.** One model call writes
anything in the product — the vision call that drafts a listing, where a wrong
answer costs the user an edit. Policy answering uses a model only to *find*
text: one embedding call ranks policy passages by meaning alongside full-text
search. **Zero model calls write the answer**, because there a wrong answer is
a false statement about someone's money, and the composer refuses rather than
improvise. [`02-architecture/ai-boundary.md`](02-architecture/ai-boundary.md)
argues both sides;
[`02-architecture/hybrid-retrieval.md`](02-architecture/hybrid-retrieval.md)
shows the retrieval half, including what it does not yet test.

## What's excluded, and why

- **Secrets, keys, hosts, buckets and account identifiers** — scanned for by
  regex and by hand; every finding is recorded in [`MANIFEST.md`](MANIFEST.md).
- **The scam-detection rule table** — publishing the patterns publishes the
  evasion recipe. The normalizer that decodes evasion *before* the patterns run
  is kept in full, because that is where the engineering is.
- **The real policy corpus** — replaced by three synthetic documents so the
  runnable package works.
- **The construction-company platform's code** — described, not published.
- **The operator console's front end** — described, not published: it embeds
  production hosts and project identifiers. The admin API behind it is published.
- **Internal control documents** — backlog, current-state, build map. Cited by
  line where a decision needs them.

The trust and strike constants were withheld in September. They are published
now: they were already readable in the published tests and in user-facing
notice copy, so withholding them protected nothing. See
[`MANIFEST.md`](MANIFEST.md) §1.2.

Every removal is itemised with file and line range in
[`MANIFEST.md`](MANIFEST.md).

## Honesty notes

This is pre-launch software in active development. There is no CI at this
commit; there are no automated mobile tests — every mobile surface is verified by a recorded device walk (see 05-process/verification-gates.md); the double-capture guards are read-then-write
with no row lock on the capture path; arrival confirmation is client-reported.
The embedding half of Help search has no test, and the recorded evals are
text-only. Block enforcement is 14 helper call sites plus 4 inlined feed
queries; an earlier résumé draft said "sixteen call sites", the résumé states no
count, and [`LIMITATIONS.md`](LIMITATIONS.md) shows the command.

I am the sole *human* code author of Zelbi. It was built with AI coding
assistants under my direction; architecture, decisions, review and release
authority stayed with me. Both halves of that sentence matter.

## Licence

All rights reserved — Zelbi material and the [`tooling/`](tooling/) bundle alike.
Published for review by prospective employers; not licensed for reuse. See
[`LICENSE`](LICENSE).

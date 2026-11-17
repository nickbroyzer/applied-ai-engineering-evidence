# Applied AI engineering — evidence

Nick Broyzer · Seattle Metro, WA · [linkedin.com/in/nickbroyzer](https://linkedin.com/in/nickbroyzer)

I build production software end to end and I write down why. This repository is
the evidence behind my résumé: the product logic, the architecture, the
decisions with their trade-offs, the debugging, the process that made
AI-assisted delivery reliable — and the code, with its tests.

The systems themselves are private. This is what can be shown.

**Status:** Zelbi is live on the App Store (iPhone) since 2026-11-04. As of
2026-11-16: 37 sign-ups and 16 listings from 4 people in the first 12 days after
launch, and no real pickup completed yet. My own and test accounts are excluded
from those figures.

**Full repository walkthrough available on request during interviews.**

## Six verified numbers

Every one re-derived on 2026-11-17 at commit `4772472b`, with the command that
produced it in [`verification/repo-metrics-2026-11-17.md`](verification/repo-metrics-2026-11-17.md).
The October figures, at `8875721`, and the September figures, at `3413d028`, are
kept beside them as history.

| | |
|---|---|
| **2,484** | commits, one Git author, 2026-04-09 → 2026-11-16 |
| **188** | active development days (222 calendar days) |
| **2,565** | backend tests, passed locally on 2026-11-17 from a clean checkout with outbound network blocked at the socket layer — [verbatim run](verification/pytest-summary-2026-11-17.txt). On CI at the same commit: `2554 passed, 11 skipped` — the 11 need a GeoLite2 file the runner doesn't have — [CI run](verification/ci-run-2026-11-17.md) |
| **74** | Alembic migrations |
| **639** | numbered decisions in the log; 61 published here |
| **22 / 22** | golden evaluation cases, **0 leak failures** — and you can run it yourself: [`runnable/knowledge-eval/`](runnable/knowledge-eval/) |

## The system

Zelbi is a location-based giveaway marketplace. Items are free; the picker pays
a small claim fee, taken as a card authorization hold, so that "I'll take it"
means something to the person waiting at the door.

```
  React Native / Expo client — 43 route screens
                    │
                    ▼
  FastAPI — 28 routers, 35 services, per-route rate limiting
    │         │            │             │              │
    ▼         ▼            ▼             ▼              ▼
  Postgres  Photos     Money path     AI boundary   Knowledge
  +PostGIS  private,   authorize/     two model     1 embedding
  74 revs   signed     capture/void/  calls: the    call finds
            URLs only  refund/        vision call   text; NO model
                       webhooks/      with its      writes the
                       sweepers       restricted-   answer. RUNNABLE →
                                      item flag;
                                      the support
                                      agent's tool
                                      loop
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
    2 cron runners      error reporting on API and
    (10-min + daily)    both crons; Sentry webhook
                        into the admin console
```

Full picture: [`02-architecture/system-overview.md`](02-architecture/system-overview.md).

## How to read this in ten minutes

**Case studies.** [`06-case-studies/INDEX.md`](06-case-studies/INDEX.md) — nine
short write-ups of problems found and fixed, each with its commits, tests and
decisions: a reminder that had never fired, consent recorded before anyone
agreed, an App Store rejection answered with walk data, a support agent's
scored rounds. Start here.

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
is 61 decisions as *question → ruling → what shipped*, including the ones that
reversed earlier decisions and the ones that ruled against building something.

## What's here

| | |
|---|---|
| [`01-product-logic/`](01-product-logic/) | The claim state machine, a 22-row failure-state matrix, the trust and safety model, location privacy, DeviceCheck-gated credits, private photo access |
| [`02-architecture/`](02-architecture/) | System overview, the AI boundary, hybrid Help retrieval, the admin API and Sentry watcher, data and migrations, the money path, and the trade-offs with what each one cost |
| [`03-decisions/`](03-decisions/) | 61 decision records, verbatim, by theme — money, trust, privacy, ai, ops |
| [`04-troubleshooting/`](04-troubleshooting/) | Five production write-ups: symptom → diagnosis → fix → test → commit. Plus excerpts from the lessons files |
| [`06-case-studies/`](06-case-studies/) | Nine case studies: what broke, the cause, the fix, the test, the commit and the decision |
| [`05-process/`](05-process/) | The behavioural rulebook, the handoff protocol behind sessions numbered through 494, model routing, verification gates, and what each enforcement hook blocks |
| [`code/`](code/) | Short excerpts, not whole files: in each subfolder an `EXCERPTS.md` with the passages the write-ups and case studies cite, each with its source path and Zelbi commit. Full source of the core systems is not published — show the work, not the recipe |
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

**Determinism is a design choice, not a limitation.** Two model calls write
anything in the product. The giver reviews and edits every listing draft before
it is posted. The support agent's decisions wait for a person, with one
exception: after 23 hours with no action it may carry out a decision that can
be undone, and it can never suspend anyone or move money. The vision call
drafts a listing and, in the same call, flags an item the rules don't allow; a
wrong answer costs the user an edit. The support agent's tool loop reads a
trust-and-safety report and proposes a decision that a person approves, or at
hour 23 an undoable one; the one line of its text a user can see passes a leak guard. Policy answering uses a model only to *find*
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
  is shown in [`code/message_guard/EXCERPTS.md`](code/message_guard/EXCERPTS.md),
  because that is where the engineering is.
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

This is software in active development, live for less than two weeks, with
little real use yet. CI runs the backend suite and the mobile Node tests on
every push ([`verification/ci-run-2026-11-17.md`](verification/ci-run-2026-11-17.md));
beyond those three Node test files there are no automated mobile tests — every mobile surface is verified by a recorded device walk (see 05-process/verification-gates.md); the double-capture guards are read-then-write
with no row lock on the capture path; arrival confirmation is client-reported.
The embedding half of Help search now has tests, with the embedding provider
stubbed, but the recorded evals are text-only. Block enforcement is 17 helper
call sites plus 4 inlined feed queries; an earlier résumé draft said "sixteen
call sites", the résumé states no count, and [`LIMITATIONS.md`](LIMITATIONS.md)
shows the command.

I am the sole *human* code author of Zelbi. It was built with AI coding
assistants under my direction; architecture, decisions, review and release
authority stayed with me. Both halves of that sentence matter.

## Licence

All rights reserved — Zelbi material and the [`tooling/`](tooling/) bundle alike.
Published for review by prospective employers; not licensed for reuse. See
[`LICENSE`](LICENSE).

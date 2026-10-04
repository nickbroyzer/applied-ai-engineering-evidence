# knowledge-eval — a policy retrieval-and-refusal system you can run

This is the knowledge system from Zelbi, extracted whole, with a synthetic
corpus in place of the real one. It answers policy questions from a tiered
document set, refuses anything it should not answer, and grades itself against
a golden set with an adversarial half.

**No model writes an answer, and this package calls no network.** Retrieval is
PostgreSQL full-text search with a keyword fallback; the answer is composed from
retrieved text by code. That is the design decision the package exists to show:
*where a wrong answer is a safety problem, determinism beats fluency.*

## What production adds, and why it is off here

Since Session 463 production retrieval has a second path: one Voyage embedding
call for the question, cosine similarity over stored chunk embeddings, and the
two ranked lists fused by reciprocal rank. The code for it is in this package,
verbatim — `app/services/knowledge/embeddings.py` and the vector branch of
`retrieval.py`. The full account is
[`../../02-architecture/hybrid-retrieval.md`](../../02-architecture/hybrid-retrieval.md).

This package pins the embedding key to the empty string (`app/config.py`). With
no key, ingestion stores chunks without vectors and logs
`knowledge_embeddings_skipped`; at query time `_vector_candidates` finds no
embedded chunks and returns before any network call (`retrieval.py:209-210`),
so the text-only order stands. **Everything recorded below is text-only
retrieval.** The vector path is not exercised here — and it is not exercised by
any test in the private repository either, which is stated rather than papered
over.

The answer side is identical in both modes: no model writes anything.

## Run it

```bash
createdb knowledge_eval_test
psql -d knowledge_eval_test -c 'CREATE EXTENSION "uuid-ossp";'

python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

export TEST_DATABASE_URL='postgresql://localhost/knowledge_eval_test'
pytest
```

Then the eval itself, against the same database (the tests truncate it, so
ingest and seed first; `--repo-root .` points ingestion at this package's
`docs/policy/`, since the script's default is the private repository's layout):

```bash
export DATABASE_URL="$TEST_DATABASE_URL"
python -m scripts.ingest_policy_docs --repo-root .
python -m scripts.seed_eval_cases
python -m scripts.run_knowledge_answer_eval
```

PostgreSQL is required; SQLite cannot run this. Retrieval uses
`to_tsvector` / `websearch_to_tsquery` / `ts_rank` and array containment, and
the visibility rules are enforced as SQL predicates and check constraints —
moving them to a database that lacks those would mean weakening the thing under
test.

No API key is needed, and none is read.

## Recorded run — 2026-10-03

Package code at Zelbi `8875721`. Machine: macOS (Darwin 25.6.0), Python
3.12.13, local PostgreSQL, a fresh virtualenv from `requirements.txt`. Outbound
network blocked at the socket layer for every command below:
`socket.connect`, `socket.connect_ex` and `socket.getaddrinfo` are patched to
permit loopback and AF_UNIX only and to raise `BlockedNetwork` for anything else
(`netblock.py`; loaded with `-p netblock` for pytest and imported first for the
scripts).

```
$ TEST_DATABASE_URL='postgresql://localhost/knowledge_eval_test' \
    PYTHONPATH=. python -m pytest -q -p netblock
........................................................................ [ 63%]
.........................................                                [100%]
113 passed in 3.55s
```

Exit code 0. 113 is pytest's collected count across the six test files.

### The eval itself

```
$ python -m scripts.ingest_policy_docs --repo-root .
knowledge_embeddings_skipped reason=VOYAGE_API_KEY is not set
status: succeeded
docs seen: 2
docs ingested: 2
docs skipped (unchanged): 0
docs rejected: 0
chunks written: 2
embeddings created: 0 (Phase 3)
$ python -m scripts.seed_eval_cases
cases in seed file: 22 (12 answer, 10 refuse_and_route)
created: 22
updated: 0
skipped (unchanged): 0
$ python -m scripts.run_knowledge_answer_eval
(22 PASS lines)
answer eval run: 86ec1e60-373b-4eed-8d5e-2dbc4038a4e4 (generation_model=deterministic-composer-v1)
cases: 22 total, 22 passed, 0 failed
leak failures: 0 (any value > 0 blocks release)
```

Every command exited 0. The retrieval-only eval (`scripts.run_knowledge_retrieval_eval`)
gives the same: 22 total, 22 passed, 0 leak failures, exit 0. Twenty-two golden
cases: **12 answer, 10 refusal/adversarial** — the same split as the private set.
The 2026-09-03 run at `3413d028` recorded the same results.

`generation_model=deterministic-composer-v1` is not a model name. It is the
version tag of the deterministic composer, and it doubles as the discriminator
that keeps answer-eval runs from being confused with retrieval-only runs, which
store `NULL` there.

### Exit codes, and what happened when I tried to make it leak

The CLI returns **0** when every case passes, **1** on ordinary failures, and
**2** when `leak_failures > 0` — a distinct code because a leak is a release
blocker and an ordinary failure is not.

Reaching code 2 turned out to be harder than expected, which is the most
interesting result in this package. Three separate injections, each restored
afterwards (recorded 2026-09-03):

| Injection | Expected | What actually happened |
|---|---|---|
| Add `"branch"` to a passing case's `must_not_include`, where the answer plainly says "branch" | leak → exit 2 | The composer **sanitised the H2 section away** before grading. Result: exit 1, `leak failures: 0`. |
| Add the case's own grounding document to its `forbidden_doc_paths` | leak → exit 2 | The composer **refused rather than cite it**. Exit 1, `leak failures: 0`. |
| Add a decision the answer legitimately cites to `forbidden_source_decisions` | leak → exit 2 | Refused again. Exit 1, `leak failures: 0`. |

The composer fails closed: when it cannot produce an answer that satisfies the
case's constraints, it refuses instead of emitting something that violates
them. So a leak cannot be induced through the eval-case contract at all — the
grader's leak counter exists to catch a regression in layers *upstream* of it.

To confirm the exit-2 wiring is real rather than dead code, the grader itself
was stubbed to report one leak:

```
FAIL  [public] return-branch  ← SIMULATED leak for exit-code verification
cases: 22 total, 21 passed, 1 failed
leak failures: 1 (any value > 0 blocks release)
CLI exit code: 2
```

## What is synthetic, and what is not

**Not synthetic — copied verbatim from the private repository at commit
`8875721`:** every module under `app/services/knowledge/` (including
`embeddings.py`), the router (`app/routers/knowledge.py`), the schemas, the
CLI scripts' logic (each carries one added comment marking the package root), and the six knowledge tables in
`app/models.py` including every check constraint and index.

**Synthetic, and clearly marked as such:**

- `docs/policy/` — three invented documents about a tool-lending library, in
  place of the real policy documents. One per tier, which is what keeps every
  tier rule demonstrable: the internal document is never ingested, so the
  corpus stores 2 of 3.
- `app/data/knowledge_eval_cases.json` — 22 invented questions in the same
  contract and the same 12/10 split.
- `app/config.py` (the empty embedding key), `app/services/api_abuse.py` (logs
  instead of writing an operator alert), `app/models.py`'s `User`,
  `app/routers/admin.py`, `app/main.py`, `app/database.py`,
  `app/dependencies.py`, `conftest.py` — small shims that stand in for platform
  pieces this package does not contain. Each says so in its own docstring.
  Production also requires a signed-in account and rate-limits `/knowledge/ask`
  in its `main.py`; this package's `main.py` mounts the router alone.

The test files were adapted from the private repository's at `3413d028` and
re-pointed at the synthetic corpus: paths, counts, and the questions the
parametrised cases name. **No assertion was weakened and no test was removed.**
The private tests changed since then in two ways, neither of which applies
here: new wording and document counts for the real corpus, and an autouse
sign-in fixture for production's account requirement. Every edit is itemised in
`../../MANIFEST.md`.

Two adaptations were forced by real properties of the system, and both are
worth knowing:

1. **Question text is not unique across the golden set.** The adversarial pairs
   seed related questions on both indexes, so `test_public_cases_use_public_index`
   looks up `(question, index)` rather than question alone.

2. **The refusal matcher is index-independent by design** — a question seeded as
   a leak probe is refused on *every* index, so elevated privilege never unlocks
   never-tier material. That means a *word-identical* public-refuse / CX-answer
   pair is impossible: it would refuse on both sides. The adversarial probe
   `probe-cx-material-from-public` therefore asks for the CX document's subject
   in different words, so the refusal comes from the SQL visibility predicate
   and the relevance floor — which is the property actually under test.

## What the 22 cases cover

The 12 answer cases include two deliberate positive controls, because a system
that refuses everything would pass a leak test trivially. Over-refusal on those
fails the run.

The 10 refusal cases are adversarial, not merely out-of-scope: direct requests
for the internal document's subject, a request that names the internal path
outright, a request for the deny-listed decision on both indexes, an
instruction-override attempt, a claimed-authority attempt inside the question
body, and one genuinely out-of-scope question that must refuse through the
relevance floor rather than the probe list.

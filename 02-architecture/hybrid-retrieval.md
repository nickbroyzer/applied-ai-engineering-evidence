# Help search — hybrid retrieval, deterministic answers

One embedding call to find the policy text. Zero model calls to write the
answer.

Code excerpts: [`../code/knowledge/EXCERPTS.md`](../code/knowledge/EXCERPTS.md),
from `retrieval.py`, `embeddings.py` and `answer.py` at Zelbi `4772472b`.
Runnable, text-only: [`../runnable/knowledge-eval/`](../runnable/knowledge-eval/).
All line numbers below are at Zelbi `8875721`.

## What changed since September

In September the Help system ranked policy text with PostgreSQL full-text search
and a keyword fallback, and called no model at all. In Session 463 a second
retrieval path was added beside it: **meaning search over Voyage embeddings,
fused with the text ranking by reciprocal rank**. The answer side did not
change. No model writes an answer; the composer still builds it from retrieved
text by code, and still refuses rather than answering weakly.

So the old sentence "the knowledge system calls no model" is no longer true,
and this repository no longer says it. The accurate sentence is the one at the
top of this page.

## The two paths, behind one `WHERE`

`retrieve()` (`retrieval.py:241-308`) builds one list of filters for the
caller's index and hands the **same list** to every path:

| Path | Where | What ranks it |
|---|---|---|
| Full-text | `_fts_candidates`, filters applied at `retrieval.py:166` | `websearch_to_tsquery` + `ts_rank` |
| Keyword fallback | `_keyword_candidates`, `retrieval.py:191` | occurrence count; fills slots full-text left empty |
| Meaning | `_vector_candidates`, `retrieval.py:199-219`, filters at :205 | cosine similarity to the question's embedding |

The filters (`_visibility_filters`, `retrieval.py:95-118`) are the September
design unchanged: the public index requires three columns to agree, internal
documents and deny-listed decisions are excluded in SQL, and the results are
re-checked in Python on the way out (`_assert_safe`, called at :307). The vector
path did not get its own access rules — it inherits the existing ones, which is
the point. A public question cannot rank a restricted chunk by meaning any more
than by words.

## Fusion

The text list (full-text then keyword) and the vector list (top 8,
`VECTOR_TOP_N`) are fused by reciprocal rank: each chunk scores
`1 / (60 + rank)` in each list it appears in, summed (`RRF_K = 60`,
`retrieval.py:51`; fusion at :275-295). Ties break on document path and chunk
id, so a fixed corpus and question give a fixed order.

Reciprocal rank was chosen over mixing raw scores because `ts_rank` and cosine
similarity are not on comparable scales; ranks are.

## Grounding: when a meaning match is strong enough

The composer refuses unless the retrieved text is strong enough to ground an
answer (`_clears_relevance_floor`, `answer.py:271-296`). Before Session 463 that
meant a full-text hit, or at least two question keywords in one chunk. Now a
vector similarity at or above **0.45** also qualifies (`answer.py:282-285`).

The floor was calibrated on real questions: help questions that rely on meaning
alone scored 0.48 and up; off-topic ones topped out at 0.40
(`retrieval.py:52-54`).

**Why it was added.** On a set of 24 real help questions, text-only retrieval
refused 6 and put the right article first on about 14. With meaning search fused
in: no refusals, and the right article first on all 24. That measurement is
recorded in the decision log (D537, not published here); it was not re-run for
this repository and is not part of the golden eval.

## Cost and failure: the path is optional

- **At most one embedding call per question** — the question itself
  (`retrieval.py:214`). Documents are embedded once, at ingestion, in a single
  batched call (`ingestion.py:264-272`).
- **No key, a network error, or a malformed response** raises
  `EmbeddingUnavailable` (`embeddings.py:20-41`, 8-second timeout at :17). The
  vector path returns nothing and the text order stands (`retrieval.py:213-216`).
  Ingestion logs a warning and stores the chunks without vectors
  (`ingestion.py:267-268`).
- **A daily ceiling** (`VOYAGE_DAILY_CEILING = 1000`, `retrieval.py:58`, D538).
  Past it, search is text-only until midnight UTC (:211-212). It is counted from
  the query log, so restarts and multiple servers cannot reset it (:55-68).
- **Alerts at 80% and 100%** of the ceiling go to the operator dashboard's
  signal feed, once each per UTC day (`routers_knowledge.py:96-119`).
- **Signed-in accounts only, 30 questions an hour each** (`main.py:82-85`, not
  published).

## Honest limits

Named plainly, because the absences are part of the design record:

- **No pgvector, no vector index.** Embeddings are stored as a nullable
  `ARRAY(Float)` column, labelled in the model as a placeholder until pgvector is
  available (`models.py:775-777`; migration `f42fad93de29`, lines 9-11 and 157).
  The vector path loads every embedded chunk that passes the visibility filter
  and computes cosine similarity in Python (`retrieval.py:203-219`,
  `embeddings.py:44-48`). That is fine for a corpus of fifteen documents and
  would not be at scale.
- **The ceiling counts questions, not Voyage calls.** It counts every logged
  question for the day — including ones that never reached Voyage (no key, no
  vectors, a matched refusal probe). It is therefore a conservative upper bound
  on query embeddings. It does not count ingestion or eval-harness calls, and the
  check-then-call is not atomic.
- **The vector path was untested at `8875721`.** No backend test exercised
  embedding, fusion, the ceiling or the alerts. Since `0cd7e3ce` (2026-11-16),
  seven tests in `tests/test_knowledge_hybrid_path.py` cover the vector half,
  fusion, the similarity floor, the fallback to text and the daily ceiling, with
  the embedding provider stubbed; the ceiling's 80% and 100% alerts are tested
  only as rows in the admin health view. The other knowledge tests still assume
  no key is present; four of them fail if one is (`backend/lessons.md`,
  2026-10-03), which is why the recorded suite run blanks it.
- **The golden eval runs text-only.** Both evals call the real `retrieve()`
  (`retrieval_eval.py:78`, `answer_eval.py:92`), so with a key and stored
  vectors they would go hybrid. But the recorded runs here have neither, and the
  eval run row stores `embedding_model=None` regardless (`answer_eval.py:184`).
  **22/22 with zero leaks describes text-only retrieval.**
- **Every typed question goes to a third party.** With a key configured, the
  question text is sent to Voyage AI to be embedded (D537 records that the
  privacy policy must name it).
- **Stale docstrings.** Several module docstrings still say "no embeddings"
  (`retrieval.py:15,25,250-251`, `answer.py:4`, `routers_knowledge.py:3-4`,
  `ingestion.py:3,16-17`). Two of them are quoted verbatim in the excerpts;
  this page is the correction.

## What is never claimed

That a model writes any Help answer. RAG in the generative sense. pgvector, a
vector index, or vector search at scale. That the golden eval measures hybrid
ranking.

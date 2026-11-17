# `code/knowledge/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Visibility is a SQL predicate, on every path

`backend/app/services/knowledge/retrieval.py`, lines 1–20, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 02-architecture/hybrid-retrieval.md.

```python
"""Phase 4 (retrieval only): deterministic text search over knowledge_chunks.

Implements the filter-first half of 14-rag-ingestion-architecture.md §9–§10
without embeddings or generation:

- The visibility predicate is part of the SQL WHERE clause, never a
  post-filter (§4): a public query physically cannot rank a CX chunk.
- Public index requires rag_index = 'public' AND audience = 'public' AND
  public_rag_safe = true (belt and suspenders — all three must agree).
- CX index allows rag_index IN ('public', 'cx') AND audience IN
  ('public', 'cx').
- Internal docs and deny-listed decisions (D212) are additionally excluded
  in SQL and re-asserted on every result before it is returned.

Ranking is deterministic text-only (no vectors, no external APIs):

1. Postgres full-text search over the Phase 1 content_tsv generated column
   (websearch_to_tsquery + ts_rank).
2. Keyword/ILIKE fallback — occurrence-count scoring over lowercased
   content — used to fill remaining slots when FTS matches fewer than k
```

## Fusion constants and the daily embedding ceiling (D537, D538)

`backend/app/services/knowledge/retrieval.py`, lines 50–68, at `4772472b`. Cited by: 06-case-studies/07; 02-architecture/hybrid-retrieval.md.

```python
VECTOR_TOP_N = 8
RRF_K = 60
# Calibrated Session 463: real help questions that rely on meaning alone scored
# 0.48 and up; off-topic ones topped out at 0.40 ("how do I bake bread").
VECTOR_SIMILARITY_FLOOR = 0.45
# D538: at most this many help questions a day (UTC) are sent to Voyage; past it,
# search falls back to text only, which costs nothing. Counted from the query log,
# so restarts and multiple servers cannot reset it.
VOYAGE_DAILY_CEILING = 1000


def voyage_calls_today(session: Session) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        session.query(func.count(models.KnowledgeQueryLog.id))
        .filter(models.KnowledgeQueryLog.created_at >= start)
        .scalar()
        or 0
    )
```

## The visibility filters

`backend/app/services/knowledge/retrieval.py`, lines 95–118, at `4772472b`. Cited by: 02-architecture/hybrid-retrieval.md.

```python
def _visibility_filters(index: str) -> list:
    """The hard SQL predicate for one index. Caller-determined, never widened."""
    chunk = models.KnowledgeChunk
    if index == "public":
        filters = [
            chunk.rag_index == "public",
            chunk.audience == "public",
            chunk.public_rag_safe.is_(True),
        ]
    elif index == "cx":
        filters = [
            chunk.rag_index.in_(("public", "cx")),
            chunk.audience.in_(("public", "cx")),
        ]
    else:
        raise ValueError(f"unknown index {index!r}; expected 'public' or 'cx'")
    # Structurally impossible rows (ingestion rejects them, constraints forbid
    # them) stay unreachable even if either of those layers ever regresses.
    filters.append(~chunk.doc_path.like(f"{INTERNAL_DIR}/%"))
    for denied in DENYLISTED_DECISIONS:
        filters.append(
            or_(chunk.source_decisions.is_(None), ~chunk.source_decisions.any(denied))
        )
    return filters
```

## The vector half, inside the same filter

`backend/app/services/knowledge/retrieval.py`, lines 199–219, at `4772472b`. Cited by: 02-architecture/hybrid-retrieval.md; 06-case-studies/07.

```python
def _vector_candidates(session: Session, query: str, filters: list, limit: int):
    """Top chunks by meaning (§9 step 2), inside the same visibility filter.
    Empty when no chunk has a vector yet or Voyage is unreachable."""
    chunk = models.KnowledgeChunk
    rows = (
        session.query(chunk)
        .filter(*filters)
        .filter(chunk.embedding.isnot(None), chunk.embedding_model == EMBEDDING_MODEL)
        .all()
    )
    if not rows:
        return []
    if voyage_calls_today(session) >= VOYAGE_DAILY_CEILING:
        return []
    try:
        [query_vector] = embed_texts([query], "query")
    except EmbeddingUnavailable:
        return []
    scored = [(row, cosine(query_vector, row.embedding)) for row in rows]
    scored.sort(key=lambda pair: (-pair[1], pair[0].doc_path, pair[0].chunk_index))
    return scored[:limit]
```

## Reciprocal rank fusion

`backend/app/services/knowledge/retrieval.py`, lines 268–297, at `4772472b`. Cited by: 06-case-studies/07; 02-architecture/hybrid-retrieval.md.

```python
        keywords = extract_keywords(query)
        for chunk, score in _keyword_candidates(session, keywords, filters, fetch):
            if chunk.id in seen_ids:
                continue
            candidates.append(_to_result(chunk, score, "keyword"))
            seen_ids.add(chunk.id)

    # §9: fuse meaning search with text search when vectors exist; otherwise the
    # text-only order above stands unchanged.
    vector_hits = _vector_candidates(session, query, filters, VECTOR_TOP_N)
    if vector_hits:
        similarity = {row.id: sim for row, sim in vector_hits}
        fused: dict[uuid.UUID, float] = {}
        by_id: dict[uuid.UUID, RetrievedChunk] = {}
        for rank, item in enumerate(candidates, start=1):
            fused[item.chunk_id] = fused.get(item.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
            by_id[item.chunk_id] = dataclasses.replace(
                item, similarity=similarity.get(item.chunk_id)
            )
        for rank, (row, sim) in enumerate(vector_hits, start=1):
            fused[row.id] = fused.get(row.id, 0.0) + 1.0 / (RRF_K + rank)
            if row.id not in by_id:
                by_id[row.id] = _to_result(row, sim, "vector")
                by_id[row.id] = dataclasses.replace(by_id[row.id], similarity=sim)
        candidates = sorted(
            by_id.values(),
            key=lambda item: (-fused[item.chunk_id], item.doc_path, item.chunk_id.hex),
        )

    results: list[RetrievedChunk] = []
```

## The embedding call

`backend/app/services/knowledge/embeddings.py`, lines 1–40 (first 40 lines of the function), at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 02-architecture/hybrid-retrieval.md.

```python
"""Voyage embeddings for the knowledge base (14-rag-ingestion-architecture.md §8).

One model for the whole corpus; documents and questions use Voyage's input_type
flag. Any failure raises EmbeddingUnavailable so callers fall back to text search.
Session 463.
"""
from __future__ import annotations

import math

import httpx

from app.config import settings

EMBEDDING_MODEL = "voyage-3.5"
_URL = "https://api.voyageai.com/v1/embeddings"
_TIMEOUT_SECONDS = 8.0


class EmbeddingUnavailable(Exception):
    """No key, a network error, or a malformed response."""


def embed_texts(texts: list[str], input_type: str) -> list[list[float]]:
    if not settings.voyage_api_key:
        raise EmbeddingUnavailable("VOYAGE_API_KEY is not set")
    if not texts:
        return []
    try:
        response = httpx.post(
            _URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={"input": texts, "model": EMBEDDING_MODEL, "input_type": input_type},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
```

## The deterministic composer: no model writes the answer

`backend/app/services/knowledge/answer.py`, lines 1–20, at `4772472b`. Cited by: README.md; 02-architecture/ai-boundary.md.

```python
"""Phase 5 (answer): deterministic answer composer over retrieved chunks.

Implements the closed-book half of 14-rag-ingestion-architecture.md §11–§13
with no LLM, no embeddings, and no external APIs:

- Answers are composed exclusively from retrieved knowledge_chunks text
  (§11.1) — never from model priors, templates aside. The only fixed prose
  is the refusal template and the unbuilt-feature note.
- Every non-refusal answer ends with a Sources block listing the doc paths
  and source decisions actually used (§13). Refusals carry no Sources block.
- Refusal / leak probes are recognized deterministically: a question that
  matches an active knowledge_eval_cases row with expected_behavior
  'refuse_and_route' is refused outright, whatever retrieval returns —
  never-tier material is unanswerable in every index (§12). Matching is
  index-independent on purpose: a probe refused on public is refused on CX.
- Answer cases matched against the golden set are grounded on their
  required_doc_paths and sanitized against their must_not_include patterns
  at H2-section granularity, so a doc section the matrix locked out of
  answers (e.g. claim-fee's "not a deposit" contrast copy) never surfaces
  even when the rest of its doc does.
```

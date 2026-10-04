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
   chunks (websearch AND-semantics can miss docs that phrase things
   differently).

Ties break on (doc_path, chunk_index) so identical corpora always return
identical results. Embeddings are Phase 3+ work and are not consulted.
"""
from __future__ import annotations

import dataclasses
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, func, literal, or_
from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.embeddings import EMBEDDING_MODEL, EmbeddingUnavailable, cosine, embed_texts
from app.services.knowledge.validation import DENYLISTED_DECISIONS, SafetyViolation

INTERNAL_DIR = "docs/policy/internal"
DEFAULT_TOP_K = 5
# §9.6 — one long doc must not crowd out a second relevant doc.
MAX_CHUNKS_PER_DOC = 3
SNIPPET_CHARS = 240
# §9: vector search runs beside text search; the two ranked lists are fused by
# reciprocal rank. The floor is the meaning-match strength an answer must reach
# when text search found nothing exact (calibrate with the eval harness).
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

_TOKEN_RE = re.compile(r"[a-z0-9$@.']+")
_STOPWORDS = frozenset(
    """
    a an and are as at be but by can could do does for from get has have how
    i if in is it its me my not of on or our so that the their them then
    there these they this to was we what when where which who why will with
    would you your
    """.split()
)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    doc_path: str
    title: str
    heading_path: str | None
    source_decisions: tuple[str, ...]
    rag_index: str
    score: float
    strategy: str  # 'fts' | 'keyword' | 'vector'
    snippet: str
    similarity: float | None = None


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


def extract_keywords(query: str) -> list[str]:
    """Lowercased, stopword-stripped tokens, deduplicated in query order."""
    seen: set[str] = set()
    keywords: list[str] = []
    for token in _TOKEN_RE.findall(query.lower()):
        if len(token) < 2 or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _escape_like(keyword: str) -> str:
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _snippet(content: str) -> str:
    """First SNIPPET_CHARS of the chunk body (context header stripped)."""
    body = content.split("\n\n", 1)[1] if "\n\n" in content else content
    body = " ".join(body.split())
    if len(body) <= SNIPPET_CHARS:
        return body
    return body[:SNIPPET_CHARS].rstrip() + "…"


def _to_result(chunk: models.KnowledgeChunk, score: float, strategy: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk.id,
        doc_path=chunk.doc_path,
        title=chunk.title,
        heading_path=chunk.heading_path,
        source_decisions=tuple(chunk.source_decisions or ()),
        rag_index=chunk.rag_index,
        score=float(score),
        strategy=strategy,
        snippet=_snippet(chunk.content),
    )


def _fts_candidates(session: Session, query: str, filters: list, limit: int):
    chunk = models.KnowledgeChunk
    tsquery = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank(chunk.content_tsv, tsquery)
    return (
        session.query(chunk, rank.label("score"))
        .filter(*filters)
        .filter(chunk.content_tsv.op("@@")(tsquery))
        .order_by(rank.desc(), chunk.doc_path.asc(), chunk.chunk_index.asc())
        .limit(limit)
        .all()
    )


def _keyword_candidates(session: Session, keywords: list[str], filters: list, limit: int):
    """Occurrence-count scoring: sum over keywords of how often each appears."""
    if not keywords:
        return []
    chunk = models.KnowledgeChunk
    lowered = func.lower(chunk.content)
    score = literal(0.0)
    any_match = []
    for keyword in keywords:
        pattern = f"%{_escape_like(keyword)}%"
        occurrences = (
            func.length(lowered) - func.length(func.replace(lowered, keyword, ""))
        ) / len(keyword)
        score = score + case((chunk.content.ilike(pattern, escape="\\"), occurrences), else_=0.0)
        any_match.append(chunk.content.ilike(pattern, escape="\\"))
    return (
        session.query(chunk, score.label("score"))
        .filter(*filters)
        .filter(or_(*any_match))
        .order_by(score.desc(), chunk.doc_path.asc(), chunk.chunk_index.asc())
        .limit(limit)
        .all()
    )


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


def _assert_safe(results: list[RetrievedChunk], index: str) -> None:
    """Re-verify in Python what the SQL already guarantees. Fail closed."""
    allowed = ("public",) if index == "public" else ("public", "cx")
    for item in results:
        if item.doc_path.startswith(INTERNAL_DIR + "/"):
            raise SafetyViolation(f"retrieval returned internal doc {item.doc_path}")
        if item.rag_index not in allowed:
            raise SafetyViolation(
                f"retrieval for index {index!r} returned {item.rag_index!r} chunk "
                f"{item.chunk_id} ({item.doc_path})"
            )
        denied = DENYLISTED_DECISIONS.intersection(item.source_decisions)
        if denied:
            raise SafetyViolation(
                f"retrieval returned deny-listed decision(s) {sorted(denied)} "
                f"via {item.doc_path}"
            )


def retrieve(
    session: Session,
    query: str,
    index: str,
    *,
    k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Top-k chunks for one query under one index's hard visibility filter.

    Returns metadata and snippets only — no answer generation, no LLM, no
    embeddings. Deterministic for a fixed corpus and query.
    """
    filters = _visibility_filters(index)
    if not query.strip():
        return []

    fetch = max(k * 4, k + MAX_CHUNKS_PER_DOC)
    candidates: list[RetrievedChunk] = []
    seen_ids: set[uuid.UUID] = set()

    for chunk, score in _fts_candidates(session, query, filters, fetch):
        candidates.append(_to_result(chunk, score, "fts"))
        seen_ids.add(chunk.id)

    # Fallback keyword pass fills slots FTS left empty (or all of them when
    # the query has no FTS match at all).
    if len(candidates) < fetch:
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
    per_doc: dict[str, int] = {}
    for item in candidates:
        if per_doc.get(item.doc_path, 0) >= MAX_CHUNKS_PER_DOC:
            continue
        per_doc[item.doc_path] = per_doc.get(item.doc_path, 0) + 1
        results.append(item)
        if len(results) >= k:
            break

    _assert_safe(results, index)
    return results

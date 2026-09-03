"""Phase 6A: HTTP surface for the deterministic knowledge answer composer.

Implements the router half of 14-rag-ingestion-architecture.md §10 with no
LLM, no embeddings, and no external APIs:

- POST /knowledge/ask — unauthenticated public endpoint. Always queries the
  literal 'public' index; a request naming any other tier is rejected with
  403 before retrieval runs. The tier is route-determined, never widened by
  a request parameter.
- POST /knowledge/cx/ask — CX endpoint behind the same auth wall as existing
  admin routes (reuses require_admin, §10). Always queries the 'cx' index.
- Every request writes a knowledge_query_logs row (index_used, caller_role,
  outcome, cited paths) — the audit trail §10 relies on if a leak is ever
  suspected. Logging is best-effort: a logging failure never breaks the
  answer.
- matched_case_slug is returned only for answered outcomes; on refusals it
  is null because the matched golden case for a refusal is a leak probe and
  its slug must not confirm the probe (or the decision it targets) exists.
"""
import hashlib
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db
from app.routers.admin import require_admin
from app.schemas.knowledge import (
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    KnowledgeQuestion,
    KnowledgeSource,
)
from app.services.knowledge.answer import ComposedAnswer, compose_answer
from app.services.knowledge.answer_eval import GENERATION_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _log_query(
    db: Session,
    *,
    index: str,
    caller_role: str,
    caller_id_hash: str | None,
    composed: ComposedAnswer,
    latency_ms: int,
) -> None:
    try:
        db.add(
            models.KnowledgeQueryLog(
                index_used=index,
                caller_role=caller_role,
                caller_id_hash=caller_id_hash,
                query_text=composed.question,
                retrieved_chunk_ids=list(composed.used_chunk_ids),
                outcome=composed.outcome,
                answer_text=composed.answer_text,
                cited_doc_paths=list(composed.cited_doc_paths),
                model=GENERATION_MODEL,
                latency_ms=latency_ms,
            )
        )
        db.commit()
    except Exception:
        logger.exception("knowledge_query_log_write_failed")
        db.rollback()


def _ask(
    db: Session,
    question: str,
    index: str,
    *,
    caller_role: str,
    caller_id_hash: str | None = None,
) -> KnowledgeAskResponse:
    started = time.monotonic()
    composed = compose_answer(db, question, index)
    latency_ms = int((time.monotonic() - started) * 1000)
    _log_query(
        db,
        index=index,
        caller_role=caller_role,
        caller_id_hash=caller_id_hash,
        composed=composed,
        latency_ms=latency_ms,
    )
    refused = composed.refused
    return KnowledgeAskResponse(
        outcome="refused" if refused else "answered",
        answer=composed.answer_text,
        matched_case_slug=None if refused else composed.matched_case_slug,
        sources=[
            KnowledgeSource(
                doc_path=citation.doc_path,
                title=citation.title,
                source_decisions=list(citation.source_decisions),
            )
            for citation in composed.citations
        ],
        retrieval_count=len(composed.used_chunk_ids),
    )


@router.post("/ask", response_model=KnowledgeAskResponse)
def ask_knowledge(
    body: KnowledgeAskRequest,
    db: Session = Depends(get_db),
) -> KnowledgeAskResponse:
    if body.index != "public":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The public endpoint can only query the public index",
        )
    # Literal 'public', not body.index: the tier is route-determined (§10).
    return _ask(db, body.question, "public", caller_role="public")


@router.post("/cx/ask", response_model=KnowledgeAskResponse)
def ask_knowledge_cx(
    body: KnowledgeQuestion,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
) -> KnowledgeAskResponse:
    return _ask(
        db,
        body.question,
        "cx",
        caller_role="cx",
        caller_id_hash=hashlib.sha256(str(current_user.id).encode()).hexdigest(),
    )

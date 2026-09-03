"""
RAG Phase 1 schema/model tests (docs/agents/14-rag-ingestion-architecture.md §5).

Proves the structural visibility invariants at the database level:
'never'/'internal' rows cannot exist, public_rag_safe must agree with
rag_index, D212 can never be stored, chunks carry denormalized visibility
metadata, and query logs / eval cases record what §5 requires.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app import models


def _document_kwargs(**overrides) -> dict:
    kwargs = dict(
        doc_path=f"docs/policy/public/claim-fee-{uuid.uuid4().hex[:8]}.md",
        title="The $2 claim fee",
        audience="public",
        rag_index="public",
        public_rag_safe=True,
        source_decisions=["D214", "D23", "D24", "D9"],
        implementation_status="built",
        last_updated=date(2026, 7, 1),
        content_hash="a" * 64,
        raw_content="# The $2 claim fee\n\nBody text.",
    )
    kwargs.update(overrides)
    return kwargs


def _make_document(db_session, **overrides) -> models.KnowledgeDocument:
    doc = models.KnowledgeDocument(**_document_kwargs(**overrides))
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _expect_rejected(db_session, instance) -> None:
    db_session.add(instance)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# --- Documents: legal rows.


def test_public_document_row_created(db_session):
    doc = _make_document(db_session)
    assert doc.id is not None
    assert doc.rag_index == "public"
    assert doc.audience == "public"
    assert doc.public_rag_safe is True
    assert doc.created_at is not None


def test_cx_document_row_created(db_session):
    doc = _make_document(
        db_session,
        doc_path=f"docs/policy/cx/cx-dispute-resolution-{uuid.uuid4().hex[:8]}.md",
        title="CX: dispute resolution",
        audience="cx",
        rag_index="cx",
        public_rag_safe=False,
        source_decisions=["D209", "D61", "D64", "D65"],
        implementation_status="built_verified",
    )
    assert doc.rag_index == "cx"
    assert doc.public_rag_safe is False


# --- Documents: illegal rows are structurally impossible.


def test_rag_index_never_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(
            **_document_kwargs(rag_index="never", public_rag_safe=False, audience="public")
        ),
    )


def test_internal_audience_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(**_document_kwargs(audience="internal")),
    )


def test_public_doc_with_public_rag_safe_false_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(**_document_kwargs(public_rag_safe=False)),
    )


def test_cx_doc_with_public_rag_safe_true_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(
            **_document_kwargs(audience="cx", rag_index="cx", public_rag_safe=True)
        ),
    )


def test_d212_in_public_document_source_decisions_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(
            **_document_kwargs(source_decisions=["D214", "D212"])
        ),
    )


def test_d212_in_cx_document_source_decisions_rejected(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeDocument(
            **_document_kwargs(
                audience="cx",
                rag_index="cx",
                public_rag_safe=False,
                source_decisions=["D212"],
            )
        ),
    )


# --- Chunks.


def _chunk_kwargs(doc, **overrides) -> dict:
    kwargs = dict(
        document_id=doc.id,
        chunk_index=0,
        heading_path="The $2 claim fee > When you're charged",
        content="You're charged when you confirm pickup or if you don't show up.",
        token_count=32,
        rag_index=doc.rag_index,
        audience=doc.audience,
        public_rag_safe=doc.public_rag_safe,
        doc_path=doc.doc_path,
        title=doc.title,
        implementation_status=doc.implementation_status,
        content_hash="b" * 64,
        source_decisions=list(doc.source_decisions),
    )
    kwargs.update(overrides)
    return kwargs


def test_chunk_stores_denormalized_visibility_metadata(db_session):
    doc = _make_document(db_session)
    chunk = models.KnowledgeChunk(**_chunk_kwargs(doc))
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.document_id == doc.id
    assert chunk.doc_path == doc.doc_path
    assert chunk.rag_index == "public"
    assert chunk.audience == "public"
    assert chunk.public_rag_safe is True
    assert chunk.source_decisions == doc.source_decisions
    assert chunk.embedding is None
    assert chunk.content_tsv is not None  # generated tsvector column


def test_chunk_with_rag_index_never_rejected(db_session):
    doc = _make_document(db_session)
    _expect_rejected(
        db_session,
        models.KnowledgeChunk(
            **_chunk_kwargs(doc, rag_index="never", public_rag_safe=False)
        ),
    )


def test_chunk_with_internal_audience_rejected(db_session):
    doc = _make_document(db_session)
    _expect_rejected(
        db_session,
        models.KnowledgeChunk(**_chunk_kwargs(doc, audience="internal")),
    )


def test_chunk_with_d212_source_decisions_rejected(db_session):
    doc = _make_document(db_session)
    _expect_rejected(
        db_session,
        models.KnowledgeChunk(**_chunk_kwargs(doc, source_decisions=["D212"])),
    )


def test_chunk_requires_existing_document(db_session):
    doc = _make_document(db_session)
    _expect_rejected(
        db_session,
        models.KnowledgeChunk(**_chunk_kwargs(doc, document_id=uuid.uuid4())),
    )


def test_chunk_deleted_when_document_deleted(db_session):
    doc = _make_document(db_session)
    chunk = models.KnowledgeChunk(**_chunk_kwargs(doc))
    db_session.add(chunk)
    db_session.commit()
    chunk_id = chunk.id

    db_session.delete(doc)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(models.KnowledgeChunk, chunk_id) is None


def test_chunk_index_unique_per_document(db_session):
    doc = _make_document(db_session)
    db_session.add(models.KnowledgeChunk(**_chunk_kwargs(doc, chunk_index=0)))
    db_session.commit()
    _expect_rejected(
        db_session,
        models.KnowledgeChunk(**_chunk_kwargs(doc, chunk_index=0)),
    )


# --- Query logs.


def test_query_log_stores_retrieved_chunk_ids(db_session):
    doc = _make_document(db_session)
    chunk = models.KnowledgeChunk(**_chunk_kwargs(doc))
    db_session.add(chunk)
    db_session.commit()

    log = models.KnowledgeQueryLog(
        index_used="public",
        caller_role="anonymous",
        query_text="What is the $2 claim fee?",
        retrieved_chunk_ids=[chunk.id],
        top_similarity=0.82,
        outcome="answered",
        answer_text="Claiming an item places a $2 claim fee hold on your card.",
        cited_doc_paths=[doc.doc_path],
        model="claude-fable-5",
        latency_ms=1200,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.retrieved_chunk_ids == [chunk.id]
    assert log.index_used == "public"
    assert log.caller_role == "anonymous"


def test_query_log_requires_tier_and_role(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeQueryLog(
            index_used=None,
            caller_role="anonymous",
            query_text="q",
            retrieved_chunk_ids=[],
        ),
    )
    _expect_rejected(
        db_session,
        models.KnowledgeQueryLog(
            index_used="internal",
            caller_role="anonymous",
            query_text="q",
            retrieved_chunk_ids=[],
        ),
    )


# --- Eval cases.


def test_eval_case_stores_refusal_and_leak_probe_expectations(db_session):
    case = models.KnowledgeEvalCase(
        slug=f"d212-hold-expiry-probe-{uuid.uuid4().hex[:8]}",
        question="What happens if my card hold expires before pickup?",
        index_under_test="public",
        expected_audience="public",
        expected_behavior="refuse_and_route",
        forbidden_source_decisions=["D212"],
        forbidden_doc_paths=["docs/policy/internal/internal-money-timers.md"],
        must_include=["support@zelbi.ai"],
        must_not_include=[r"capture_before", r"auth(orization)? (expir|window)", r"sweeper"],
        notes="D212 probe — any substantive answer is a leak failure.",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    assert case.expected_behavior == "refuse_and_route"
    assert case.index_under_test == "public"
    assert "support@zelbi.ai" in case.must_include
    assert r"capture_before" in case.must_not_include
    assert case.active is True


def test_eval_case_requires_expected_audience_and_behavior(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeEvalCase(
            slug=f"missing-behavior-{uuid.uuid4().hex[:8]}",
            question="q",
            index_under_test="public",
            expected_behavior=None,
        ),
    )
    _expect_rejected(
        db_session,
        models.KnowledgeEvalCase(
            slug=f"bad-index-{uuid.uuid4().hex[:8]}",
            question="q",
            index_under_test="internal",
            expected_behavior="answer",
        ),
    )


# --- Ingestion + eval runs.


def test_ingestion_and_eval_run_rows(db_session):
    run = models.KnowledgeIngestionRun(git_commit="ae5de91", status="succeeded")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    assert run.docs_seen == 0
    assert run.started_at is not None

    doc = _make_document(db_session, ingestion_run_id=run.id)
    assert doc.ingestion_run_id == run.id

    eval_run = models.KnowledgeEvalRun(
        ingestion_run_id=run.id,
        git_commit="ae5de91",
        cases_total=20,
        cases_passed=20,
        cases_failed=0,
        leak_failures=0,
        results=[{"case_slug": "claim-fee-basic", "passed": True}],
    )
    db_session.add(eval_run)
    db_session.commit()
    db_session.refresh(eval_run)
    assert eval_run.leak_failures == 0
    assert eval_run.results[0]["case_slug"] == "claim-fee-basic"


def test_ingestion_run_rejects_unknown_status(db_session):
    _expect_rejected(
        db_session,
        models.KnowledgeIngestionRun(status="exploded"),
    )

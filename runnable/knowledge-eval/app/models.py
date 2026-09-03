"""Standalone SQLAlchemy models for the knowledge-eval package.

Copied verbatim from the private repository's `backend/app/models.py`: the six
knowledge tables below are byte-identical to production, including every check
constraint and index. What is NOT copied is the rest of that file — the
marketplace domain (users, listings, claims, messages, payments, trust) — which
this package does not touch. `User` below is a minimal stand-in carrying only
the two columns the CX route's admin gate reads; the production model has many
more.

The imports and `Base` are reconstructed here because the original file takes
them from `app.database`, which in production binds to a configured DSN.
"""
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """Minimal stand-in. Production carries the full marketplace user."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    email = Column(Text, nullable=False, unique=True)
    display_name = Column(Text, nullable=True)
    is_admin = Column(Boolean, nullable=False, server_default=text("false"))
    is_suspended = Column(Boolean, nullable=False, server_default=text("false"))




# --- RAG knowledge base (docs/agents/14-rag-ingestion-architecture.md §5) ---
#
# Visibility invariants enforced at the DB level, not just at ingestion:
# rag_index/audience may only be 'public' or 'cx' in stored rows ('never' /
# 'internal' content is rejected before storage and has no row to leak),
# public_rag_safe must be true iff rag_index = 'public', and D212 may never
# appear in any stored source_decisions.


class KnowledgeIngestionRun(Base):
    __tablename__ = "knowledge_ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    started_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    finished_at = Column(DateTime(timezone=True), nullable=True)
    git_commit = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default=text("'running'"))

    docs_seen = Column(Integer, nullable=False, server_default='0')
    docs_ingested = Column(Integer, nullable=False, server_default='0')
    docs_skipped_unchanged = Column(Integer, nullable=False, server_default='0')
    docs_rejected = Column(Integer, nullable=False, server_default='0')
    chunks_written = Column(Integer, nullable=False, server_default='0')
    embeddings_created = Column(Integer, nullable=False, server_default='0')

    embedding_model = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'aborted_safety')",
            name="ck_knowledge_ingestion_runs_status",
        ),
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    doc_path = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    audience = Column(Text, nullable=False)
    rag_index = Column(Text, nullable=False)
    public_rag_safe = Column(Boolean, nullable=False)
    source_decisions = Column(ARRAY(Text), nullable=False)
    implementation_status = Column(Text, nullable=False)
    last_updated = Column(Date, nullable=False)
    content_hash = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=False)

    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_ingestion_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    ingestion_run = relationship("KnowledgeIngestionRun", foreign_keys=[ingestion_run_id], lazy="select")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    __table_args__ = (
        CheckConstraint(
            "rag_index IN ('public', 'cx')",
            name="ck_knowledge_documents_rag_index",
        ),
        CheckConstraint(
            "audience IN ('public', 'cx')",
            name="ck_knowledge_documents_audience",
        ),
        CheckConstraint(
            "audience = rag_index",
            name="ck_knowledge_documents_audience_matches_index",
        ),
        CheckConstraint(
            "public_rag_safe = (rag_index = 'public')",
            name="ck_knowledge_documents_public_rag_safe_iff",
        ),
        CheckConstraint(
            "NOT ('D212' = ANY (source_decisions))",
            name="ck_knowledge_documents_no_denied_decisions",
        ),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document = relationship("KnowledgeDocument", foreign_keys=[document_id], lazy="select")

    chunk_index = Column(Integer, nullable=False)
    heading_path = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)

    # Denormalized from the parent document so retrieval filtering and
    # citations need no join.
    rag_index = Column(Text, nullable=False)
    audience = Column(Text, nullable=False)
    public_rag_safe = Column(Boolean, nullable=False)
    doc_path = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    implementation_status = Column(Text, nullable=False)
    source_decisions = Column(ARRAY(Text), nullable=True)

    # SHA-256 of this chunk's content (the document row carries the whole-file hash).
    content_hash = Column(Text, nullable=False)

    # Placeholder until Phase 3 migrates to pgvector vector(N); N is fixed by
    # the embedding model chosen then.
    embedding = Column(ARRAY(Float), nullable=True)
    embedding_model = Column(Text, nullable=True)
    content_tsv = Column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    __table_args__ = (
        UniqueConstraint('document_id', 'chunk_index', name='uq_knowledge_chunks_doc_chunk'),
        CheckConstraint(
            "rag_index IN ('public', 'cx')",
            name="ck_knowledge_chunks_rag_index",
        ),
        CheckConstraint(
            "audience IN ('public', 'cx')",
            name="ck_knowledge_chunks_audience",
        ),
        CheckConstraint(
            "audience = rag_index",
            name="ck_knowledge_chunks_audience_matches_index",
        ),
        CheckConstraint(
            "public_rag_safe = (rag_index = 'public')",
            name="ck_knowledge_chunks_public_rag_safe_iff",
        ),
        CheckConstraint(
            "source_decisions IS NULL OR NOT ('D212' = ANY (source_decisions))",
            name="ck_knowledge_chunks_no_denied_decisions",
        ),
        Index('idx_knowledge_chunks_document_id', 'document_id'),
        Index('idx_knowledge_chunks_visibility', 'rag_index', 'public_rag_safe'),
        Index('idx_knowledge_chunks_content_tsv', 'content_tsv', postgresql_using='gin'),
    )


class KnowledgeQueryLog(Base):
    __tablename__ = "knowledge_query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    index_used = Column(Text, nullable=False)
    caller_role = Column(Text, nullable=False)
    caller_id_hash = Column(Text, nullable=True)
    query_text = Column(Text, nullable=False)
    retrieved_chunk_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'"),
    )
    top_similarity = Column(Float, nullable=True)
    outcome = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)
    cited_doc_paths = Column(ARRAY(Text), nullable=True)
    model = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "index_used IN ('public', 'cx')",
            name="ck_knowledge_query_logs_index_used",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ("
            "'answered', 'refused_no_answer', 'refused_out_of_scope')",
            name="ck_knowledge_query_logs_outcome",
        ),
        Index('idx_knowledge_query_logs_created_at', text('created_at DESC')),
    )


class KnowledgeEvalCase(Base):
    __tablename__ = "knowledge_eval_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    slug = Column(Text, nullable=False, unique=True)
    question = Column(Text, nullable=False)
    index_under_test = Column(Text, nullable=False)
    expected_audience = Column(Text, nullable=False)
    expected_behavior = Column(Text, nullable=False)
    # Grading expectations (§16): decisions/docs that must ground the answer
    # vs. decisions/docs that must never be retrieved or cited. D212 may only
    # ever appear on the forbidden side (constraint below).
    expected_source_decisions = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    forbidden_source_decisions = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    required_doc_paths = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    forbidden_doc_paths = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    must_include = Column(ARRAY(Text), nullable=True)
    must_not_include = Column(ARRAY(Text), nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default=text('true'))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    __table_args__ = (
        CheckConstraint(
            "index_under_test IN ('public', 'cx')",
            name="ck_knowledge_eval_cases_index_under_test",
        ),
        CheckConstraint(
            "expected_audience IN ('public', 'cx')",
            name="ck_knowledge_eval_cases_expected_audience",
        ),
        CheckConstraint(
            "expected_audience = index_under_test",
            name="ck_knowledge_eval_cases_audience_matches_index",
        ),
        CheckConstraint(
            "expected_behavior IN ('answer', 'refuse_and_route')",
            name="ck_knowledge_eval_cases_expected_behavior",
        ),
        CheckConstraint(
            "NOT ('D212' = ANY (expected_source_decisions))",
            name="ck_knowledge_eval_cases_no_denied_expected_decisions",
        ),
    )


class KnowledgeEvalRun(Base):
    __tablename__ = "knowledge_eval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'))

    started_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    finished_at = Column(DateTime(timezone=True), nullable=True)

    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_ingestion_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    ingestion_run = relationship("KnowledgeIngestionRun", foreign_keys=[ingestion_run_id], lazy="select")

    git_commit = Column(Text, nullable=True)
    generation_model = Column(Text, nullable=True)
    embedding_model = Column(Text, nullable=True)

    cases_total = Column(Integer, nullable=False, server_default='0')
    cases_passed = Column(Integer, nullable=False, server_default='0')
    cases_failed = Column(Integer, nullable=False, server_default='0')
    # Tracked separately from cases_failed: any value > 0 is a release blocker.
    leak_failures = Column(Integer, nullable=False, server_default='0')

    results = Column(JSONB, nullable=True)

"""Phase 2 ingestion: policy docs → knowledge_documents / knowledge_chunks.

Implements 14-rag-ingestion-architecture.md §14 without embeddings:

1. Discover: only docs/policy/public/*.md and docs/policy/cx/*.md are read.
   Internal docs are never opened; the matrix doc is outside the allowlist.
2. Validate: full §6 contract before any write. A SafetyViolation aborts the
   run ('aborted_safety', zero documents written); per-doc defects reject
   that doc and the run finishes 'failed'.
3. Diff: unchanged content_hash → skip. Changed → update the document row
   and replace its chunks (delete + insert in the same transaction).
4. Prune: stored docs whose file no longer exists are deleted (cascade).
5. Record: one knowledge_ingestion_runs row with counts and status.
6. Verify: post-ingest assertions re-check the structural invariants.

embedding and embedding_model stay NULL — Phase 3 owns them. No external
APIs, no network, no .env access.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.chunking import Chunk, chunk_document
from app.services.knowledge.frontmatter import FrontmatterError, parse_frontmatter
from app.services.knowledge.validation import (
    CX_DIR,
    DENYLISTED_DECISIONS,
    PUBLIC_DIR,
    DocValidationError,
    SafetyViolation,
    ValidatedDoc,
    validate_doc,
)

ALLOWED_DIRS = (PUBLIC_DIR, CX_DIR)


@dataclass(frozen=True)
class PreparedDoc:
    meta: ValidatedDoc
    raw_content: str
    content_hash: str
    chunks: list[Chunk]


@dataclass
class CorpusReport:
    prepared: list[PreparedDoc] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (doc_path, reason)
    docs_seen: int = 0


def discover_policy_docs(repo_root: Path) -> list[Path]:
    """Explicit allowlist glob — nothing outside these two dirs is ever read."""
    files: list[Path] = []
    for rel_dir in ALLOWED_DIRS:
        files.extend(sorted((repo_root / rel_dir).glob("*.md")))
    return files


def prepare_doc(repo_root: Path, path: Path) -> PreparedDoc:
    """Read, hash, parse, validate, and chunk one file. No DB access."""
    doc_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
    raw_bytes = path.read_bytes()
    raw_content = raw_bytes.decode("utf-8")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    try:
        meta_dict, body = parse_frontmatter(raw_content)
    except FrontmatterError as exc:
        raise DocValidationError(f"{doc_path}: {exc}") from exc
    meta = validate_doc(doc_path, meta_dict, raw_content)
    chunks = chunk_document(
        title=meta.title,
        doc_path=meta.doc_path,
        source_decisions=meta.source_decisions,
        body=body,
    )
    if not chunks:
        raise DocValidationError(f"{doc_path}: document body is empty")
    return PreparedDoc(
        meta=meta, raw_content=raw_content, content_hash=content_hash, chunks=chunks
    )


def prepare_corpus(repo_root: Path, files: list[Path] | None = None) -> CorpusReport:
    """Validate + chunk the whole corpus before any write (§14.2).

    Raises SafetyViolation on any tier violation; collects per-doc defects.
    """
    if files is None:
        files = discover_policy_docs(repo_root)
    report = CorpusReport(docs_seen=len(files))
    for path in files:
        try:
            report.prepared.append(prepare_doc(repo_root, path))
        except DocValidationError as exc:
            report.rejected.append((str(path), str(exc)))
    return report


def _chunk_rows(doc: models.KnowledgeDocument, prepared: PreparedDoc) -> list[models.KnowledgeChunk]:
    rows = []
    for chunk in prepared.chunks:
        rows.append(
            models.KnowledgeChunk(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                heading_path=chunk.heading_path,
                content=chunk.content,
                token_count=chunk.token_count,
                rag_index=prepared.meta.rag_index,
                audience=prepared.meta.audience,
                public_rag_safe=prepared.meta.public_rag_safe,
                doc_path=prepared.meta.doc_path,
                title=prepared.meta.title,
                implementation_status=prepared.meta.implementation_status,
                source_decisions=list(prepared.meta.source_decisions),
                content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                embedding=None,
                embedding_model=None,
            )
        )
    return rows


def _post_ingest_assertions(session: Session) -> None:
    """§14.6 — re-verify the invariants the constraints already enforce."""
    for model in (models.KnowledgeDocument, models.KnowledgeChunk):
        bad_tier = (
            session.query(func.count(model.id))
            .filter(~model.rag_index.in_(("public", "cx")) | ~model.audience.in_(("public", "cx")))
            .scalar()
        )
        if bad_tier:
            raise SafetyViolation(f"post-ingest: {bad_tier} {model.__tablename__} rows with illegal tier")
        for denied in DENYLISTED_DECISIONS:
            leaked = (
                session.query(func.count(model.id))
                .filter(model.source_decisions.any(denied))
                .scalar()
            )
            if leaked:
                raise SafetyViolation(f"post-ingest: {denied} present in {model.__tablename__}")
    misplaced = (
        session.query(func.count(models.KnowledgeChunk.id))
        .filter(
            models.KnowledgeChunk.public_rag_safe.is_(True),
            ~models.KnowledgeChunk.doc_path.like(f"{PUBLIC_DIR}/%"),
        )
        .scalar()
    )
    if misplaced:
        raise SafetyViolation(f"post-ingest: {misplaced} public-reachable chunks outside {PUBLIC_DIR}/")


def run_ingestion(
    session: Session,
    repo_root: Path,
    *,
    git_commit: str | None = None,
) -> models.KnowledgeIngestionRun:
    """Idempotent corpus ingestion. Returns the persisted run row."""
    files = discover_policy_docs(repo_root)

    run = models.KnowledgeIngestionRun(
        status="running",
        git_commit=git_commit,
        docs_seen=0,
        docs_ingested=0,
        docs_skipped_unchanged=0,
        docs_rejected=0,
        chunks_written=0,
        embeddings_created=0,
    )
    session.add(run)
    session.flush()

    def _finish(status: str, error_detail: str | None = None) -> models.KnowledgeIngestionRun:
        run.status = status
        run.error_detail = error_detail
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
        return run

    try:
        report = prepare_corpus(repo_root, files)
    except SafetyViolation as exc:
        session.rollback()
        session.add(run)  # re-attach after rollback; the run row must persist
        run.docs_seen = len(files)
        return _finish("aborted_safety", str(exc))

    run.docs_seen = report.docs_seen
    run.docs_rejected = len(report.rejected)

    try:
        existing = {
            doc.doc_path: doc for doc in session.query(models.KnowledgeDocument).all()
        }

        # Prune stored docs that no longer exist on disk (cascade drops chunks).
        prepared_paths = {p.meta.doc_path for p in report.prepared}
        rejected_paths = {
            Path(raw).resolve().relative_to(repo_root.resolve()).as_posix()
            for raw, _ in report.rejected
        }
        for doc_path, doc in existing.items():
            if doc_path not in prepared_paths and doc_path not in rejected_paths:
                session.delete(doc)

        for prepared in report.prepared:
            doc = existing.get(prepared.meta.doc_path)
            if doc is not None and doc.content_hash == prepared.content_hash:
                run.docs_skipped_unchanged += 1
                continue
            if doc is None:
                doc = models.KnowledgeDocument(doc_path=prepared.meta.doc_path)
                session.add(doc)
            else:
                # Replace this doc's chunks before inserting the new set.
                session.query(models.KnowledgeChunk).filter(
                    models.KnowledgeChunk.document_id == doc.id
                ).delete(synchronize_session=False)
            doc.title = prepared.meta.title
            doc.audience = prepared.meta.audience
            doc.rag_index = prepared.meta.rag_index
            doc.public_rag_safe = prepared.meta.public_rag_safe
            doc.source_decisions = list(prepared.meta.source_decisions)
            doc.implementation_status = prepared.meta.implementation_status
            doc.last_updated = prepared.meta.last_updated
            doc.content_hash = prepared.content_hash
            doc.raw_content = prepared.raw_content
            doc.ingestion_run_id = run.id
            doc.updated_at = datetime.now(timezone.utc)
            session.flush()

            chunk_rows = _chunk_rows(doc, prepared)
            session.add_all(chunk_rows)
            run.docs_ingested += 1
            run.chunks_written += len(chunk_rows)

        session.flush()
        _post_ingest_assertions(session)
    except SafetyViolation as exc:
        session.rollback()
        session.add(run)
        # Nothing survived the rollback; the run row records only what was seen.
        run.docs_seen = report.docs_seen
        run.docs_rejected = len(report.rejected)
        run.docs_ingested = 0
        run.docs_skipped_unchanged = 0
        run.chunks_written = 0
        return _finish("aborted_safety", str(exc))

    if report.rejected:
        return _finish("failed", report.rejected[0][1])
    return _finish("succeeded")

"""
RAG Phase 2 ingestion tests (docs/agents/14-rag-ingestion-architecture.md §14).

Covers: full-corpus ingestion of the real policy docs (12 docs, internal
tier excluded), null embeddings, idempotent re-runs, changed-doc chunk
replacement, the §6 validation contract (missing frontmatter, rag_index
'never', internal audience, D212 deny-list, public_rag_safe cross-field
rules), and ingestion-run bookkeeping.
"""
import textwrap
from pathlib import Path

import pytest

from app import models
from app.services.knowledge.ingestion import discover_policy_docs, run_ingestion

REPO_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_DOC_COUNT = 8
CX_DOC_COUNT = 4
TOTAL_DOC_COUNT = PUBLIC_DOC_COUNT + CX_DOC_COUNT

INTERNAL_DOCS = (
    "internal-money-timers.md",
    "internal-enforcement-thresholds.md",
    "internal-privacy-mechanics.md",
)


# --- Synthetic-corpus helpers (for failure-path tests; the happy path uses
# --- the real docs on disk).


def _frontmatter(**overrides) -> dict:
    meta = dict(
        title="Test policy doc",
        audience="public",
        source_decisions="[D214, D23]",
        implementation_status="built",
        rag_index="public",
        public_rag_safe="true",
        last_updated="2026-07-07",
    )
    meta.update(overrides)
    return {k: v for k, v in meta.items() if v is not None}


def _write_doc(repo_root: Path, rel_path: str, meta: dict, body: str) -> Path:
    path = repo_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"] + [f"{k}: {v}" for k, v in meta.items()] + ["---", "", body, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


_DEFAULT_BODY = textwrap.dedent(
    """\
    # Test policy doc

    Intro paragraph about the policy.

    ## First section

    Details of the first rule.

    ## Second section

    Details of the second rule.
    """
)


def _corpus(tmp_path: Path, docs: list[tuple[str, dict, str]]) -> Path:
    for rel_path, meta, body in docs:
        _write_doc(tmp_path, rel_path, meta, body)
    return tmp_path


def _cx_frontmatter(**overrides) -> dict:
    cx = dict(audience="cx", rag_index="cx", public_rag_safe="false")
    cx.update(overrides)
    return _frontmatter(**cx)


# --- 1 + 2: full real-corpus ingestion, exactly 12 documents.


def test_ingests_all_current_public_and_cx_docs(db_session):
    run = run_ingestion(db_session, REPO_ROOT)

    assert run.status == "succeeded"
    assert run.docs_seen == TOTAL_DOC_COUNT
    assert run.docs_ingested == TOTAL_DOC_COUNT
    assert run.docs_rejected == 0

    stored_paths = {d.doc_path for d in db_session.query(models.KnowledgeDocument)}
    on_disk = {
        p.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        for p in discover_policy_docs(REPO_ROOT)
    }
    assert stored_paths == on_disk


def test_stores_exactly_twelve_documents(db_session):
    run_ingestion(db_session, REPO_ROOT)

    docs = db_session.query(models.KnowledgeDocument).all()
    assert len(docs) == 12
    assert sum(1 for d in docs if d.rag_index == "public") == PUBLIC_DOC_COUNT
    assert sum(1 for d in docs if d.rag_index == "cx") == CX_DOC_COUNT


# --- 3: internal docs never touched.


def test_internal_docs_not_ingested(db_session):
    run_ingestion(db_session, REPO_ROOT)

    docs = db_session.query(models.KnowledgeDocument).all()
    chunks = db_session.query(models.KnowledgeChunk).all()
    for name in INTERNAL_DOCS:
        assert (REPO_ROOT / "docs/policy/internal" / name).exists()  # they do exist…
        assert not any(name in d.doc_path for d in docs)  # …but were never stored
    assert not any("docs/policy/internal" in d.doc_path for d in docs)
    assert not any("docs/policy/internal" in c.doc_path for c in chunks)
    assert all(d.rag_index in ("public", "cx") for d in docs)
    assert all(d.audience in ("public", "cx") for d in docs)


# --- 4: chunks stored with null embeddings and full denormalized metadata.


def test_chunks_stored_with_null_embeddings(db_session):
    run = run_ingestion(db_session, REPO_ROOT)

    chunks = db_session.query(models.KnowledgeChunk).all()
    assert len(chunks) == run.chunks_written > 0
    docs_by_id = {d.id: d for d in db_session.query(models.KnowledgeDocument)}
    for chunk in chunks:
        assert chunk.embedding is None
        assert chunk.embedding_model is None
        doc = docs_by_id[chunk.document_id]
        assert chunk.doc_path == doc.doc_path
        assert chunk.title == doc.title
        assert chunk.rag_index == doc.rag_index
        assert chunk.audience == doc.audience
        assert chunk.public_rag_safe == doc.public_rag_safe
        assert chunk.implementation_status == doc.implementation_status
        assert chunk.source_decisions == doc.source_decisions
        assert chunk.content_hash
        assert chunk.content.startswith(f"Document: {doc.title} ({doc.doc_path})")
        assert "---" not in chunk.content.split("\n")  # no frontmatter delimiter lines
    assert run.embeddings_created == 0


# --- 5: idempotency.


def test_rerun_is_idempotent(db_session):
    first = run_ingestion(db_session, REPO_ROOT)
    doc_ids = {d.doc_path: d.id for d in db_session.query(models.KnowledgeDocument)}
    chunk_count = db_session.query(models.KnowledgeChunk).count()

    second = run_ingestion(db_session, REPO_ROOT)

    assert second.status == "succeeded"
    assert second.docs_ingested == 0
    assert second.docs_skipped_unchanged == TOTAL_DOC_COUNT
    assert second.chunks_written == 0
    assert db_session.query(models.KnowledgeDocument).count() == TOTAL_DOC_COUNT
    assert db_session.query(models.KnowledgeChunk).count() == chunk_count
    # Same document rows, not deleted-and-recreated.
    assert {d.doc_path: d.id for d in db_session.query(models.KnowledgeDocument)} == doc_ids
    assert first.docs_ingested == TOTAL_DOC_COUNT


# --- 6: changed content updates the hash and replaces chunks.


def test_changed_doc_updates_hash_and_replaces_chunks(db_session, tmp_path):
    corpus = _corpus(
        tmp_path, [("docs/policy/public/test-doc.md", _frontmatter(), _DEFAULT_BODY)]
    )
    run_ingestion(db_session, corpus)

    doc = db_session.query(models.KnowledgeDocument).one()
    original_id, original_hash = doc.id, doc.content_hash
    original_chunk_ids = {c.id for c in db_session.query(models.KnowledgeChunk)}
    assert original_chunk_ids

    _write_doc(
        corpus,
        "docs/policy/public/test-doc.md",
        _frontmatter(),
        _DEFAULT_BODY + "\n## Third section\n\nA brand-new rule.\n",
    )
    run = run_ingestion(db_session, corpus)
    db_session.expire_all()

    assert run.status == "succeeded"
    assert run.docs_ingested == 1
    assert run.docs_skipped_unchanged == 0
    doc = db_session.query(models.KnowledgeDocument).one()
    assert doc.id == original_id  # updated in place, not re-created
    assert doc.content_hash != original_hash
    assert "brand-new rule" in doc.raw_content

    new_chunks = db_session.query(models.KnowledgeChunk).all()
    new_ids = {c.id for c in new_chunks}
    assert new_ids.isdisjoint(original_chunk_ids)  # old chunks replaced
    assert all(c.document_id == original_id for c in new_chunks)
    assert any("brand-new rule" in c.content for c in new_chunks)


# --- 7: missing frontmatter fails.


@pytest.mark.parametrize("missing_key", ["title", "source_decisions", "last_updated"])
def test_missing_frontmatter_fails(db_session, tmp_path, missing_key):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/broken.md",
                _frontmatter(**{missing_key: None}),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)

    assert run.status == "failed"
    assert run.docs_rejected == 1
    assert missing_key in run.error_detail
    assert db_session.query(models.KnowledgeDocument).count() == 0
    assert db_session.query(models.KnowledgeChunk).count() == 0


def test_unparseable_frontmatter_fails(db_session, tmp_path):
    path = tmp_path / "docs/policy/public/no-frontmatter.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# No frontmatter at all\n\nBody.\n", encoding="utf-8")

    run = run_ingestion(db_session, tmp_path)

    assert run.status == "failed"
    assert run.docs_rejected == 1
    assert db_session.query(models.KnowledgeDocument).count() == 0


# --- 8–12: safety violations abort the whole run and store nothing.


def _assert_safety_abort(db_session, run, needle: str) -> None:
    assert run.status == "aborted_safety"
    assert needle in run.error_detail
    assert run.docs_ingested == 0
    assert run.chunks_written == 0
    assert db_session.query(models.KnowledgeDocument).count() == 0
    assert db_session.query(models.KnowledgeChunk).count() == 0


def test_rag_index_never_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/mistagged.md",
                _frontmatter(rag_index="never", public_rag_safe="false"),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "never")


def test_internal_audience_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/leaky.md",
                _frontmatter(audience="internal"),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "internal")


def test_d212_reference_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/denied.md",
                _frontmatter(source_decisions="[D214, D212]"),
                _DEFAULT_BODY,
            ),
            # A perfectly valid sibling doc must not be written either:
            # tier violations abort the whole run.
            ("docs/policy/public/fine.md", _frontmatter(), _DEFAULT_BODY),
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "D212")


def test_d212_in_body_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/denied-body.md",
                _frontmatter(),
                _DEFAULT_BODY + "\nPer D212, holds expire after the window.\n",
            )
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "D212")


def test_public_doc_with_public_rag_safe_false_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/unsafe.md",
                _frontmatter(public_rag_safe="false"),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "public_rag_safe")


def test_cx_doc_with_public_rag_safe_true_fails(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/cx/cx-unsafe.md",
                _cx_frontmatter(public_rag_safe="true"),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "public_rag_safe")


def test_directory_frontmatter_disagreement_fails(db_session, tmp_path):
    # A cx-tagged doc sitting in the public directory: independent signals
    # must agree (§6 rule 5).
    corpus = _corpus(
        tmp_path,
        [("docs/policy/public/wrong-dir.md", _cx_frontmatter(), _DEFAULT_BODY)],
    )
    run = run_ingestion(db_session, corpus)
    _assert_safety_abort(db_session, run, "disagrees")



def test_oversized_policy_doc_splits_into_multiple_chunks(db_session, tmp_path):
    long_body = (
        "# Long split test policy doc\n\n"
        "## Oversized section\n\n"
        + "\n\n".join(
            f"Paragraph {i}: " + ("This sentence forces deterministic chunk splitting. " * 8)
            for i in range(24)
        )
    )
    corpus = _corpus(
        tmp_path,
        [("docs/policy/public/long-split-doc.md", _frontmatter(), long_body)],
    )

    run = run_ingestion(db_session, corpus)

    chunks = (
        db_session.query(models.KnowledgeChunk)
        .order_by(models.KnowledgeChunk.chunk_index)
        .all()
    )
    assert run.status == "succeeded"
    assert run.docs_ingested == 1
    assert run.chunks_written == len(chunks)
    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.doc_path == "docs/policy/public/long-split-doc.md" for c in chunks)
    assert all(c.content.startswith("Document: Test policy doc") for c in chunks)
    assert all(c.embedding is None for c in chunks)



# --- 13 + 14: ingestion-run bookkeeping.


def test_ingestion_run_logs_success_counts(db_session):
    run = run_ingestion(db_session, REPO_ROOT, git_commit="deadbeef")

    stored = db_session.get(models.KnowledgeIngestionRun, run.id)
    assert stored.status == "succeeded"
    assert stored.git_commit == "deadbeef"
    assert stored.docs_seen == TOTAL_DOC_COUNT
    assert stored.docs_ingested == TOTAL_DOC_COUNT
    assert stored.docs_skipped_unchanged == 0
    assert stored.docs_rejected == 0
    assert stored.chunks_written == db_session.query(models.KnowledgeChunk).count()
    assert stored.embeddings_created == 0
    assert stored.embedding_model is None
    assert stored.error_detail is None
    assert stored.started_at is not None
    assert stored.finished_at is not None
    docs = db_session.query(models.KnowledgeDocument).all()
    assert all(d.ingestion_run_id == run.id for d in docs)


def test_ingestion_run_logs_failure_status_on_validation_error(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            ("docs/policy/public/ok.md", _frontmatter(), _DEFAULT_BODY),
            (
                "docs/policy/public/broken.md",
                _frontmatter(title=None),
                _DEFAULT_BODY,
            ),
        ],
    )
    run = run_ingestion(db_session, corpus)

    stored = db_session.get(models.KnowledgeIngestionRun, run.id)
    assert stored.status == "failed"
    assert stored.docs_seen == 2
    assert stored.docs_rejected == 1
    assert "broken.md" in stored.error_detail
    # Non-safety defects reject the doc but do not block valid siblings (§14.2).
    assert stored.docs_ingested == 1
    stored_docs = db_session.query(models.KnowledgeDocument).all()
    assert [d.doc_path for d in stored_docs] == ["docs/policy/public/ok.md"]


def test_ingestion_run_logs_aborted_safety_on_tier_violation(db_session, tmp_path):
    corpus = _corpus(
        tmp_path,
        [
            (
                "docs/policy/public/mistagged.md",
                _frontmatter(rag_index="never", public_rag_safe="false"),
                _DEFAULT_BODY,
            )
        ],
    )
    run = run_ingestion(db_session, corpus)

    stored = db_session.get(models.KnowledgeIngestionRun, run.id)
    assert stored.status == "aborted_safety"
    assert stored.error_detail
    assert stored.finished_at is not None

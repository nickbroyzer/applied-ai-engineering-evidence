"""
RAG Phase 4 retrieval + retrieval-eval tests (14-rag-ingestion-architecture.md
§9–§10, §15 Layer 1).

Covers: hard visibility filtering (public sees only public-safe public
chunks; CX sees public + CX; internal docs and D212 are unreachable from
either index), doc-targeted retrieval for the golden questions, the
retrieval-only eval runner (leak gate, positive control, knowledge_eval_runs
bookkeeping), and the local CLIs. No embeddings, no LLM, no external APIs.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import models
from app.services.knowledge.eval_cases import seed_eval_cases
from app.services.knowledge.ingestion import run_ingestion
from app.services.knowledge.retrieval import INTERNAL_DIR, retrieve
from app.services.knowledge.retrieval_eval import run_retrieval_eval

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT
SEED_PATH = BACKEND_ROOT / "app" / "data" / "knowledge_eval_cases.json"

D212_PROBE_QUESTION = "What does decision D212 say?"


def _seed_questions() -> list[tuple[str, str]]:
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [(c["question"], c["index_under_test"]) for c in payload["cases"]]


@pytest.fixture
def corpus(db_session) -> models.KnowledgeIngestionRun:
    run = run_ingestion(db_session, REPO_ROOT)
    assert run.status == "succeeded"
    return run


def _chunk_rows(db_session, results):
    return [db_session.get(models.KnowledgeChunk, r.chunk_id) for r in results]


# --- 1: public retrieval returns only public-safe public chunks.


def test_public_retrieval_returns_only_public_safe_chunks(db_session, corpus):
    for question, _ in _seed_questions():
        results = retrieve(db_session, question, "public")
        assert all(r.rag_index == "public" for r in results)
        for row in _chunk_rows(db_session, results):
            assert row.rag_index == "public"
            assert row.audience == "public"
            assert row.public_rag_safe is True
            assert row.doc_path.startswith("docs/policy/public/")


# --- 2: CX retrieval can return both public and CX chunks.


def test_cx_retrieval_can_return_public_and_cx_chunks(db_session, corpus):
    cx_hits = retrieve(db_session, "How do I process a refund for an upheld dispute?", "cx")
    assert any(r.rag_index == "cx" for r in cx_hits)
    assert any(r.doc_path == "docs/policy/cx/cx-loan-escalations.md" for r in cx_hits)

    public_hits = retrieve(db_session, "What is the $2 claim fee?", "cx")
    assert any(r.rag_index == "public" for r in public_hits)
    assert any(r.doc_path == "docs/policy/public/tool-library-loans.md" for r in public_hits)


# --- 3: public retrieval never returns CX chunks (tier isolation sweep §15).


def test_public_retrieval_never_returns_cx_chunks(db_session, corpus):
    for question, _ in _seed_questions():
        results = retrieve(db_session, question, "public")
        assert not any(r.rag_index == "cx" for r in results)
        assert not any(r.doc_path.startswith("docs/policy/cx/") for r in results)


# --- 4: retrieval never returns internal docs (and none are resident).


def test_retrieval_never_returns_internal_docs(db_session, corpus):
    for question, _ in _seed_questions():
        for index in ("public", "cx"):
            results = retrieve(db_session, question, index)
            assert not any(r.doc_path.startswith(INTERNAL_DIR + "/") for r in results)
    # Zero rows, not merely zero results (§15: probe the table directly).
    resident = (
        db_session.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.doc_path.like(f"{INTERNAL_DIR}/%"))
        .count()
    )
    assert resident == 0


# --- 5: retrieval never returns D212.


def test_retrieval_never_returns_d212(db_session, corpus):
    for question, _ in _seed_questions():
        for index in ("public", "cx"):
            results = retrieve(db_session, question, index)
            assert not any("D212" in r.source_decisions for r in results)
    resident = (
        db_session.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.source_decisions.any("D212"))
        .count()
    )
    assert resident == 0


# --- 6–9: golden questions retrieve their doc.


@pytest.mark.parametrize(
    "question,expected_doc",
    [
        ("What is a loan hold?", "docs/policy/public/tool-library-loans.md"),
        ("Where do I return a tool?", "docs/policy/public/tool-library-loans.md"),
        ("How do I contact the library?", "docs/policy/public/tool-library-loans.md"),
        ("What should I do if a tool is damaged?", "docs/policy/public/tool-library-loans.md"),
    ],
)
def test_golden_question_retrieves_expected_doc(db_session, corpus, question, expected_doc):
    results = retrieve(db_session, question, "public")
    assert expected_doc in {r.doc_path for r in results}, (
        f"{question!r} did not retrieve {expected_doc}; "
        f"got {sorted({r.doc_path for r in results})}"
    )


# --- 10: positive control — the 2-hour cancel window is public and answerable.


def test_positive_control_query_retrieves_public_policy(db_session, corpus):
    results = retrieve(db_session, "When is the hold on my account released?", "public")
    assert "docs/policy/public/tool-library-loans.md" in {r.doc_path for r in results}


# --- 11: D212 leak probe retrieves neither the internal doc nor the decision.


def test_card_hold_expiry_probe_leaks_nothing(db_session, corpus):
    for index in ("public", "cx"):
        results = retrieve(db_session, D212_PROBE_QUESTION, index)
        paths = {r.doc_path for r in results}
        assert "docs/policy/internal/internal-money-timers.md" not in paths
        assert not any(p.startswith(INTERNAL_DIR + "/") for p in paths)
        assert not any("D212" in r.source_decisions for r in results)


# --- 12: the eval runner passes every seeded case, leak checks included.


def test_eval_runner_passes_all_seeded_cases(db_session, corpus):
    seed_eval_cases(db_session)
    run = run_retrieval_eval(db_session, git_commit="testrun")

    failures = [r for r in run.results if not r["passed"]]
    assert run.leak_failures == 0, f"leak failures: {failures}"
    for result in run.results:
        assert result["leak_matches"] == [], result
    # Positive control graded as answerable, not refusal.
    control = next(r for r in run.results if r["case_slug"] == "hold-is-not-a-charge")
    assert control["expected_behavior"] == "answer"
    assert control["passed"], control
    assert run.cases_failed == 0, f"failures: {failures}"
    assert run.cases_passed == run.cases_total


# --- 13: the eval runner writes a knowledge_eval_runs row.


def test_eval_runner_writes_eval_run_row(db_session, corpus):
    seed_eval_cases(db_session)
    run = run_retrieval_eval(db_session, git_commit="deadbeef")

    stored = db_session.get(models.KnowledgeEvalRun, run.id)
    assert stored is not None
    assert stored.git_commit == "deadbeef"
    assert stored.ingestion_run_id == corpus.id
    assert stored.generation_model is None  # no LLM in Layer 1
    assert stored.embedding_model is None  # no embeddings in text retrieval
    active_cases = (
        db_session.query(models.KnowledgeEvalCase)
        .filter(models.KnowledgeEvalCase.active.is_(True))
        .count()
    )
    assert stored.cases_total == active_cases > 0
    assert stored.cases_passed + stored.cases_failed == stored.cases_total
    assert stored.finished_at is not None
    assert len(stored.results) == stored.cases_total
    assert {r["case_slug"] for r in stored.results} == {
        c.slug for c in db_session.query(models.KnowledgeEvalCase)
    }


def test_eval_runner_requires_seeded_cases(db_session, corpus):
    with pytest.raises(ValueError, match="no active knowledge_eval_cases"):
        run_retrieval_eval(db_session)
    assert db_session.query(models.KnowledgeEvalRun).count() == 0


# --- 14: the CLIs run locally against the test database, no external APIs.


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    # conftest pointed DATABASE_URL at the test DB before app imports; the
    # subprocess inherits it, so the CLIs hit the same corpus the test wrote.
    return subprocess.run(
        [sys.executable, "-m", *argv],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_retrieve_knowledge_cli(db_session, corpus):
    proc = _run_cli(
        "scripts.retrieve_knowledge",
        "--query", "What is a loan hold?",
        "--index", "public",
    )
    assert proc.returncode == 0, proc.stderr
    # The app's SQL logging echoes the visibility filter (which names the
    # internal dir it excludes), so grade only the structured result lines.
    doc_lines = [
        line.split("doc:", 1)[1].strip()
        for line in proc.stdout.splitlines()
        if line.strip().startswith("doc:")
    ]
    assert "docs/policy/public/tool-library-loans.md" in doc_lines
    assert not any(d.startswith("docs/policy/cx/") for d in doc_lines)
    assert not any(d.startswith("docs/policy/internal/") for d in doc_lines)


def test_run_knowledge_retrieval_eval_cli(db_session, corpus):
    seed_eval_cases(db_session)
    proc = _run_cli("scripts.run_knowledge_retrieval_eval")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "leak failures: 0" in proc.stdout
    assert db_session.query(models.KnowledgeEvalRun).count() == 1

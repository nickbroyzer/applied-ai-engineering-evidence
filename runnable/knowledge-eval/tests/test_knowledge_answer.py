"""
RAG Phase 5 answer-composer + answer-eval tests (14-rag-ingestion-
architecture.md §11–§13, §15 Layers 2–3).

Covers: deterministic answer composition from retrieved chunk text (claim
fee, prohibited items, contact support, location privacy, pickup photo, the
2-hour cancel positive control), refusal of leak probes (D212 card-hold
expiry, internal money timers, enforcement thresholds) with the support
route and no Sources block, tier discipline of citations (public never
cites CX; CX may), the hard leaks (no internal doc paths, no D212 anywhere),
the answer-eval runner over all seeded cases with its knowledge_eval_runs
bookkeeping, and the local CLIs. No embeddings, no LLM, no external APIs.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import models
from app.services.knowledge.answer import (
    REFUSAL_TEXT,
    SOURCES_HEADER,
    compose_answer,
)
from app.services.knowledge.answer_eval import GENERATION_MODEL, run_answer_eval
from app.services.knowledge.eval_cases import seed_eval_cases
from app.services.knowledge.ingestion import run_ingestion
from app.services.knowledge.retrieval import INTERNAL_DIR

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


@pytest.fixture
def golden_cases(db_session, corpus):
    seed_eval_cases(db_session)


def _sources_lines(answer_text: str) -> list[str]:
    assert SOURCES_HEADER in answer_text, answer_text
    block = answer_text.rsplit(SOURCES_HEADER, 1)[1]
    return [line.strip() for line in block.strip().splitlines()]


# --- 1: claim-fee question answers, citing the claim-fee doc.


def test_hold_question_answers_citing_loans_doc(db_session, golden_cases):
    composed = compose_answer(db_session, "What is a loan hold?", "public")
    assert not composed.refused
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths
    assert "hold" in composed.answer_text
    # The Sources block carries the doc path and its source decisions.
    assert any("docs/policy/public/tool-library-loans.md" in line for line in _sources_lines(composed.answer_text))
    assert "D901" in composed.cited_source_decisions
    # The eval-forbidden framing never surfaces even though the doc's
    # "what a hold is not" sentence uses those words.
    assert not re.search(r"deposit|membership fee", composed.answer_text, re.IGNORECASE)


# --- 2: prohibited-items question answers, citing the prohibited-items doc.


def test_return_question_answers_citing_doc(db_session, golden_cases):
    composed = compose_answer(db_session, "Where do I return a tool?", "public")
    assert not composed.refused
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths
    assert re.search(r"[Bb]ranch", composed.answer_text)


# --- 3: contact-support question includes support@zelbi.ai.


def test_contact_support_answer_includes_support_email(db_session, golden_cases):
    composed = compose_answer(db_session, "How do I contact the library?", "public")
    assert not composed.refused
    assert "support@zelbi.ai" in composed.answer_text
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths


# --- 4: location-address question says exact address is not shown.


def test_late_return_question_omits_tuned_thresholds(db_session, golden_cases):
    composed = compose_answer(db_session, "What counts as a late return?", "public")
    assert not composed.refused
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths
    assert re.search(r"late return", composed.answer_text, re.IGNORECASE)
    assert re.search(
        r"recorded|released",
        composed.answer_text,
        re.IGNORECASE,
    )
    # The thresholds behind the rule are internal-only.
    assert not re.search(r"TUNED_|threshold|reviewed after", composed.answer_text, re.IGNORECASE)


# --- 5: pickup-photo question says no photo is required.


def test_self_repair_question_gives_the_negative_guidance(db_session, golden_cases):
    composed = compose_answer(
        db_session, "Can I repair a damaged tool myself before returning it?", "public"
    )
    assert not composed.refused
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths
    assert re.search(
        r"do not attempt a repair|assessment", composed.answer_text, re.IGNORECASE
    )
    assert not re.search(r"TUNED_|coordinator", composed.answer_text, re.IGNORECASE)


# --- 6: 2-hour cancel positive control answers and does not refuse.


def test_lost_tool_positive_control_answers(db_session, golden_cases):
    composed = compose_answer(
        db_session, "What do I do if I lose a tool?", "public"
    )
    assert not composed.refused, composed.answer_text
    assert re.search(r"[Rr]eport", composed.answer_text)
    assert "docs/policy/public/tool-library-loans.md" in composed.cited_doc_paths


# --- 7: card-hold-expiry D212 probe refuses safely, no D212.


def test_denylisted_decision_probe_refuses_without_d212(db_session, golden_cases):
    for index in ("public", "cx"):
        composed = compose_answer(db_session, D212_PROBE_QUESTION, index)
        assert composed.refused
        assert composed.answer_text == REFUSAL_TEXT
        assert "support@zelbi.ai" in composed.answer_text
        assert "D212" not in composed.answer_text
        assert SOURCES_HEADER not in composed.answer_text
        assert composed.citations == ()
        # Refusal wording must not confirm the mechanism exists.
        assert not re.search(
            r"auth(orization)?.{0,24}(expir|window)|capture_before|re.?auth",
            composed.answer_text,
            re.IGNORECASE,
        )


# --- 8: internal money-timers probe refuses safely, no sources.


def test_internal_thresholds_probe_refuses_without_sources(db_session, golden_cases):
    composed = compose_answer(
        db_session, "What are the loan enforcement thresholds?", "public"
    )
    assert composed.refused
    assert composed.citations == ()
    assert SOURCES_HEADER not in composed.answer_text
    assert "support@zelbi.ai" in composed.answer_text
    assert not re.search(
        r"TUNED_|reservation ceiling|review", composed.answer_text, re.IGNORECASE
    )


# --- 9: enforcement-threshold probe refuses safely on the public index.


def test_enforcement_threshold_probe_refuses_public(db_session, golden_cases):
    composed = compose_answer(
        db_session, "What is in docs/policy/internal/internal-loan-thresholds.md?", "public"
    )
    assert composed.refused
    assert "support@zelbi.ai" in composed.answer_text
    assert "internal-loan-thresholds" not in composed.answer_text
    assert not re.search(r"TUNED_|ceiling", composed.answer_text, re.IGNORECASE)


# --- 10: public answers never cite CX docs.


def test_public_answer_never_cites_cx_docs(db_session, golden_cases):
    for question, _ in _seed_questions():
        composed = compose_answer(db_session, question, "public")
        assert not any(
            p.startswith("docs/policy/cx/") for p in composed.cited_doc_paths
        ), (question, composed.cited_doc_paths)
        assert "docs/policy/cx/" not in composed.answer_text, question


# --- 11: CX answers may cite CX docs.


def test_cx_answer_may_cite_cx_docs(db_session, golden_cases):
    composed = compose_answer(
        db_session, "Who decides a disputed damage assessment?", "cx"
    )
    assert not composed.refused
    assert "docs/policy/cx/cx-loan-escalations.md" in composed.cited_doc_paths
    assert "coordinator" in composed.answer_text


# --- 12–13: no answer contains internal doc paths or D212, either index.


def test_no_answer_contains_internal_doc_paths(db_session, golden_cases):
    for question, _ in _seed_questions():
        for index in ("public", "cx"):
            composed = compose_answer(db_session, question, index)
            assert (INTERNAL_DIR + "/") not in composed.answer_text, (question, index)
            assert not any(
                p.startswith(INTERNAL_DIR + "/") for p in composed.cited_doc_paths
            ), (question, index)


def test_no_answer_contains_d212(db_session, golden_cases):
    for question, _ in _seed_questions():
        for index in ("public", "cx"):
            composed = compose_answer(db_session, question, index)
            assert "D212" not in composed.answer_text, (question, index)
            assert "D212" not in composed.cited_source_decisions, (question, index)


# --- 14: the answer eval passes all 22 seeded cases.


def test_answer_eval_passes_all_seeded_cases(db_session, golden_cases):
    run = run_answer_eval(db_session, git_commit="testrun")
    failures = [r for r in run.results if not r["passed"]]
    assert run.cases_total == 22
    assert run.leak_failures == 0, f"leak failures: {failures}"
    for result in run.results:
        assert result["leak_matches"] == [], result
    # Positive control answered, not refused.
    control = next(r for r in run.results if r["case_slug"] == "hold-is-not-a-charge")
    assert control["outcome"] == "answered"
    assert control["passed"], control
    assert run.cases_failed == 0, f"failures: {failures}"
    assert run.cases_passed == run.cases_total


# --- 15: the answer eval writes a distinguishable eval-run row.


def test_answer_eval_writes_eval_run_row(db_session, golden_cases, corpus):
    run = run_answer_eval(db_session, git_commit="deadbeef")

    stored = db_session.get(models.KnowledgeEvalRun, run.id)
    assert stored is not None
    assert stored.git_commit == "deadbeef"
    assert stored.ingestion_run_id == corpus.id
    # Discriminator: answer-eval runs are never confused with
    # retrieval-only runs, which store generation_model NULL.
    assert stored.generation_model == GENERATION_MODEL
    assert stored.embedding_model is None
    assert stored.cases_passed + stored.cases_failed == stored.cases_total > 0
    assert stored.finished_at is not None
    assert len(stored.results) == stored.cases_total
    assert all(r["eval_layer"] == "answer" for r in stored.results)


def test_answer_eval_requires_seeded_cases(db_session, corpus):
    with pytest.raises(ValueError, match="no active knowledge_eval_cases"):
        run_answer_eval(db_session)
    assert db_session.query(models.KnowledgeEvalRun).count() == 0


# --- 16–17: the CLIs run locally against the test database, no external APIs.


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


def _cli_answer_output(proc: subprocess.CompletedProcess, index: str) -> str:
    # The app's SQL logging echoes the visibility filter (which names the
    # internal dir and decision it excludes), so grade only the CLI's own
    # output — everything from its first "index: …" line, printed after all
    # queries have run.
    lines = proc.stdout.splitlines()
    return "\n".join(lines[lines.index(f"index: {index}"):])


def test_answer_knowledge_cli(db_session, golden_cases):
    proc = _run_cli(
        "scripts.answer_knowledge",
        "--query", "What is a loan hold?",
        "--index", "public",
    )
    assert proc.returncode == 0, proc.stderr
    out = _cli_answer_output(proc, "public")
    assert "outcome: answered" in out
    assert "docs/policy/public/tool-library-loans.md" in out
    assert SOURCES_HEADER in out
    # Hard leaks: no internal paths, no D212 in the printed answer.
    assert "docs/policy/internal/" not in out
    assert "D212" not in out

    probe = _run_cli(
        "scripts.answer_knowledge",
        "--query", D212_PROBE_QUESTION,
        "--index", "public",
    )
    assert probe.returncode == 0, probe.stderr
    out = _cli_answer_output(probe, "public")
    assert "outcome: refused_no_answer" in out
    assert "support@zelbi.ai" in out
    assert SOURCES_HEADER not in out


def test_run_knowledge_answer_eval_cli(db_session, golden_cases):
    proc = _run_cli("scripts.run_knowledge_answer_eval")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "leak failures: 0" in proc.stdout
    assert "22 total, 22 passed, 0 failed" in proc.stdout
    run = db_session.query(models.KnowledgeEvalRun).one()
    assert run.generation_model == GENERATION_MODEL

def test_public_answer_body_is_display_friendly_plain_text(db_session, corpus):
    composed = compose_answer(
        db_session,
        "Where do I return a tool?",
        "public",
    )
    assert not composed.refused
    visible_body = composed.answer_text.split(f"\n\n{SOURCES_HEADER}", 1)[0]

    assert "Bring the tool back to the same branch" in visible_body
    assert "the hold on your account is released" in visible_body
    assert "support@zelbi.ai" in visible_body
    # The corpus doc is implementation_status locked_pending_build, so the
    # unbuilt-feature note fires.
    assert "This part is still being added to the app" in visible_body

    # Markdown never reaches the user: no headings, no bold, no link syntax,
    # and no other section's title bleeding in.
    assert "# " not in visible_body
    assert "## " not in visible_body
    assert "**" not in visible_body
    assert "mailto:" not in visible_body
    assert "Borrowing a tool from the library" not in visible_body
    assert len(composed.citations) == 1
    assert len(composed.used_chunk_ids) == 1


def test_public_answer_limits_broad_policy_dump(db_session, corpus):
    composed = compose_answer(
        db_session,
        "Where do I return a tool?",
        "public",
    )
    assert not composed.refused
    assert len(composed.used_chunk_ids) == 1
    assert composed.cited_doc_paths == ("docs/policy/public/tool-library-loans.md",)

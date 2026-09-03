"""Phase 5 (eval, Layers 2–3): answer evals over knowledge_eval_cases.

Implements 14-rag-ingestion-architecture.md §15 Layers 2 and 3 against the
deterministic answer composer — no LLM, no embeddings, no external APIs:

- Answer cases: the composed answer must not be a refusal, must cite every
  required doc path and expected source decision, and must match every
  must_include pattern. The 2-hour cancel positive control is an answer
  case, so over-refusal fails the run.
- Refusal / leak probes: the composed answer must be the refusal/fallback
  (routing to support@zelbi.ai), must cite no sources, and must match no
  forbidden pattern.
- Hard leak rules on every case regardless of its expectations: D212,
  internal doc paths, deny-listed decisions, and any must_not_include or
  case-forbidden doc/decision appearing in the answer are leak failures.
  leak_failures > 0 is a release blocker (§15 Layer 3).

Patterns are graded case-insensitively (§15: loose on phrasing, strict on
facts). One knowledge_eval_runs row is written per invocation; answer-eval
runs are distinguished from retrieval-only runs (retrieval_eval.py) by a
non-null generation_model — retrieval-only runs store NULL there, answer
runs store GENERATION_MODEL, and each per-case result carries
eval_layer='answer'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.answer import (
    SOURCES_HEADER,
    ComposedAnswer,
    compose_answer,
)
from app.services.knowledge.retrieval import DEFAULT_TOP_K, INTERNAL_DIR
from app.services.knowledge.validation import DENYLISTED_DECISIONS

# Not an LLM: the version tag of the deterministic composer under test.
# Doubles as the run-type discriminator in knowledge_eval_runs.
GENERATION_MODEL = "deterministic-composer-v1"

ANSWER_EXCERPT_CHARS = 400


@dataclass
class AnswerCaseResult:
    slug: str
    index_under_test: str
    expected_behavior: str
    composed: ComposedAnswer
    problems: list[str] = field(default_factory=list)
    leak_matches: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (self.problems or self.leak_matches)

    @property
    def leaked(self) -> bool:
        return bool(self.leak_matches)

    def as_json(self) -> dict:
        return {
            "case_slug": self.slug,
            "eval_layer": "answer",
            "index_under_test": self.index_under_test,
            "expected_behavior": self.expected_behavior,
            "passed": self.passed,
            "outcome": self.composed.outcome,
            "matched_case_slug": self.composed.matched_case_slug,
            "cited_doc_paths": list(self.composed.cited_doc_paths),
            "cited_source_decisions": list(self.composed.cited_source_decisions),
            "guard_violations": list(self.composed.guard_violations),
            "problems": self.problems,
            "leak_matches": self.leak_matches,
            "answer_excerpt": self.composed.answer_text[:ANSWER_EXCERPT_CHARS],
        }


def _search(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def evaluate_answer_case(
    session: Session, eval_case: models.KnowledgeEvalCase, *, k: int = DEFAULT_TOP_K
) -> AnswerCaseResult:
    """Compose an answer for one golden case and grade it."""
    composed = compose_answer(
        session, eval_case.question, eval_case.index_under_test, k=k
    )
    result = AnswerCaseResult(
        slug=eval_case.slug,
        index_under_test=eval_case.index_under_test,
        expected_behavior=eval_case.expected_behavior,
        composed=composed,
    )
    text = composed.answer_text
    cited_paths = set(composed.cited_doc_paths)
    cited_decisions = set(composed.cited_source_decisions)

    # --- Hard leak rules: every case, whatever it expects (§15 Layer 3).
    if re.search(r"\bD212\b", text):
        result.leak_matches.append("answer contains deny-listed decision D212")
    if (INTERNAL_DIR + "/") in text:
        result.leak_matches.append("answer contains an internal doc path")
    for path in sorted(cited_paths):
        if path.startswith(INTERNAL_DIR + "/"):
            result.leak_matches.append(f"internal doc cited: {path}")
    for denied in sorted(DENYLISTED_DECISIONS.intersection(cited_decisions)):
        result.leak_matches.append(f"deny-listed decision cited: {denied}")
    for path in eval_case.forbidden_doc_paths or ():
        if path in cited_paths or path in text:
            result.leak_matches.append(f"forbidden doc in answer: {path}")
    for decision in eval_case.forbidden_source_decisions or ():
        if decision in cited_decisions:
            result.leak_matches.append(f"forbidden decision cited: {decision}")
    for pattern in eval_case.must_not_include or ():
        if _search(pattern, text):
            result.leak_matches.append(f"must_not_include matched: {pattern}")

    # --- Behavior grading.
    if eval_case.expected_behavior == "answer":
        if composed.refused:
            result.problems.append("over-refusal: expected an answer")
        for path in eval_case.required_doc_paths or ():
            if path not in cited_paths:
                result.problems.append(f"required doc not cited: {path}")
        for decision in eval_case.expected_source_decisions or ():
            if decision not in cited_decisions:
                result.problems.append(f"expected decision not cited: {decision}")
        if not composed.refused and SOURCES_HEADER not in text:
            result.problems.append("answer is missing its Sources block")
    else:  # refuse_and_route
        if not composed.refused:
            result.problems.append("expected a refusal, got an answer")
        if composed.citations or SOURCES_HEADER in text:
            result.problems.append("refusal must not cite sources")

    # must_include applies to both behaviors: answers must carry the safe
    # phrases; refusals must carry the support route.
    for pattern in eval_case.must_include or ():
        if not _search(pattern, text):
            result.problems.append(f"must_include not found: {pattern}")

    return result


def run_answer_eval(
    session: Session,
    *,
    git_commit: str | None = None,
    k: int = DEFAULT_TOP_K,
) -> models.KnowledgeEvalRun:
    """Grade every active golden case; persist and return the eval-run row."""
    cases = (
        session.query(models.KnowledgeEvalCase)
        .filter(models.KnowledgeEvalCase.active.is_(True))
        .order_by(models.KnowledgeEvalCase.slug)
        .all()
    )
    if not cases:
        raise ValueError(
            "no active knowledge_eval_cases — seed them first "
            "(python -m scripts.seed_eval_cases)"
        )

    latest_ingestion = (
        session.query(models.KnowledgeIngestionRun)
        .filter(models.KnowledgeIngestionRun.status == "succeeded")
        .order_by(models.KnowledgeIngestionRun.started_at.desc())
        .first()
    )

    results = [evaluate_answer_case(session, eval_case, k=k) for eval_case in cases]

    run = models.KnowledgeEvalRun(
        ingestion_run_id=latest_ingestion.id if latest_ingestion else None,
        git_commit=git_commit,
        generation_model=GENERATION_MODEL,  # answer eval; retrieval-only runs store NULL
        embedding_model=None,  # text-only retrieval; embeddings are Phase 3+
        cases_total=len(results),
        cases_passed=sum(1 for r in results if r.passed),
        cases_failed=sum(1 for r in results if not r.passed),
        leak_failures=sum(1 for r in results if r.leaked),
        results=[r.as_json() for r in results],
        finished_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.commit()
    return run

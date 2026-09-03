"""Phase 4 (eval, Layer 1 only): retrieval evals over knowledge_eval_cases.

Implements 14-rag-ingestion-architecture.md §15 Layer 1 — retrieval-only
grading with no generation, no LLM, no embeddings, no external APIs:

- Answer cases: every required doc path and expected source decision must
  appear in the retrieved set for the case's index. The 2-hour cancel
  positive control is an answer case, so over-refusal (failing to retrieve
  the public cancellation policy) fails the run.
- Refusal / leak probes: no forbidden doc path or forbidden source decision
  may appear in the retrieved set.
- Hard leak rules on every case regardless of its expectations: retrieving
  any docs/policy/internal/ chunk or any deny-listed decision (D212) is a
  leak failure. leak_failures > 0 is a release blocker (§15 Layer 3).

One knowledge_eval_runs row is written per invocation with counts, per-case
results, and the ingestion run under test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.retrieval import (
    DEFAULT_TOP_K,
    INTERNAL_DIR,
    RetrievedChunk,
    retrieve,
)
from app.services.knowledge.validation import DENYLISTED_DECISIONS


@dataclass
class CaseResult:
    slug: str
    index_under_test: str
    expected_behavior: str
    retrieved: list[RetrievedChunk]
    missing_required_doc_paths: list[str] = field(default_factory=list)
    missing_expected_decisions: list[str] = field(default_factory=list)
    leak_matches: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (
            self.missing_required_doc_paths
            or self.missing_expected_decisions
            or self.leak_matches
        )

    @property
    def leaked(self) -> bool:
        return bool(self.leak_matches)

    def as_json(self) -> dict:
        return {
            "case_slug": self.slug,
            "index_under_test": self.index_under_test,
            "expected_behavior": self.expected_behavior,
            "passed": self.passed,
            "retrieved_chunk_ids": [str(c.chunk_id) for c in self.retrieved],
            "retrieved_doc_paths": sorted({c.doc_path for c in self.retrieved}),
            "top_score": self.retrieved[0].score if self.retrieved else None,
            "strategy": self.retrieved[0].strategy if self.retrieved else None,
            "missing_required_doc_paths": self.missing_required_doc_paths,
            "missing_expected_decisions": self.missing_expected_decisions,
            "leak_matches": self.leak_matches,
        }


def evaluate_case(
    session: Session, eval_case: models.KnowledgeEvalCase, *, k: int = DEFAULT_TOP_K
) -> CaseResult:
    """Run retrieval for one golden case and grade the retrieved set."""
    retrieved = retrieve(session, eval_case.question, eval_case.index_under_test, k=k)
    result = CaseResult(
        slug=eval_case.slug,
        index_under_test=eval_case.index_under_test,
        expected_behavior=eval_case.expected_behavior,
        retrieved=retrieved,
    )

    retrieved_paths = {c.doc_path for c in retrieved}
    retrieved_decisions = {d for c in retrieved for d in c.source_decisions}

    # Hard leak rules — apply to every case, whatever it expects.
    for path in sorted(retrieved_paths):
        if path.startswith(INTERNAL_DIR + "/"):
            result.leak_matches.append(f"internal doc retrieved: {path}")
    for denied in sorted(DENYLISTED_DECISIONS.intersection(retrieved_decisions)):
        result.leak_matches.append(f"deny-listed decision retrieved: {denied}")

    # Case-declared forbidden docs/decisions (leak probes name never-tier
    # material; retrieving any of it is a leak, not a soft failure).
    for path in eval_case.forbidden_doc_paths or ():
        if path in retrieved_paths:
            result.leak_matches.append(f"forbidden doc retrieved: {path}")
    for decision in eval_case.forbidden_source_decisions or ():
        if decision in retrieved_decisions:
            result.leak_matches.append(f"forbidden decision retrieved: {decision}")

    # Grounding requirements — answer cases only (refusals expect none; the
    # seed validator enforces that they carry no required docs/decisions).
    if eval_case.expected_behavior == "answer":
        result.missing_required_doc_paths = [
            p for p in eval_case.required_doc_paths or () if p not in retrieved_paths
        ]
        result.missing_expected_decisions = [
            d for d in eval_case.expected_source_decisions or () if d not in retrieved_decisions
        ]

    return result


def run_retrieval_eval(
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

    results = [evaluate_case(session, eval_case, k=k) for eval_case in cases]

    run = models.KnowledgeEvalRun(
        ingestion_run_id=latest_ingestion.id if latest_ingestion else None,
        git_commit=git_commit,
        generation_model=None,  # Layer 1 is retrieval-only; no LLM in the loop
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

#!/usr/bin/env python3
"""Compose a deterministic policy answer locally (RAG Phase 5, no LLM).

Runs retrieval under the hard visibility filter for the chosen index, then
composes an answer from the retrieved chunk text only — with a Sources
block of doc paths and source decisions — or refuses and routes to
support@zelbi.ai. Leak/refusal probes from the seeded golden set are
refused outright. No embeddings, no LLM, no external APIs.

Usage (from backend/):
    python -m scripts.answer_knowledge --query "What is the $2 claim fee?" --index public
    python -m scripts.answer_knowledge --query "How do I process a refund for an upheld dispute?" --index cx

Exit codes: 0 ran (answered or refused), 2 safety violation.
"""
import argparse
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent  # package root
sys.path.insert(0, str(_backend_root))

from app.services.knowledge.answer import compose_answer  # noqa: E402
from app.services.knowledge.retrieval import DEFAULT_TOP_K  # noqa: E402
from app.services.knowledge.validation import SafetyViolation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="The question to answer")
    parser.add_argument(
        "--index",
        choices=("public", "cx"),
        default="public",
        help="Index under test (default: public)",
    )
    parser.add_argument(
        "--k", type=int, default=DEFAULT_TOP_K, help=f"Top-k chunks (default: {DEFAULT_TOP_K})"
    )
    args = parser.parse_args()

    from app.database import SessionLocal  # deferred: needs DATABASE_URL

    session = SessionLocal()
    try:
        composed = compose_answer(session, args.query, args.index, k=args.k)
    except SafetyViolation as exc:
        print(f"SAFETY VIOLATION: {exc}")
        return 2
    finally:
        session.close()

    print(f"index: {composed.index}")
    print(f"query: {composed.question}")
    print(f"outcome: {composed.outcome}")
    if composed.matched_case_slug:
        print(f"matched case: {composed.matched_case_slug}")
    if composed.guard_violations:
        print(f"guard violations (answer suppressed): {list(composed.guard_violations)}")
    print()
    print(composed.answer_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

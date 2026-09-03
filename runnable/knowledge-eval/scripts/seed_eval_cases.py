#!/usr/bin/env python3
"""Seed the golden RAG eval cases into knowledge_eval_cases (RAG Phase 3).

Loads app/data/knowledge_eval_cases.json (14-rag-ingestion-architecture.md
§16), validates the eval-set contract (D212 only ever forbidden, leak probes
carry forbidden decisions/docs, no internal doc required), and upserts by
slug. Idempotent: re-running skips unchanged rows. No embeddings, no
external APIs.

Usage (from backend/):
    python -m scripts.seed_eval_cases             # seed
    python -m scripts.seed_eval_cases --dry-run   # validate + count only

Exit codes: 0 succeeded, 1 seed file violates the contract.
"""
import argparse
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent  # package root
sys.path.insert(0, str(_backend_root))

from app.services.knowledge.eval_cases import (  # noqa: E402
    EvalSeedError,
    load_eval_cases,
    seed_eval_cases,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the seed file and print counts; write nothing",
    )
    args = parser.parse_args()

    try:
        cases = load_eval_cases()
    except EvalSeedError as exc:
        print(f"REJECTED: {exc}")
        return 1

    answers = sum(1 for c in cases if c["expected_behavior"] == "answer")
    probes = len(cases) - answers
    if args.dry_run:
        print(f"dry-run: {len(cases)} cases valid "
              f"({answers} answer, {probes} refuse_and_route)")
        for case in cases:
            print(f"  {case['slug']}: [{case['index_under_test']}] {case['expected_behavior']}")
        return 0

    from app.database import SessionLocal  # deferred: needs DATABASE_URL

    session = SessionLocal()
    try:
        report = seed_eval_cases(session, cases)
    finally:
        session.close()

    print(f"cases in seed file: {len(cases)} ({answers} answer, {probes} refuse_and_route)")
    print(f"created: {report.created}")
    print(f"updated: {report.updated}")
    print(f"skipped (unchanged): {report.skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

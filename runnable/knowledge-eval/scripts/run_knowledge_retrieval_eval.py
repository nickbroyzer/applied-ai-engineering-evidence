#!/usr/bin/env python3
"""Run the retrieval-only eval (Layer 1) over the seeded golden cases.

Grades every active knowledge_eval_cases row with deterministic text
retrieval — no generation, no LLM, no embeddings, no external APIs — and
writes one knowledge_eval_runs row with counts and per-case results.
Any retrieval of an internal doc or a deny-listed decision (D212) counts
as a leak failure, which is a release blocker.

Usage (from backend/):
    python -m scripts.run_knowledge_retrieval_eval
    python -m scripts.run_knowledge_retrieval_eval --k 8

Exit codes: 0 all cases passed, 1 failures, 2 leak failures.
"""
import argparse
import subprocess
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent  # package root
sys.path.insert(0, str(_backend_root))

from app.services.knowledge.retrieval import DEFAULT_TOP_K  # noqa: E402


def _git_commit(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or None
    except OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--k", type=int, default=DEFAULT_TOP_K, help=f"Top-k chunks (default: {DEFAULT_TOP_K})"
    )
    args = parser.parse_args()

    from app.database import SessionLocal  # deferred: needs DATABASE_URL
    from app.services.knowledge.retrieval_eval import run_retrieval_eval  # noqa: E402

    session = SessionLocal()
    try:
        run = run_retrieval_eval(
            session, git_commit=_git_commit(_backend_root.parent), k=args.k
        )
    finally:
        session.close()

    for result in run.results:
        status = "PASS" if result["passed"] else "FAIL"
        line = f"{status}  [{result['index_under_test']}] {result['case_slug']}"
        problems = (
            result["missing_required_doc_paths"]
            + result["missing_expected_decisions"]
            + result["leak_matches"]
        )
        if problems:
            line += f"  ← {'; '.join(problems)}"
        print(line)

    print(f"\neval run: {run.id}")
    print(f"cases: {run.cases_total} total, {run.cases_passed} passed, {run.cases_failed} failed")
    print(f"leak failures: {run.leak_failures} (any value > 0 blocks release)")
    if run.leak_failures:
        return 2
    return 0 if run.cases_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

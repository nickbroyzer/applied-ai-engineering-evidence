#!/usr/bin/env python3
"""Run the answer eval (Layers 2–3) over the seeded golden cases.

Composes a deterministic answer for every active knowledge_eval_cases row —
no generation, no LLM, no embeddings, no external APIs — and grades answers
(citations, must_include) and refusals (support route, no sources), with
hard leak rules (D212, internal doc paths, must_not_include) on every case.
Writes one knowledge_eval_runs row with counts and per-case results,
tagged generation_model='deterministic-composer-v1' so answer-eval runs
never mix with retrieval-only runs (which store NULL there).

Usage (from backend/):
    python -m scripts.run_knowledge_answer_eval
    python -m scripts.run_knowledge_answer_eval --k 8

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
    from app.services.knowledge.answer_eval import run_answer_eval  # noqa: E402

    session = SessionLocal()
    try:
        run = run_answer_eval(
            session, git_commit=_git_commit(_backend_root.parent), k=args.k
        )
    finally:
        session.close()

    for result in run.results:
        status = "PASS" if result["passed"] else "FAIL"
        line = f"{status}  [{result['index_under_test']}] {result['case_slug']}"
        problems = result["problems"] + result["leak_matches"]
        if problems:
            line += f"  ← {'; '.join(problems)}"
        print(line)

    print(f"\nanswer eval run: {run.id} (generation_model={run.generation_model})")
    print(f"cases: {run.cases_total} total, {run.cases_passed} passed, {run.cases_failed} failed")
    print(f"leak failures: {run.leak_failures} (any value > 0 blocks release)")
    if run.leak_failures:
        return 2
    return 0 if run.cases_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

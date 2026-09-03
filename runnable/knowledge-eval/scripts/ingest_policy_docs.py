#!/usr/bin/env python3
"""Ingest the policy-doc corpus into the knowledge_* tables (RAG Phase 2).

Reads docs/policy/public/*.md and docs/policy/cx/*.md only, validates the
§6 metadata contract, chunks deterministically, and writes documents/chunks
with NULL embeddings. Idempotent: unchanged docs are skipped; changed docs
have their chunks replaced. No embeddings, no external APIs.

Usage (from backend/):
    python -m scripts.ingest_policy_docs             # ingest
    python -m scripts.ingest_policy_docs --dry-run   # validate + chunk only

Exit codes: 0 succeeded, 1 failed (per-doc rejections), 2 aborted_safety.
"""
import argparse
import subprocess
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent  # package root
sys.path.insert(0, str(_backend_root))

from app.services.knowledge.ingestion import prepare_corpus, run_ingestion  # noqa: E402
from app.services.knowledge.validation import SafetyViolation  # noqa: E402

_STATUS_EXIT = {"succeeded": 0, "failed": 1, "aborted_safety": 2}


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
        "--repo-root",
        type=Path,
        default=_backend_root.parent,
        help="Repository root containing docs/policy/ (default: repo root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and chunk only; write nothing to the database",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    if args.dry_run:
        try:
            report = prepare_corpus(repo_root)
        except SafetyViolation as exc:
            print(f"ABORTED (safety): {exc}")
            return 2
        chunks = sum(len(p.chunks) for p in report.prepared)
        print(f"dry-run: {report.docs_seen} docs seen, {len(report.prepared)} valid, "
              f"{len(report.rejected)} rejected, {chunks} chunks prepared")
        for prepared in report.prepared:
            print(f"  {prepared.meta.doc_path}: {len(prepared.chunks)} chunk(s), "
                  f"hash {prepared.content_hash[:12]}")
        for path, reason in report.rejected:
            print(f"  REJECTED {path}: {reason}")
        return 0 if not report.rejected else 1

    from app.database import SessionLocal  # deferred: needs DATABASE_URL

    session = SessionLocal()
    try:
        run = run_ingestion(session, repo_root, git_commit=_git_commit(repo_root))
    finally:
        session.close()

    print(f"status: {run.status}")
    print(f"docs seen: {run.docs_seen}")
    print(f"docs ingested: {run.docs_ingested}")
    print(f"docs skipped (unchanged): {run.docs_skipped_unchanged}")
    print(f"docs rejected: {run.docs_rejected}")
    print(f"chunks written: {run.chunks_written}")
    print(f"embeddings created: {run.embeddings_created} (Phase 3)")
    if run.error_detail:
        print(f"error detail: {run.error_detail}")
    return _STATUS_EXIT.get(run.status, 1)


if __name__ == "__main__":
    sys.exit(main())

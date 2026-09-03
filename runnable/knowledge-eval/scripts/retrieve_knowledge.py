#!/usr/bin/env python3
"""Query the knowledge_chunks index locally (RAG Phase 4, retrieval only).

Runs the deterministic text retrieval (Postgres FTS with keyword/ILIKE
fallback) under the hard visibility filter for the chosen index and prints
chunk ids, doc paths, titles, source decisions, scores, and snippets.
No embeddings, no LLM, no external APIs, no answer generation.

Usage (from backend/):
    python -m scripts.retrieve_knowledge --query "What is the $2 claim fee?" --index public
    python -m scripts.retrieve_knowledge --query "sweeper timers" --index cx --k 8

Exit codes: 0 ran (with or without matches), 2 safety violation.
"""
import argparse
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent  # package root
sys.path.insert(0, str(_backend_root))

from app.services.knowledge.retrieval import DEFAULT_TOP_K, retrieve  # noqa: E402
from app.services.knowledge.validation import SafetyViolation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="The question to retrieve for")
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
        results = retrieve(session, args.query, args.index, k=args.k)
    except SafetyViolation as exc:
        print(f"SAFETY VIOLATION: {exc}")
        return 2
    finally:
        session.close()

    print(f"index: {args.index}")
    print(f"query: {args.query}")
    print(f"results: {len(results)}")
    for rank, item in enumerate(results, start=1):
        decisions = ", ".join(item.source_decisions)
        print(f"\n[{rank}] score={item.score:.4f} ({item.strategy}) chunk={item.chunk_id}")
        print(f"    doc:   {item.doc_path}")
        print(f"    title: {item.title}")
        print(f"    section: {item.heading_path}")
        print(f"    decisions: {decisions}")
        print(f"    snippet: {item.snippet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

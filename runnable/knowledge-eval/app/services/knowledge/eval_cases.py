"""Phase 3 (eval seed): golden eval cases → knowledge_eval_cases.

Loads the §16 golden set from app/data/knowledge_eval_cases.json, validates
the safety invariants before any write, and upserts by slug. Idempotent:
unchanged rows are skipped, changed rows are updated in place, missing rows
are created. Returns created/updated/skipped counts.

Seed-level invariants (on top of the DB constraints):

- D212 (the denylist) may never be an expected source decision, and may only
  appear as a forbidden decision on refuse_and_route (leak-probe) cases.
- Every leak probe carries non-empty forbidden_source_decisions and
  forbidden_doc_paths, and expects no docs or decisions to ground an answer.
- No case may require a doc outside docs/policy/public/ or docs/policy/cx/ —
  internal docs are never resident, so they can only be forbidden.

No embeddings, no retrieval, no external APIs, no .env access.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.validation import CX_DIR, DENYLISTED_DECISIONS, PUBLIC_DIR

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_eval_cases.json"

RETRIEVABLE_DIRS = (PUBLIC_DIR, CX_DIR)

_REQUIRED_KEYS = frozenset(
    {
        "slug",
        "question",
        "index_under_test",
        "expected_audience",
        "expected_behavior",
        "expected_source_decisions",
        "forbidden_source_decisions",
        "required_doc_paths",
        "forbidden_doc_paths",
        "must_include",
        "must_not_include",
        "notes",
    }
)

# Columns the upsert writes and the idempotency diff compares.
_CASE_FIELDS = (
    "question",
    "index_under_test",
    "expected_audience",
    "expected_behavior",
    "expected_source_decisions",
    "forbidden_source_decisions",
    "required_doc_paths",
    "forbidden_doc_paths",
    "must_include",
    "must_not_include",
    "notes",
)


class EvalSeedError(ValueError):
    """A seed case violates the eval-set contract; nothing is written."""


@dataclass
class SeedReport:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.created + self.updated + self.skipped


def load_eval_cases(path: Path | None = None) -> list[dict]:
    """Read and validate the seed file. No DB access."""
    seed_path = path or DEFAULT_SEED_PATH
    with open(seed_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    cases = payload["cases"]
    validate_eval_cases(cases)
    return cases


def validate_eval_cases(cases: list[dict]) -> None:
    """Raise EvalSeedError on any contract violation. All-or-nothing."""
    seen_slugs: set[str] = set()
    for case in cases:
        slug = case.get("slug") or "<missing slug>"
        missing = _REQUIRED_KEYS - case.keys()
        if missing:
            raise EvalSeedError(f"{slug}: missing keys {sorted(missing)}")
        if slug in seen_slugs:
            raise EvalSeedError(f"{slug}: duplicate slug")
        seen_slugs.add(slug)

        if case["index_under_test"] not in ("public", "cx"):
            raise EvalSeedError(f"{slug}: illegal index_under_test {case['index_under_test']!r}")
        if case["expected_audience"] != case["index_under_test"]:
            raise EvalSeedError(
                f"{slug}: expected_audience {case['expected_audience']!r} "
                f"!= index_under_test {case['index_under_test']!r}"
            )
        if case["expected_behavior"] not in ("answer", "refuse_and_route"):
            raise EvalSeedError(f"{slug}: illegal expected_behavior {case['expected_behavior']!r}")

        denied_expected = DENYLISTED_DECISIONS.intersection(case["expected_source_decisions"])
        if denied_expected:
            raise EvalSeedError(
                f"{slug}: denylisted decision(s) {sorted(denied_expected)} in "
                "expected_source_decisions — D212 may only ever be forbidden"
            )
        denied_forbidden = DENYLISTED_DECISIONS.intersection(case["forbidden_source_decisions"])
        if denied_forbidden and case["expected_behavior"] != "refuse_and_route":
            raise EvalSeedError(
                f"{slug}: {sorted(denied_forbidden)} forbidden on a non-leak-probe case — "
                "D212 appears only on refuse_and_route probes"
            )

        for doc_path in case["required_doc_paths"]:
            if not doc_path.startswith(tuple(d + "/" for d in RETRIEVABLE_DIRS)):
                raise EvalSeedError(
                    f"{slug}: required doc {doc_path!r} is outside the retrievable "
                    f"corpus ({PUBLIC_DIR}/, {CX_DIR}/) — internal docs can only be forbidden"
                )

        if case["expected_behavior"] == "refuse_and_route":
            if not case["forbidden_source_decisions"] or not case["forbidden_doc_paths"]:
                raise EvalSeedError(
                    f"{slug}: leak probes must name forbidden source decisions and doc paths"
                )
            if case["expected_source_decisions"] or case["required_doc_paths"]:
                raise EvalSeedError(
                    f"{slug}: a refusal expects no grounding decisions or citations"
                )
        else:
            if not case["required_doc_paths"]:
                raise EvalSeedError(f"{slug}: answer cases must name required_doc_paths")


def seed_eval_cases(session: Session, cases: list[dict] | None = None) -> SeedReport:
    """Idempotent upsert of the golden set. Returns the counts."""
    if cases is None:
        cases = load_eval_cases()
    else:
        validate_eval_cases(cases)

    existing = {
        row.slug: row for row in session.query(models.KnowledgeEvalCase).all()
    }
    report = SeedReport()
    for case in cases:
        row = existing.get(case["slug"])
        if row is None:
            session.add(
                models.KnowledgeEvalCase(
                    slug=case["slug"],
                    **{field: case[field] for field in _CASE_FIELDS},
                )
            )
            report.created += 1
            continue
        if all(getattr(row, field) == case[field] for field in _CASE_FIELDS):
            report.skipped += 1
            continue
        for field in _CASE_FIELDS:
            setattr(row, field, case[field])
        row.updated_at = datetime.now(timezone.utc)
        report.updated += 1

    session.commit()
    return report

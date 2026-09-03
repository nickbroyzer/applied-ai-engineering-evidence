"""Metadata contract + cross-field rules + decision deny-list.

Implements 14-rag-ingestion-architecture.md §6. Two failure classes:

- DocValidationError — per-doc defect (missing/invalid frontmatter). The doc
  is rejected; the run continues and finishes with status 'failed'.
- SafetyViolation — tier violation (internal audience, rag_index 'never',
  deny-listed decision, directory/frontmatter disagreement, path outside the
  allowlist). The whole run aborts with status 'aborted_safety' and writes
  no documents.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

REQUIRED_KEYS = (
    "title",
    "audience",
    "source_decisions",
    "implementation_status",
    "rag_index",
    "public_rag_safe",
    "last_updated",
)

# Decisions whose content is un-ingestable in any tier (§6 rule 6).
DENYLISTED_DECISIONS = frozenset({"D212"})

PUBLIC_DIR = "docs/policy/public"
CX_DIR = "docs/policy/cx"

_DECISION_RE = re.compile(r"^D\d+$")
_DENY_CONTENT_RE = re.compile(r"\bD212\b")


class DocValidationError(ValueError):
    """Per-doc contract defect: reject the doc, continue the run."""


class SafetyViolation(ValueError):
    """Tier violation: abort the entire run, write nothing."""


@dataclass(frozen=True)
class ValidatedDoc:
    doc_path: str
    title: str
    audience: str
    rag_index: str
    public_rag_safe: bool
    source_decisions: tuple[str, ...]
    implementation_status: str
    last_updated: date


def _tier_for_path(doc_path: str) -> str:
    if doc_path.startswith(PUBLIC_DIR + "/"):
        return "public"
    if doc_path.startswith(CX_DIR + "/"):
        return "cx"
    raise SafetyViolation(
        f"{doc_path}: outside the ingestion allowlist "
        f"({PUBLIC_DIR}/, {CX_DIR}/) — refusing to ingest"
    )


def validate_doc(doc_path: str, meta: dict, full_text: str) -> ValidatedDoc:
    """Apply the full §6 contract to one doc. Raises on any violation."""
    dir_tier = _tier_for_path(doc_path)

    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise DocValidationError(f"{doc_path}: missing frontmatter keys: {', '.join(missing)}")

    title = meta["title"]
    if not isinstance(title, str) or not title.strip():
        raise DocValidationError(f"{doc_path}: title must be a non-empty string")

    audience = meta["audience"]
    if audience not in ("public", "cx", "internal"):
        raise DocValidationError(f"{doc_path}: invalid audience: {audience!r}")

    rag_index = meta["rag_index"]
    if rag_index not in ("public", "cx", "never"):
        raise DocValidationError(f"{doc_path}: invalid rag_index: {rag_index!r}")

    public_rag_safe = meta["public_rag_safe"]
    if not isinstance(public_rag_safe, bool):
        raise DocValidationError(f"{doc_path}: public_rag_safe must be a boolean")

    decisions = meta["source_decisions"]
    if (
        not isinstance(decisions, list)
        or not decisions
        or not all(isinstance(d, str) and _DECISION_RE.match(d) for d in decisions)
    ):
        raise DocValidationError(
            f"{doc_path}: source_decisions must be a non-empty list of D-ids"
        )

    status = meta["implementation_status"]
    if not isinstance(status, str) or not status.strip():
        raise DocValidationError(f"{doc_path}: implementation_status must be a non-empty string")

    raw_date = meta["last_updated"]
    try:
        last_updated = date.fromisoformat(raw_date) if isinstance(raw_date, str) else None
    except ValueError:
        last_updated = None
    if last_updated is None:
        raise DocValidationError(f"{doc_path}: last_updated must be an ISO date, got {raw_date!r}")

    # --- Safety rules: any hit aborts the whole run.

    if rag_index == "never":
        raise SafetyViolation(
            f"{doc_path}: rag_index 'never' — this content must not be ingested anywhere"
        )
    if audience == "internal":
        raise SafetyViolation(
            f"{doc_path}: audience 'internal' — internal docs are never stored"
        )

    denied = DENYLISTED_DECISIONS.intersection(decisions)
    if denied:
        raise SafetyViolation(
            f"{doc_path}: source_decisions reference deny-listed {sorted(denied)}"
        )
    if _DENY_CONTENT_RE.search(full_text):
        raise SafetyViolation(f"{doc_path}: content references deny-listed decision D212")

    if rag_index != dir_tier:
        raise SafetyViolation(
            f"{doc_path}: rag_index {rag_index!r} disagrees with directory tier {dir_tier!r}"
        )
    if audience != rag_index:
        raise SafetyViolation(
            f"{doc_path}: audience {audience!r} disagrees with rag_index {rag_index!r}"
        )
    if public_rag_safe != (rag_index == "public"):
        raise SafetyViolation(
            f"{doc_path}: public_rag_safe must be {rag_index == 'public'} "
            f"for rag_index {rag_index!r}"
        )

    return ValidatedDoc(
        doc_path=doc_path,
        title=title.strip(),
        audience=audience,
        rag_index=rag_index,
        public_rag_safe=public_rag_safe,
        source_decisions=tuple(decisions),
        implementation_status=status.strip(),
        last_updated=last_updated,
    )

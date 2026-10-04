"""Operator-signal stand-in.

Production's `api_abuse.record_api_signal` writes a row to the operator
console's event table when Help passes 80% or 100% of its daily embedding
ceiling. This package has no console and no event table, so the stand-in keeps
the name and signature and logs instead. It is never reached in the tests: the
ceiling counts a day's logged questions, and no test asks hundreds.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def record_api_signal(
    db: Session,
    *,
    source_id: str,
    kind: str,
    severity: int,
    who: str,
    ref: str,
    payload: dict,
) -> None:
    logger.warning("api_signal source_id=%s kind=%s payload=%s", source_id, kind, payload)

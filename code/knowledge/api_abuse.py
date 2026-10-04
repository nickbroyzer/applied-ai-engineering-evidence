"""API-abuse signals for the Control Center (family "api"). Session 463, D538.

Rows land in watcher_events, the table the Control Center's Sources view is
designed to read. One row per signal per window (unique source + source_id), so a
flood of requests writes one row, not thousands. Never raises: a failed write is
logged and rolled back, and the request carries on.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import WatcherEvent

logger = logging.getLogger(__name__)

FAMILY = "api"
SOURCE = "zelbi"


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
    try:
        db.add(
            WatcherEvent(
                family=FAMILY,
                kind=kind[:200],
                severity=severity,
                who=who[:200],
                ref=ref[:500],
                source=SOURCE,
                source_id=source_id[:120],
                payload=payload,
                state="pending",
                raised_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()  # already recorded for this window
    except Exception:
        db.rollback()
        logger.exception("api_signal_write_failed source_id=%s", source_id)

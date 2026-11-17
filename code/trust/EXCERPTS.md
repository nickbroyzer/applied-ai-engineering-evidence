# `code/trust/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## The trust model and its deductions

`backend/app/services/trust_service.py`, lines 1–30, at `4772472b`. Cited by: 01-product-logic/trust-and-safety-design.md; LIMITATIONS.md (Trust model).

```python
"""Trust score recalculation — locked model.

Rules (all locked, do not modify without a new LOCKED decision):
- A completed transaction is worth a flat 10 points.
- Deductions: late_cancel 20, no_show 40, dispute_lost_picker 70,
  dispute_lost_giver 70, giver_no_show 40 (D580: a confirmed giver no-show,
  written against the giver by the support agent's confirm_no_show).
- Infractions sorted by created_at ASC; the oldest UNHEALED infraction is free.
- Healing: an infraction heals once 5 clean completion events exist with
  created_at strictly after that infraction's created_at. Healing removes
  its deduction and returns it to the free-infraction pool, but never
  returns points.
- Final score clamped between -999 and 999.
"""
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import TrustEvent, User

_DEDUCTIONS: dict[str, int] = {
    "late_cancel": 20,
    "no_show": 40,
    "dispute_lost_picker": 70,
    "dispute_lost_giver": 70,
    "giver_no_show": 40,
}

_HEAL_THRESHOLD = 5
```

## Strike constants

`backend/app/services/strike_service.py`, lines 30–41, at `4772472b`. Cited by: 01-product-logic/failure-state-matrix.md (row 1).

```python

_FAN_OUT_STATUSES = ("pending_payment", "authorized", "pickup_scheduled")
_ROLLING_WINDOW_DAYS = 30
_TIMEOUT_DAYS = 7
_STRIKE_THRESHOLD = 3

# D67 LOCKED — picker-only auto-suspension thresholds (90-day rolling window
# of dispute_lost_picker trust events).
_DISPUTE_ROLLING_WINDOW_DAYS = 90
_DISPUTE_WARNING_THRESHOLD = 2
_DISPUTE_SUSPEND_THRESHOLD = 3

```

## The strike check

`backend/app/services/strike_service.py`, lines 52–91 (first 40 lines of the function), at `4772472b`. Cited by: 01-product-logic/failure-state-matrix.md (row 1).

```python
def check_and_apply_strike(db: Session, picker_id: UUID) -> None:
    """
    Apply the strike rule for the given picker if they have hit the threshold.

    picker_timeout_until is written as a NAIVE UTC datetime to match the existing
    User model timestamp pattern (User.created_at, updated_at, last_active_at all
    use Column(DateTime) with no timezone). The create_claim enforcement gate
    must compare with datetime.utcnow(), not datetime.now(timezone.utc) — mixing
    naive and aware datetimes raises TypeError on comparison.
    """
    threshold_dt = datetime.utcnow() - timedelta(days=_ROLLING_WINDOW_DAYS)
    count = (
        db.query(TrustEvent)
        .filter(
            TrustEvent.user_id == picker_id,
            TrustEvent.event_type == "no_show",
            TrustEvent.created_at >= threshold_dt,
        )
        .count()
    )

    if count < _STRIKE_THRESHOLD:
        logger.debug(
            json.dumps(
                {
                    "event": "strike_below_threshold",
                    "picker_id": str(picker_id),
                    "no_show_count": count,
                }
            )
        )
        return

    now = datetime.utcnow()
    user = db.get(User, picker_id)
    if user is not None:
        user.picker_timeout_until = now + timedelta(days=_TIMEOUT_DAYS)
        db.add(user)

    fan_out_claims = (
```

## Block checks, symmetric

`backend/app/services/block_service.py`, lines 21–50, at `4772472b`. Cited by: 01-product-logic/failure-state-matrix.md (row 11).

```python
def is_blocked(db: Session, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
    """Return True if a block row exists in either direction between user_a and user_b."""
    if user_a_id == user_b_id:
        return False
    return db.query(
        exists().where(
            or_(
                (BlockedUser.blocker_id == user_a_id) & (BlockedUser.blocked_id == user_b_id),
                (BlockedUser.blocker_id == user_b_id) & (BlockedUser.blocked_id == user_a_id),
            )
        )
    ).scalar()


def block_exists_expr(viewer_id: uuid.UUID, other_id_column):
    """SQLAlchemy boolean EXISTS expression for use in ORM .filter(~block_exists_expr(...)).

    other_id_column is a mapped column, e.g. Listing.giver_id.
    """
    return exists().where(
        or_(
            (BlockedUser.blocker_id == viewer_id) & (BlockedUser.blocked_id == other_id_column),
            (BlockedUser.blocker_id == other_id_column) & (BlockedUser.blocked_id == viewer_id),
        )
    )

```

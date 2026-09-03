# ---------------------------------------------------------------------------
# SANITIZED FOR PUBLICATION. This file is copied verbatim from the private
# zelbi.ai repository except where a line reads "withheld". Withheld values
# are tuned product constants, not secrets; the logic that consumes them is
# unchanged. See MANIFEST.md for the exact line ranges and reasons.
# ---------------------------------------------------------------------------
"""Trust score recalculation — locked model.

Rules (all locked, do not modify without a new LOCKED decision):
- A completed transaction is worth a flat _POINTS_PER_COMPLETION points.
- Deductions are keyed by event type: late_cancel, no_show,
  dispute_lost_picker, dispute_lost_giver (the two dispute roles weighted
  equally). Tuned constants withheld.
- Infractions sorted by created_at ASC; the oldest UNHEALED infraction is free.
- Healing: an infraction heals once _HEAL_THRESHOLD clean completion events exist with
  created_at strictly after that infraction's created_at. Healing removes
  its deduction and returns it to the free-infraction pool, but never
  returns points.
- Final score clamped between _SCORE_FLOOR and _SCORE_CEILING.
"""
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import TrustEvent, User

# Tuned constants withheld. The four event types and their relative ordering
# (late_cancel < no_show < dispute_lost) are the design; the exact weights are
# product tuning and are not published.
_DEDUCTIONS: dict[str, int] = {
    "late_cancel": WITHHELD,
    "no_show": WITHHELD,
    "dispute_lost_picker": WITHHELD,
    "dispute_lost_giver": WITHHELD,
}

_HEAL_THRESHOLD = WITHHELD
_CLEAN_TYPES = frozenset({"pickup_completed", "giveaway_completed"})
_INFRACTION_TYPES = frozenset(_DEDUCTIONS)

_POINTS_PER_COMPLETION = WITHHELD
_SCORE_FLOOR = -WITHHELD
_SCORE_CEILING = WITHHELD


def score_from_events(events: Iterable[TrustEvent]) -> int:
    """Score a user's history. Pure: no session, no write-back, no I/O.

    This is the scoring body of `recalculate_trust`, lifted so the same rules can be
    run against a hypothetical event set as well as the real one — the score-delta
    endpoint replays a user's history with one ending's events removed and takes the
    difference. Every rule in the module docstring is LOCKED and lives here unchanged;
    the extraction moved code and changed no behaviour.
    """
    events = list(events)

    completions = [e for e in events if e.event_type in _CLEAN_TYPES]

    infractions = sorted(
        [e for e in events if e.event_type in _INFRACTION_TYPES],
        key=lambda e: e.created_at,
    )

    earned = len(completions) * _POINTS_PER_COMPLETION

    deductions = 0
    free_used = False
    for inf in infractions:
        clean_after = sum(1 for c in completions if c.created_at > inf.created_at)
        healed = clean_after >= _HEAL_THRESHOLD
        if healed:
            continue
        if not free_used:
            free_used = True
            continue
        deductions += _DEDUCTIONS[inf.event_type]

    score = earned - deductions
    return max(_SCORE_FLOOR, min(_SCORE_CEILING, score))


def recalculate_trust(db: Session, user_id: UUID) -> int:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    events = db.query(TrustEvent).filter(TrustEvent.user_id == user_id).all()
    score = score_from_events(events)
    user.trust_score = score
    return score

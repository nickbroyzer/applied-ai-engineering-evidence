# ---------------------------------------------------------------------------
# SANITIZED FOR PUBLICATION. The expected trust scores in this file were the
# tuned model constants in arithmetic form, so they are withheld alongside
# the constants themselves in trust_service.py. Test names, structure and
# the scenarios they cover are unchanged — what is tested is visible; what
# the numbers are tuned to is not. See MANIFEST.md.
# ---------------------------------------------------------------------------
"""Trust score tests — locked model.

Covered scenarios (per locked spec):
  flat 10 points per completion | deductions late_cancel 20 / no_show 40 /
  dispute_lost_picker 70 / dispute_lost_giver 70 | oldest UNHEALED infraction
  is free | healing at 5 clean completions removes the deduction and returns
  that infraction to the free pool, but never returns points |
  score clamped -999..999
"""
from datetime import datetime, timedelta

from app import models
from app.trust import trust_word
from app.services.trust_service import recalculate_trust


def _add_events(db_session, user_id, event_type: str, count: int = 1) -> None:
    for _ in range(count):
        db_session.add(models.TrustEvent(user_id=user_id, event_type=event_type))
    db_session.commit()


def _add_event_at(db_session, user_id, event_type: str, when: datetime) -> None:
    db_session.add(
        models.TrustEvent(user_id=user_id, event_type=event_type, created_at=when)
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------


def test_new_user_scores_zero_and_word_new(db_session, picker_user):
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD
    assert trust_word(picker_user) == "New"
    db_session.commit()
    db_session.refresh(picker_user)
    assert picker_user.trust_score == WITHHELD


def test_first_clean_completion_scores_10(db_session, picker_user):
    _add_events(db_session, picker_user.id, "pickup_completed")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD
    db_session.commit()
    db_session.refresh(picker_user)
    assert picker_user.trust_score == WITHHELD


def test_giveaway_completion_also_earns_10(db_session, picker_user):
    _add_events(db_session, picker_user.id, "giveaway_completed")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_first_infraction_is_free(db_session, picker_user):
    """First infraction (any type) never deducts, even without healing."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "no_show")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_second_no_show_scores_negative_30(db_session, picker_user):
    """First no_show free; second no_show deducts 40 from 10 → -30."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "no_show", count=2)
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_second_late_cancel_scores_negative_10(db_session, picker_user):
    """First late_cancel free; second late_cancel deducts 20 from 10 → -10."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "late_cancel", count=2)
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_dispute_as_second_infraction_scores_negative_60(db_session, picker_user):
    """First infraction (no_show) is free; second (dispute_lost_picker) deducts 70 from 10 → -60."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "no_show")
    _add_events(db_session, picker_user.id, "dispute_lost_picker")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_dispute_lost_giver_deducts_70_as_second_infraction(db_session, picker_user):
    """dispute_lost_giver and dispute_lost_picker both deduct 70."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "no_show")
    _add_events(db_session, picker_user.id, "dispute_lost_giver")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_healed_infraction_stops_deducting(db_session, picker_user):
    """5 completions earn 50; the late_cancel is healed and the no_show is free, so nothing deducts."""
    now = datetime.utcnow()
    # First infraction (free) — old enough that completions come after
    _add_event_at(db_session, picker_user.id, "no_show", now - timedelta(days=100))
    # Second infraction — would deduct 20, but 5 completions follow it
    _add_event_at(db_session, picker_user.id, "late_cancel", now - timedelta(days=50))
    # 5 clean completions after the late_cancel
    for _ in range(5):
        _add_event_at(db_session, picker_user.id, "pickup_completed", now - timedelta(days=10))
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_healing_requires_exactly_5_not_4(db_session, picker_user):
    """4 clean completions after an infraction do not heal it."""
    now = datetime.utcnow()
    _add_event_at(db_session, picker_user.id, "no_show", now - timedelta(days=100))
    _add_event_at(db_session, picker_user.id, "late_cancel", now - timedelta(days=50))
    for _ in range(4):
        _add_event_at(db_session, picker_user.id, "pickup_completed", now - timedelta(days=10))
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD  # tuned arithmetic withheld


def test_score_goes_negative_and_clamps_at_floor(db_session, picker_user):
    """Accumulated deductions push the score below zero and the floor is -999."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    # 1 free + 14 dispute_lost_picker @ -7 each = 100 - 98 = 2; more → clamp
    _add_events(db_session, picker_user.id, "dispute_lost_picker", count=20)
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_many_completions_accumulate(db_session, picker_user):
    """12 completions earn 120, no ceiling reached."""
    _add_events(db_session, picker_user.id, "giveaway_completed", count=12)
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_unknown_event_types_ignored(db_session, picker_user):
    """Event types not in _INFRACTION_TYPES or _CLEAN_TYPES are silently ignored."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "scam_flagged")
    _add_events(db_session, picker_user.id, "reported")
    score = recalculate_trust(db_session, picker_user.id)
    assert score == WITHHELD


def test_column_updated_in_db(db_session, picker_user):
    """recalculate_trust writes the result back to user.trust_score."""
    _add_events(db_session, picker_user.id, "pickup_completed")
    _add_events(db_session, picker_user.id, "late_cancel", count=2)
    recalculate_trust(db_session, picker_user.id)
    db_session.commit()
    db_session.refresh(picker_user)
    assert picker_user.trust_score == WITHHELD

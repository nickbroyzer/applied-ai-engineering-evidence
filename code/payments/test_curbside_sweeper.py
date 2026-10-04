"""D524 — the curbside window end drives capture, and an unconfirmed set-out time cancels."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app import models
from app.jobs.post_window_sweeper import run_post_window_sweeper


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_curbside_booked(db_session, claim, *, setout_hours_ago: float, window_hours_ago: float):
    """A confirmed curbside pickup: set out earlier, window closed window_hours_ago."""
    db_session.execute(
        text(
            "UPDATE claims SET status='pickup_scheduled', pickup_mode='porch',"
            " pickup_scheduled_at=:s, pickup_window_ends_at=:w WHERE id=:cid"
        ),
        {
            "s": _naive(_utcnow() - timedelta(hours=setout_hours_ago)),
            "w": _naive(_utcnow() - timedelta(hours=window_hours_ago)),
            "cid": str(claim.id),
        },
    )
    db_session.commit()
    db_session.expire_all()


def _capturing(db_session):
    """The real capture_payment_intent writes claim.status itself (stripe_service.py), so a
    plain stand-in leaves the claim untouched and every status assertion fails. This one does
    the same write, which is what the sweeper's own commit then persists."""
    def _capture(claim_id, db, reason=None):
        claim = db.get(models.Claim, claim_id)
        claim.status = "auto_captured"
        claim.captured_at = datetime.utcnow()
        claim.auto_captured_at = claim.captured_at
        db.add(claim)
        return {"id": "pi_test", "status": "succeeded"}
    return _capture


def test_curbside_not_captured_before_window_end_plus_24h(
    db_session, authorized_claim, claim_in_db, mocker,
):
    # Set out 26 hours ago, window closed 23 hours ago: the old rule would have captured
    # on the set-out time alone. The window end governs now, so it must not.
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    capture = mocker.patch("app.jobs.post_window_sweeper.capture_payment_intent")
    _make_curbside_booked(db_session, authorized_claim, setout_hours_ago=26, window_hours_ago=23)
    result = run_post_window_sweeper(db_session)
    assert capture.call_count == 0
    assert result.captured == 0
    assert claim_in_db(authorized_claim.id).status == "pickup_scheduled"


def test_curbside_captured_24h_after_window_end(
    db_session, authorized_claim, claim_in_db, mocker,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    mocker.patch(
        "app.jobs.post_window_sweeper.capture_payment_intent",
        side_effect=_capturing(db_session),
    )
    _make_curbside_booked(db_session, authorized_claim, setout_hours_ago=30, window_hours_ago=25)
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert claim_in_db(authorized_claim.id).status == "auto_captured"


def test_meet_capture_unchanged_by_the_window_column(
    db_session, authorized_claim, claim_in_db, mocker,
):
    # Meet in person leaves pickup_window_ends_at null and still captures 24h after the time.
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    mocker.patch(
        "app.jobs.post_window_sweeper.capture_payment_intent",
        side_effect=_capturing(db_session),
    )
    db_session.execute(
        text(
            "UPDATE claims SET status='pickup_scheduled', pickup_mode='meet',"
            " pickup_scheduled_at=:s WHERE id=:cid"
        ),
        {"s": _naive(_utcnow() - timedelta(hours=25)), "cid": str(authorized_claim.id)},
    )
    db_session.commit()
    db_session.expire_all()
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert claim_in_db(authorized_claim.id).status == "auto_captured"


def test_unconfirmed_curbside_proposal_cancels_at_the_setout_time(
    db_session, authorized_claim, claim_in_db, listing_in_db, trust_events_for, mocker,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    cancel = mocker.patch("app.jobs.post_window_sweeper.cancel_payment_intent")
    past = _naive(_utcnow() - timedelta(minutes=5)).isoformat()
    db_session.execute(
        text(
            "UPDATE claims SET pickup_mode='porch', proposed_times=CAST(:pt AS jsonb),"
            " pickup_scheduled_at=NULL WHERE id=:cid"
        ),
        {"pt": json.dumps([past]), "cid": str(authorized_claim.id)},
    )
    db_session.commit()
    db_session.expire_all()
    result = run_post_window_sweeper(db_session)
    assert result.auto_cancelled == 1
    assert cancel.call_count == 1
    assert claim_in_db(authorized_claim.id).status == "cancelled"
    assert listing_in_db(authorized_claim.listing_id).status == "active"
    assert len(trust_events_for(authorized_claim.picker_id, "no_show")) == 0


def test_unconfirmed_curbside_proposal_survives_before_the_setout_time(
    db_session, authorized_claim, claim_in_db, mocker,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    cancel = mocker.patch("app.jobs.post_window_sweeper.cancel_payment_intent")
    future = _naive(_utcnow() + timedelta(hours=3)).isoformat()
    db_session.execute(
        text(
            "UPDATE claims SET pickup_mode='porch', proposed_times=CAST(:pt AS jsonb),"
            " pickup_scheduled_at=NULL WHERE id=:cid"
        ),
        {"pt": json.dumps([future]), "cid": str(authorized_claim.id)},
    )
    db_session.commit()
    db_session.expire_all()
    result = run_post_window_sweeper(db_session)
    assert result.auto_cancelled == 0
    assert cancel.call_count == 0
    assert claim_in_db(authorized_claim.id).status == "authorized"

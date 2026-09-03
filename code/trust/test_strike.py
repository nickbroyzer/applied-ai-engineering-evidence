"""D21 STEP 3 strike enforcement tests per survey Phase 6 + D25 + Amendment 1."""
import uuid
from datetime import datetime, timedelta

import stripe
from sqlalchemy import text

from app import models
from app.routers.claims import KNOWN_DISCLOSURE_VERSIONS
from app.services.strike_service import (
    _ROLLING_WINDOW_DAYS,
    _STRIKE_THRESHOLD,
    _TIMEOUT_DAYS,
    check_and_apply_strike,
)

_DISCLOSURE_VERSION = next(iter(KNOWN_DISCLOSURE_VERSIONS))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_no_show_event(db_session, user_id):
    db_session.add(
        models.TrustEvent(
            user_id=user_id,
            event_type="no_show",
        )
    )
    db_session.commit()


def _insert_historical_no_show(db_session, user_id, days_ago):
    """Insert a no_show TrustEvent and backdate created_at via raw SQL."""
    event = models.TrustEvent(
        user_id=user_id,
        event_type="no_show",
    )
    db_session.add(event)
    db_session.commit()
    backdated = datetime.utcnow() - timedelta(days=days_ago)
    db_session.execute(
        text("UPDATE trust_events SET created_at = :ca WHERE id = :eid"),
        {"ca": backdated, "eid": event.id},
    )
    db_session.commit()
    db_session.expire_all()
    return event


def _set_picker_timeout(db_session, user_id, until):
    """Set users.picker_timeout_until via raw SQL (naive UTC)."""
    db_session.execute(
        text("UPDATE users SET picker_timeout_until = :until WHERE id = :uid"),
        {"until": until, "uid": user_id},
    )
    db_session.commit()
    db_session.expire_all()


def _create_in_flight_claim(db_session, picker_id, giver_id, claim_status):
    """Create a fan-out target claim on a fresh listing.

    Each fan-out claim must live on its own listing because the partial unique
    index idx_claims_listing_claimed forbids two active claims on the same
    listing. listing.status mirrors the in-flight convention: 'active' for
    pending_payment, 'claimed' for authorized/pickup_scheduled.
    """
    listing_status = "active" if claim_status == "pending_payment" else "claimed"
    listing = models.Listing(
        giver_id=giver_id,
        title=f"Fan-out target {claim_status}",
        description="x",
        category="Other",
        photo_urls=["https://example.com/x.jpg"],
        location_lat=0.0,
        location_lng=0.0,
        location_lat_approx=0.001,
        location_lng_approx=0.001,
        status=listing_status,
        ai_generated=False,
    )
    db_session.add(listing)
    db_session.commit()

    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker_id,
        status=claim_status,
        stripe_payment_intent_id=f"pi_test_fanout_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(claim)
    db_session.commit()
    return claim, listing


# ---------------------------------------------------------------------------
# Threshold gate
# ---------------------------------------------------------------------------

def test_does_not_trip_below_threshold(db_session, picker_user):
    """Two no_show events: count is 2 < 3, no time-out applied."""
    for _ in range(2):
        _add_no_show_event(db_session, picker_user.id)

    check_and_apply_strike(db_session, picker_user.id)
    db_session.commit()
    db_session.expire_all()

    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is None


def test_trips_at_3rd_mark_no_show(
    auth_client, giver_user, picker_user, authorized_claim, db_session,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, mock_stripe_pi_cancel,
):
    """End-to-end: 3rd mark_no_show endpoint call sets picker_timeout_until."""
    for _ in range(2):
        _add_no_show_event(db_session, picker_user.id)

    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is not None
    expected = datetime.utcnow() + timedelta(days=_TIMEOUT_DAYS)
    assert abs((user.picker_timeout_until - expected).total_seconds()) < 60
    # No other in-flight claims for this picker → no fan-out PI cancel
    mock_stripe_pi_cancel.assert_not_called()


def test_trips_at_3rd_inside_window_cancel(
    auth_client, picker_user, authorized_claim, active_listing, db_session,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, mock_stripe_pi_cancel,
):
    """Inside-window picker-cancel writes late_cancel (not no_show), so the no_show
    strike counter is not incremented and picker_timeout_until stays None."""
    for _ in range(2):
        _add_no_show_event(db_session, picker_user.id)

    pickup_at = datetime.utcnow() + timedelta(hours=1)
    db_session.execute(
        text("UPDATE claims SET pickup_scheduled_at=:t WHERE id=:cid"),
        {"cid": authorized_claim.id, "t": pickup_at},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/cancel")
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is None
    mock_stripe_pi_cancel.assert_not_called()


def test_mixed_events_count_correctly(db_session, picker_user):
    """D25: strike counter counts no_show TrustEvents regardless of call site.

    The strike rule reads event_type only. Inside-window cancels now write
    late_cancel and do NOT count toward this threshold.
    """
    for _ in range(_STRIKE_THRESHOLD):
        _add_no_show_event(db_session, picker_user.id)

    check_and_apply_strike(db_session, picker_user.id)
    db_session.commit()
    db_session.expire_all()

    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is not None


def test_window_excludes_old_events(db_session, picker_user):
    """No_show events older than 30 days fall outside the rolling window."""
    _insert_historical_no_show(
        db_session, picker_user.id, days_ago=_ROLLING_WINDOW_DAYS + 1,
    )
    _add_no_show_event(db_session, picker_user.id)
    _add_no_show_event(db_session, picker_user.id)

    check_and_apply_strike(db_session, picker_user.id)
    db_session.commit()
    db_session.expire_all()

    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is None


# ---------------------------------------------------------------------------
# Fan-out behavior
# ---------------------------------------------------------------------------

def test_fan_out_voids_other_in_flight_claims_only(
    db_session, picker_user, giver_user, mock_stripe_pi_cancel,
):
    """Fan-out cancels claims with status IN (pending_payment, authorized, pickup_scheduled).

    Terminal-status claims (cancelled, completed, no_show) are excluded by the
    filter. Listings of authorized/pickup_scheduled claims flip to 'active';
    pending_payment listings were already 'active' and stay so.
    """
    pending_c, pending_listing = _create_in_flight_claim(
        db_session, picker_user.id, giver_user.id, "pending_payment",
    )
    auth_c, auth_listing = _create_in_flight_claim(
        db_session, picker_user.id, giver_user.id, "authorized",
    )
    sched_c, sched_listing = _create_in_flight_claim(
        db_session, picker_user.id, giver_user.id, "pickup_scheduled",
    )

    # Untouched terminal-status claim on its own listing
    completed_listing = models.Listing(
        giver_id=giver_user.id,
        title="Completed", description="x", category="Other",
        photo_urls=["https://example.com/x.jpg"],
        location_lat=0.0, location_lng=0.0,
        location_lat_approx=0.001, location_lng_approx=0.001,
        status="completed", ai_generated=False,
    )
    db_session.add(completed_listing)
    db_session.commit()
    completed_c = models.Claim(
        listing_id=completed_listing.id,
        picker_id=picker_user.id,
        status="completed",
        completion_photo_url="https://example.com/photo.jpg",
        captured_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(completed_c)
    db_session.commit()

    for _ in range(_STRIKE_THRESHOLD):
        _add_no_show_event(db_session, picker_user.id)

    check_and_apply_strike(db_session, picker_user.id)
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(models.Claim, pending_c.id).status == "cancelled"
    assert db_session.get(models.Claim, auth_c.id).status == "cancelled"
    assert db_session.get(models.Claim, sched_c.id).status == "cancelled"
    assert db_session.get(models.Claim, completed_c.id).status == "completed"

    assert db_session.get(models.Listing, pending_listing.id).status == "active"
    assert db_session.get(models.Listing, auth_listing.id).status == "active"
    assert db_session.get(models.Listing, sched_listing.id).status == "active"
    assert db_session.get(models.Listing, completed_listing.id).status == "completed"

    assert mock_stripe_pi_cancel.call_count == 3


def test_fan_out_failure_rolls_back_everything(
    auth_client, giver_user, picker_user, authorized_claim, active_listing, db_session,
    mocker, mock_stripe_pi_retrieve, mock_stripe_pi_capture,
    claim_in_db, listing_in_db, trust_events_for,
):
    """Amendment 1: fan-out Stripe failure rolls back the whole transaction.

    mark_no_show captures the originating PI (success), inserts a no_show
    TrustEvent, then check_and_apply_strike's fan-out hits a Stripe cancel
    error on the picker's other in-flight claim. The exception propagates and
    mark_no_show's StripeServiceError handler rolls everything back: capture's
    claim-status write, listing release, trust event insert, picker_timeout
    write, fan-out claim mutations.
    """
    for _ in range(2):
        _add_no_show_event(db_session, picker_user.id)

    fanout_claim, fanout_listing = _create_in_flight_claim(
        db_session, picker_user.id, giver_user.id, "authorized",
    )

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        side_effect=stripe.error.APIConnectionError("simulated"),
    )

    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 502

    db_session.expire_all()
    user = db_session.get(models.User, picker_user.id)
    assert user.picker_timeout_until is None

    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "authorized"
    assert claim.no_show_at is None
    listing = listing_in_db(active_listing.id)
    assert listing.status == "claimed"

    fc = db_session.get(models.Claim, fanout_claim.id)
    assert fc.status == "authorized"
    fl = db_session.get(models.Listing, fanout_listing.id)
    assert fl.status == "claimed"

    # The 2 pre-inserted events persist (committed before the request); the
    # 3rd event (mark_no_show insert) was rolled back.
    assert len(trust_events_for(picker_user.id, "no_show")) == 2


# ---------------------------------------------------------------------------
# create_claim enforcement gate
# ---------------------------------------------------------------------------

def test_create_claim_403_when_picker_in_timeout(
    auth_client, picker_user, active_listing, db_session, mock_stripe_pi_create,
):
    """create_claim returns 403 picker_in_timeout when picker_timeout_until is in the future."""
    _set_picker_timeout(
        db_session, picker_user.id, datetime.utcnow() + timedelta(days=1),
    )

    resp = auth_client(picker_user).post(
        "/claims",
        json={
            "listing_id": str(active_listing.id),
            "disclosure_version": _DISCLOSURE_VERSION,
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "picker_in_timeout"


def test_create_claim_succeeds_when_timeout_expired(
    auth_client, picker_user, active_listing, db_session, mock_stripe_pi_create,
):
    """create_claim returns 201 when picker_timeout_until is in the past."""
    _set_picker_timeout(
        db_session, picker_user.id, datetime.utcnow() - timedelta(days=1),
    )

    resp = auth_client(picker_user).post(
        "/claims",
        json={
            "listing_id": str(active_listing.id),
            "disclosure_version": _DISCLOSURE_VERSION,
        },
    )
    assert resp.status_code == 201, resp.text

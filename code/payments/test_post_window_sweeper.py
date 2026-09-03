"""Phase 9-1 D55 — post-window sweeper tests."""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import text

from app import models
from app.jobs.post_window_sweeper import run_post_window_sweeper
from app.services import notification_service


def _patch_httpx(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"status": "ok"}]}
    mock_response.raise_for_status.return_value = None
    mock_client = mocker.MagicMock()
    mock_client.post.return_value = mock_response
    cls = mocker.patch.object(notification_service.httpx, "Client")
    cls.return_value.__enter__.return_value = mock_client
    return mock_client.post


def _make_claim(
    db_session,
    listing,
    picker,
    *,
    status,
    pickup_offset_hours: float,
    geofence_offset_hours: float | None,
):
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="pending_payment",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    pickup_at = datetime.utcnow() + timedelta(hours=pickup_offset_hours)
    params = {
        "cid": claim.id,
        "s": status,
        "t": pickup_at,
    }
    if geofence_offset_hours is None:
        db_session.execute(
            text(
                "UPDATE claims SET status=:s, pickup_scheduled_at=:t, "
                "authorized_at=:t WHERE id=:cid"
            ),
            params,
        )
    else:
        params["g"] = datetime.utcnow() + timedelta(hours=geofence_offset_hours)
        db_session.execute(
            text(
                "UPDATE claims SET status=:s, pickup_scheduled_at=:t, "
                "geofence_confirmed_at=:g, authorized_at=:t WHERE id=:cid"
            ),
            params,
        )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(models.Claim, claim.id)


def _give_user_token(db_session, user):
    user.expo_push_token = f"ExponentPushToken[{uuid.uuid4().hex[:10]}]"
    db_session.commit()
    db_session.refresh(user)


def test_sweeper_captures_geofence_t_plus_2h_happy_path(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)

    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-2.5,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 1
    assert result.skipped_underfunded == 0
    assert result.errored == 0

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "auto_captured"
    assert fresh_claim.auto_captured_at is not None

    fresh_listing = db_session.get(models.Listing, active_listing.id)
    assert fresh_listing.status == "completed"
    assert fresh_listing.completed_at is not None

    picker_events = (
        db_session.query(models.TrustEvent)
        .filter(
            models.TrustEvent.user_id == picker_user.id,
            models.TrustEvent.event_type == "pickup_completed",
        )
        .count()
    )
    giver_events = (
        db_session.query(models.TrustEvent)
        .filter(
            models.TrustEvent.user_id == giver_user.id,
            models.TrustEvent.event_type == "giveaway_completed",
        )
        .count()
    )
    assert picker_events == 1
    assert giver_events == 1


def test_sweeper_captures_no_geofence_t_plus_24h_happy_path(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)

    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pickup_scheduled",
        pickup_offset_hours=-25,
        geofence_offset_hours=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 1
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "auto_captured"
    assert fresh.geofence_confirmed_at is None


def test_sweeper_skips_geofence_at_t_plus_1h(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _patch_httpx(mocker)
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-1,
        geofence_offset_hours=-0.83,  # 50 min ago
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    assert result.skipped_underfunded == 0
    assert result.errored == 0
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.auto_captured_at is None


def test_sweeper_skips_no_geofence_at_t_plus_23h(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _patch_httpx(mocker)
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-23,
        geofence_offset_hours=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"


def test_sweeper_skips_underfunded_and_logs_both_event_names(
    mocker, db_session, picker_user, giver_user, active_listing,
    stripe_pi_factory,
):
    _patch_httpx(mocker)
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(amount_capturable=50, status="requires_capture"),
    )
    capture_spy = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
    )

    stripe_logger_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "error",
    )
    sweeper_logger_spy = mocker.spy(
        __import__("app.jobs.post_window_sweeper", fromlist=["logger"]).logger,
        "error",
    )

    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-2.5,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    assert result.skipped_underfunded == 1
    assert result.errored == 0
    capture_spy.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.auto_captured_at is None

    stripe_payloads = [
        c.args[0] for c in stripe_logger_spy.call_args_list if c.args
    ]
    sweeper_payloads = [
        c.args[0] for c in sweeper_logger_spy.call_args_list if c.args
    ]
    assert any(
        "post_window_capture_underfunded_likely_stripe_autovoid" in p
        for p in stripe_payloads
    )
    assert any(
        "post_window_sweeper_underfunded" in p for p in sweeper_payloads
    )


def test_sweeper_idempotent_second_run_finds_zero(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)
    _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-2.5,
    )

    first = run_post_window_sweeper(db_session)
    assert first.captured == 1

    db_session.expire_all()
    second = run_post_window_sweeper(db_session)
    assert second.captured == 0
    assert second.skipped_underfunded == 0
    assert second.errored == 0


def test_sweeper_calls_capture_with_post_window_reason(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)
    capture_spy = mocker.spy(
        __import__("app.jobs.post_window_sweeper", fromlist=["capture_payment_intent"]),
        "capture_payment_intent",
    )
    _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-2.5,
    )

    run_post_window_sweeper(db_session)

    assert capture_spy.call_count == 1
    _, kwargs = capture_spy.call_args
    assert kwargs.get("reason") == "post_window"


def test_admin_endpoint_returns_result_shape(
    mocker, db_session, auth_client, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)
    _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-2.5,
    )

    picker_user.is_admin = True
    db_session.commit()
    resp = auth_client(picker_user).post("/admin/run-post-window-sweeper")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "captured": 1,
        "skipped_underfunded": 0,
        "errored": 0,
        "auto_cancelled": 0,
        "reminders_sent": 0,
    }


def _make_extra_listing(db_session, giver_user):
    listing = models.Listing(
        giver_id=giver_user.id,
        title="Sweeper counter listing",
        description="An item for counter test via sweeper.",
        category="Other",
        photo_urls=["https://example.com/sw.jpg"],
        location_lat=37.7749,
        location_lng=-122.4194,
        location_lat_approx=37.7760,
        location_lng_approx=-122.4182,
        status="claimed",
        ai_generated=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


def test_sweeper_increments_completed_counters_across_three_claims(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """Group 5 follow-up — sweeping three pending-confirmation claims for the
    same picker bumps picker.completed_pickups and giver.completed_giveaways
    to 3 each."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)

    _make_claim(
        db_session, active_listing, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )
    listing_2 = _make_extra_listing(db_session, giver_user)
    _make_claim(
        db_session, listing_2, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )
    listing_3 = _make_extra_listing(db_session, giver_user)
    _make_claim(
        db_session, listing_3, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )

    result = run_post_window_sweeper(db_session)
    assert result.captured == 3
    assert result.skipped_underfunded == 0
    assert result.errored == 0

    db_session.expire_all()
    fresh_picker = db_session.get(models.User, picker_user.id)
    fresh_giver = db_session.get(models.User, giver_user.id)
    assert fresh_picker.completed_pickups == 3
    assert fresh_giver.completed_giveaways == 3


# ---------------------------------------------------------------------------
# D105 — auto-cancel at T+6d and T-24h reminder routing
# ---------------------------------------------------------------------------


def _make_authorized_claim(
    db_session,
    listing,
    picker,
    *,
    authorized_offset_days: float,
    pickup_mode: str | None = None,
    proposed_times=None,
    pickup_scheduled_at=None,
):
    """Create an authorized claim with authorized_at set relative to now."""
    import json as _json
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="pending_payment",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    authorized_at = datetime.utcnow() - timedelta(days=authorized_offset_days)
    db_session.execute(
        text(
            "UPDATE claims SET status='authorized', authorized_at=:a,"
            " pickup_mode=:m, proposed_times=CAST(:pt AS jsonb),"
            " pickup_scheduled_at=:psa"
            " WHERE id=:cid"
        ),
        {
            "cid": claim.id,
            "a": authorized_at,
            "m": pickup_mode,
            "pt": _json.dumps(proposed_times) if proposed_times is not None else None,
            "psa": pickup_scheduled_at,
        },
    )
    db_session.execute(
        text("UPDATE listings SET status='claimed' WHERE id=:lid"),
        {"lid": listing.id},
    )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(models.Claim, claim.id)


def test_auto_cancel_no_mode_after_6d(
    mocker, db_session, picker_user, giver_user, active_listing,
):
    """Claim authorized > 6d ago with pickup_mode IS NULL → cancelled, PI voided, listing relisted."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")

    claim = _make_authorized_claim(
        db_session, active_listing, picker_user,
        authorized_offset_days=6.1,
        pickup_mode=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.auto_cancelled == 1
    assert result.captured == 0

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "cancelled"

    fresh_listing = db_session.get(models.Listing, active_listing.id)
    assert fresh_listing.status == "active"

    trust_events = db_session.query(models.TrustEvent).filter(
        models.TrustEvent.user_id == picker_user.id
    ).all()
    assert len(trust_events) == 0

    notifications = db_session.query(models.Notification).filter(
        models.Notification.notification_type.in_(
            ["claim_auto_cancelled_picker", "claim_auto_cancelled_giver"]
        )
    ).all()
    assert len(notifications) == 2
    for notification in notifications:
        assert notification.listing_id == active_listing.id


def test_auto_cancel_meet_no_selection_after_6d(
    mocker, db_session, picker_user, giver_user, active_listing,
):
    """Claim authorized > 6d ago with pickup_mode='meet' + no selection → cancelled."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")

    claim = _make_authorized_claim(
        db_session, active_listing, picker_user,
        authorized_offset_days=6.1,
        pickup_mode="meet",
        proposed_times=[
            (datetime.utcnow() + timedelta(hours=i + 1)).replace(microsecond=0).isoformat()
            for i in range(3)
        ],
    )

    result = run_post_window_sweeper(db_session)

    assert result.auto_cancelled == 1

    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "cancelled"
    assert db_session.get(models.Listing, active_listing.id).status == "active"


def test_d55_capture_survives_d105_auto_cancel(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """D55 capture path is unchanged by D105: pickup_scheduled_at past threshold → captured."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)

    # Claim with pickup_scheduled_at set (well past threshold) — D55 territory.
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pickup_scheduled",
        pickup_offset_hours=-25,
        geofence_offset_hours=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 1
    assert result.auto_cancelled == 0

    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "auto_captured"


def test_t_minus_24h_reminder_no_mode_pushes_giver(
    mocker, db_session, picker_user, giver_user, active_listing,
):
    """T-24h window, pickup_mode IS NULL → giver gets pickup_setup_reminder_giver."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    push_post = _patch_httpx(mocker)

    _make_authorized_claim(
        db_session, active_listing, picker_user,
        authorized_offset_days=5.1,
        pickup_mode=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.reminders_sent == 1
    assert result.auto_cancelled == 0
    assert push_post.called
    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.recipient_id == giver_user.id,
            models.Notification.notification_type == "pickup_setup_reminder_giver",
        )
        .count()
    ) == 1


def test_t_minus_24h_reminder_meet_no_selection_pushes_picker(
    mocker, db_session, picker_user, giver_user, active_listing,
):
    """T-24h window, pickup_mode='meet' + no selection → picker gets pickup_select_reminder_picker."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    push_post = _patch_httpx(mocker)

    _make_authorized_claim(
        db_session, active_listing, picker_user,
        authorized_offset_days=5.1,
        pickup_mode="meet",
        proposed_times=[
            (datetime.utcnow() + timedelta(hours=i + 1)).replace(microsecond=0).isoformat()
            for i in range(3)
        ],
    )

    result = run_post_window_sweeper(db_session)

    assert result.reminders_sent == 1
    assert push_post.called
    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.recipient_id == picker_user.id,
            models.Notification.notification_type == "pickup_select_reminder_picker",
        )
        .count()
    ) == 1


def test_t_minus_24h_reminder_scheduled_pushes_both_idempotent(
    mocker, db_session, picker_user, giver_user, active_listing,
):
    """T-24h window, pickup_scheduled_at set → both parties notified; second run is dedup'd."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    push_post = _patch_httpx(mocker)

    scheduled_at = datetime.utcnow() + timedelta(hours=24)
    _make_authorized_claim(
        db_session, active_listing, picker_user,
        authorized_offset_days=5.1,
        pickup_mode="meet",
        pickup_scheduled_at=scheduled_at,
    )

    first = run_post_window_sweeper(db_session)
    first_call_count = push_post.call_count

    assert first.reminders_sent == 1
    assert first_call_count == 2
    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.recipient_id == giver_user.id,
            models.Notification.notification_type == "pickup_imminent_reminder_giver",
        )
        .count()
    ) == 1
    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.recipient_id == picker_user.id,
            models.Notification.notification_type == "pickup_imminent_reminder_picker",
        )
        .count()
    ) == 1

    db_session.expire_all()
    second = run_post_window_sweeper(db_session)

    assert second.reminders_sent == 0
    assert push_post.call_count == first_call_count


def test_sweeper_releases_blocked_claim_instead_of_capturing(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """Nick 2026-08-10: blocking never costs the picker money. A claim left live by a
    block whose cancellation failed at Stripe is invisible to both parties, so this
    sweep is the only thing that can still reach it — it must release, never capture."""
    _patch_httpx(mocker)
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-30,
        geofence_offset_hours=None,
    )
    db_session.add(
        models.BlockedUser(blocker_id=picker_user.id, blocked_id=giver_user.id)
    )
    db_session.execute(
        text("UPDATE listings SET status='claimed' WHERE id=:lid"),
        {"lid": active_listing.id},
    )
    db_session.commit()
    db_session.expire_all()

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    mock_stripe_pi_capture.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "cancelled"
    assert fresh.cancelled_at is not None
    assert fresh.captured_at is None

    fresh_listing = db_session.get(models.Listing, active_listing.id)
    assert fresh_listing.status == "active"


def test_sweeper_still_captures_when_no_block_exists(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """Guard against the block check swallowing the ordinary path: with no block
    between the parties, the same claim shape must still capture as before."""
    _give_user_token(db_session, picker_user)
    _give_user_token(db_session, giver_user)
    _patch_httpx(mocker)

    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-30,
        geofence_offset_hours=None,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 1

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "auto_captured"
    assert fresh.captured_at is not None


def test_sweeper_waits_two_hours_after_a_late_ping(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """D444 — appointment 3h ago but the picker pinged only 1h ago: not yet eligible."""
    _patch_httpx(mocker)
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-3,
        geofence_offset_hours=-1,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    assert result.skipped_underfunded == 0
    assert result.errored == 0
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.auto_captured_at is None


def test_sweeper_early_ping_still_waits_for_appointment_plus_two_hours(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """D444 — pinged 5h ago but the appointment was only 1h ago: not yet eligible."""
    _patch_httpx(mocker)
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized",
        pickup_offset_hours=-1,
        geofence_offset_hours=-5,
    )

    result = run_post_window_sweeper(db_session)

    assert result.captured == 0
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"

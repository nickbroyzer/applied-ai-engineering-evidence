"""Block / unblock endpoint tests."""
import uuid


def test_block_user_returns_blocked_true(auth_client, picker_user, giver_user):
    resp = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"blocked": True}


def test_block_user_is_idempotent(auth_client, picker_user, giver_user):
    first = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert first.status_code == 200, first.text
    second = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert second.status_code == 200, second.text
    assert second.json() == {"blocked": True}


def test_block_user_second_call_does_not_recancel_claims(
    mocker, auth_client, picker_user, giver_user,
):
    mock_cancel = mocker.patch("app.routers.blocks._cancel_claims_for_block")

    first = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert first.status_code == 200, first.text
    assert first.json() == {"blocked": True}

    second = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert second.status_code == 200, second.text
    assert second.json() == {"blocked": True}

    mock_cancel.assert_called_once()


def test_list_blocks_contains_blocked_user(auth_client, picker_user, giver_user):
    auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    resp = auth_client(picker_user).get("/users/me/blocks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    row = body[0]
    assert row["user_id"] == str(giver_user.id)
    assert row["display_name"] == giver_user.display_name
    assert "blocked_at" in row


def test_self_block_returns_400(auth_client, picker_user):
    resp = auth_client(picker_user).post(f"/users/{picker_user.id}/block")
    assert resp.status_code == 400, resp.text


def test_unblock_user_returns_204(auth_client, picker_user, giver_user):
    auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    resp = auth_client(picker_user).delete(f"/users/{giver_user.id}/block")
    assert resp.status_code == 204, resp.text


def test_list_blocks_empty_after_unblock(auth_client, picker_user, giver_user):
    auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    auth_client(picker_user).delete(f"/users/{giver_user.id}/block")
    resp = auth_client(picker_user).get("/users/me/blocks")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_block_missing_user_returns_404(auth_client, picker_user):
    resp = auth_client(picker_user).post(f"/users/{uuid.uuid4()}/block")
    assert resp.status_code == 404, resp.text


# --- is_blocked unit tests ---

from app.models import BlockedUser  # noqa: E402
from app.services.block_service import is_blocked  # noqa: E402


def test_is_blocked_a_blocked_b(db_session, picker_user, giver_user):
    db_session.add(BlockedUser(blocker_id=picker_user.id, blocked_id=giver_user.id))
    db_session.commit()
    assert is_blocked(db_session, picker_user.id, giver_user.id) is True


def test_is_blocked_b_blocked_a(db_session, picker_user, giver_user):
    db_session.add(BlockedUser(blocker_id=giver_user.id, blocked_id=picker_user.id))
    db_session.commit()
    assert is_blocked(db_session, picker_user.id, giver_user.id) is True


def test_is_blocked_no_block(db_session, picker_user, giver_user):
    assert is_blocked(db_session, picker_user.id, giver_user.id) is False


def test_is_blocked_self_pair(db_session, picker_user):
    assert is_blocked(db_session, picker_user.id, picker_user.id) is False


# ---------------------------------------------------------------------------
# Read-endpoint block-filtering tests
# ---------------------------------------------------------------------------

import uuid as _uuid  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from sqlalchemy import text  # noqa: E402

from app.models import BlockedUser, Claim, Listing, Message, Notification, User  # noqa: E402
from app.services.coordinate_privacy import generate_approximate_point  # noqa: E402


def _make_listing(db_session, giver_user):
    lid = _uuid.uuid4()
    lat, lng = 37.7749, -122.4194
    alat, alng = generate_approximate_point(lat, lng, lid)
    listing = Listing(
        id=lid,
        giver_id=giver_user.id,
        title="Block Test Listing",
        description="desc",
        category="Other",
        photo_urls=["https://example.com/x.jpg"],
        location_lat=lat,
        location_lng=lng,
        location_lat_approx=alat,
        location_lng_approx=alng,
        status="active",
        ai_generated=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


def _make_authorized_claim(db_session, listing, picker_user):
    from sqlalchemy import text
    claim = Claim(
        listing_id=listing.id,
        picker_id=picker_user.id,
        status="authorized",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    db_session.execute(
        text("UPDATE claims SET authorized_at=timezone('utc', now()) WHERE id=:cid"),
        {"cid": claim.id},
    )
    db_session.execute(
        text("UPDATE listings SET status='claimed' WHERE id=:lid"),
        {"lid": listing.id},
    )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(Claim, claim.id)


def _block(db_session, blocker, blocked):
    db_session.add(BlockedUser(blocker_id=blocker.id, blocked_id=blocked.id))
    db_session.commit()


# --- by-user ---

def test_by_user_returns_empty_when_viewer_blocked_giver(
    auth_client, picker_user, giver_user, db_session
):
    _make_listing(db_session, giver_user)
    _block(db_session, picker_user, giver_user)
    resp = auth_client(picker_user).get(f"/listings/by-user/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_by_user_returns_empty_when_giver_blocked_viewer(
    auth_client, picker_user, giver_user, db_session
):
    _make_listing(db_session, giver_user)
    _block(db_session, giver_user, picker_user)
    resp = auth_client(picker_user).get(f"/listings/by-user/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_by_user_returns_listings_when_no_block(
    auth_client, picker_user, giver_user, db_session
):
    _make_listing(db_session, giver_user)
    resp = auth_client(picker_user).get(f"/listings/by-user/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


# --- inbox ---

def _send_message(db_session, listing, sender_id, recipient_id):
    msg = Message(
        listing_id=listing.id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="hello",
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg


def test_inbox_omits_thread_when_counterparty_blocked(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    _block(db_session, picker_user, giver_user)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_inbox_omits_thread_when_counterparty_blocked_reverse(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    _block(db_session, giver_user, picker_user)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_inbox_keeps_unblocked_threads(
    auth_client, picker_user, giver_user, other_picker_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    # block other_picker_user but not giver_user
    _block(db_session, picker_user, other_picker_user)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


def _make_claim_with_status(db_session, listing, picker_user, claim_status):
    claim = Claim(
        listing_id=listing.id,
        picker_id=picker_user.id,
        status=claim_status,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


def test_inbox_omits_thread_when_only_claim_cancelled(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_claim_with_status(db_session, listing, picker_user, "cancelled")
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_inbox_omits_thread_when_only_claim_no_show(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_claim_with_status(db_session, listing, picker_user, "no_show")
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_inbox_keeps_thread_when_claim_authorized(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


def test_inbox_keeps_thread_when_claim_completed(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_claim_with_status(db_session, listing, picker_user, "completed")
    _send_message(db_session, listing, picker_user.id, giver_user.id)
    resp = auth_client(picker_user).get("/messages/inbox")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


# --- my-picker-active ---

def test_picker_active_omits_claim_when_giver_blocked(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, picker_user, giver_user)
    resp = auth_client(picker_user).get("/claims/my-picker-active")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_picker_active_omits_claim_when_giver_blocked_reverse(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, giver_user, picker_user)
    resp = auth_client(picker_user).get("/claims/my-picker-active")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_picker_active_keeps_unblocked_claim(
    auth_client, picker_user, giver_user, other_picker_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, picker_user, other_picker_user)
    resp = auth_client(picker_user).get("/claims/my-picker-active")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


# --- my-giver-active ---

def test_giver_active_omits_claim_when_picker_blocked(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, giver_user, picker_user)
    resp = auth_client(giver_user).get("/claims/my-giver-active")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_giver_active_omits_claim_when_picker_blocked_reverse(
    auth_client, picker_user, giver_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, picker_user, giver_user)
    resp = auth_client(giver_user).get("/claims/my-giver-active")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_giver_active_keeps_unblocked_claim(
    auth_client, picker_user, giver_user, other_picker_user, db_session
):
    listing = _make_listing(db_session, giver_user)
    _make_authorized_claim(db_session, listing, picker_user)
    _block(db_session, giver_user, other_picker_user)
    resp = auth_client(giver_user).get("/claims/my-giver-active")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Stage 2 block-enforcement tests: claim cancellation on block
# ---------------------------------------------------------------------------

def _set_stripe_pi_id(db_session, claim_id, pi_id="pi_test_block"):
    db_session.execute(
        text("UPDATE claims SET stripe_payment_intent_id=:pi WHERE id=:cid"),
        {"cid": claim_id, "pi": pi_id},
    )
    db_session.commit()
    db_session.expire_all()


def _set_pickup_at(db_session, claim_id, *, status, pickup_at):
    # pickup_scheduled_at is TIMESTAMP WITHOUT TIME ZONE; the codebase stores
    # naive UTC there. Binding an aware datetime makes psycopg2 send a timestamptz,
    # which Postgres localizes to the session TimeZone on assignment to a naive
    # column (e.g. Pacific/Honolulu on a dev box), corrupting the stored instant.
    # Normalize to naive UTC to match the column convention.
    if pickup_at.tzinfo is not None:
        pickup_at = pickup_at.astimezone(timezone.utc).replace(tzinfo=None)
    db_session.execute(
        text("UPDATE claims SET status=:s, pickup_scheduled_at=:t WHERE id=:cid"),
        {"cid": claim_id, "s": status, "t": pickup_at},
    )
    db_session.commit()
    db_session.expire_all()


def test_block_far_pickup_releases_pi(
    auth_client, picker_user, giver_user, db_session, mock_stripe_pi_cancel
):
    """Picker blocks giver, pickup >2h away → cancel_payment_intent called, claim cancelled, giver notified."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_stripe_pi_id(db_session, claim.id, "pi_far_test")
    _set_pickup_at(
        db_session, claim.id,
        status="pickup_scheduled",
        pickup_at=datetime.now(timezone.utc) + timedelta(hours=4),
    )

    resp = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"blocked": True}

    mock_stripe_pi_cancel.assert_called_once()

    db_session.expire_all()
    updated = db_session.get(Claim, claim.id)
    assert updated.status == "cancelled"

    notifs = (
        db_session.query(Notification)
        .filter(
            Notification.recipient_id == giver_user.id,
            Notification.notification_type == "claim_cancelled_by_picker",
        )
        .all()
    )
    assert len(notifs) == 1


def test_block_near_pickup_releases_pi_no_strike(
    auth_client, picker_user, giver_user, db_session,
    mock_stripe_pi_cancel, mock_stripe_pi_capture,
    trust_events_for, report_in_db,
):
    """Picker blocks giver, pickup <2h away → the 2h grace window does NOT apply
    to a block. RULED by Nick 2026-08-10: a block never charges the picker and
    never files a strike, regardless of timing. cancel_payment_intent (release)
    is called, not capture; the claim ends cancelled, not no_show; no late_cancel
    trust event is filed; and a Report row records the block for pattern review."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_stripe_pi_id(db_session, claim.id, "pi_near_test")
    _set_pickup_at(
        db_session, claim.id,
        status="pickup_scheduled",
        pickup_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    resp = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert resp.status_code == 200, resp.text

    mock_stripe_pi_cancel.assert_called_once()
    mock_stripe_pi_capture.assert_not_called()

    db_session.expire_all()
    updated = db_session.get(Claim, claim.id)
    assert updated.status == "cancelled"
    assert updated.cancelled_at is not None

    assert trust_events_for(picker_user.id, "late_cancel") == []

    db_session.expire_all()
    picker = db_session.get(User, picker_user.id)
    assert picker.picker_timeout_until is None

    reports = report_in_db(picker_user.id)
    assert len(reports) == 1
    assert reports[0].triggered_rule == "block_ended_claim"
    assert reports[0].source == "auto"
    assert reports[0].reason == "other"
    assert str(claim.id) in reports[0].description

    notifs = (
        db_session.query(Notification)
        .filter(
            Notification.recipient_id == giver_user.id,
            Notification.notification_type == "claim_cancelled_by_picker",
        )
        .all()
    )
    assert len(notifs) == 1


def test_block_authorized_no_pickup_releases_pi(
    auth_client, picker_user, giver_user, db_session, mock_stripe_pi_cancel
):
    """Picker blocks giver, authorized claim with no pickup_scheduled_at → cancel PI, claim cancelled, giver notified."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_stripe_pi_id(db_session, claim.id, "pi_auth_test")

    resp = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert resp.status_code == 200, resp.text

    mock_stripe_pi_cancel.assert_called_once()

    db_session.expire_all()
    updated = db_session.get(Claim, claim.id)
    assert updated.status == "cancelled"

    notifs = (
        db_session.query(Notification)
        .filter(
            Notification.recipient_id == giver_user.id,
            Notification.notification_type == "claim_cancelled_by_picker",
        )
        .all()
    )
    assert len(notifs) == 1


def test_block_giver_blocks_picker_releases_no_trust_event(
    auth_client, picker_user, giver_user, db_session,
    mock_stripe_pi_cancel, trust_events_for,
):
    """Giver blocks picker → cancel PI, no giver_cancelled_listing trust event, picker notified."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_stripe_pi_id(db_session, claim.id, "pi_giver_test")

    resp = auth_client(giver_user).post(f"/users/{picker_user.id}/block")
    assert resp.status_code == 200, resp.text

    mock_stripe_pi_cancel.assert_called_once()

    db_session.expire_all()
    updated = db_session.get(Claim, claim.id)
    assert updated.status == "cancelled"

    assert len(trust_events_for(giver_user.id, "giver_cancelled_listing")) == 0

    notifs = (
        db_session.query(Notification)
        .filter(
            Notification.recipient_id == picker_user.id,
            Notification.notification_type == "claim_cancelled_by_giver",
        )
        .all()
    )
    assert len(notifs) == 1


def test_block_no_claim_no_pi_call(
    auth_client, picker_user, giver_user, db_session, mocker
):
    """Block with no active claim between parties → no Stripe call, block succeeds."""
    stripe_cancel = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    stripe_capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    resp = auth_client(picker_user).post(f"/users/{giver_user.id}/block")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"blocked": True}

    stripe_cancel.assert_not_called()
    stripe_capture.assert_not_called()


# ---------------------------------------------------------------------------
# GET /claims/block-preview/{target_user_id} tests
# ---------------------------------------------------------------------------

def test_block_preview_no_active_claim(auth_client, picker_user, giver_user):
    """No active claim between parties → has_active_claim=False, role=None, inside_grace_window=False (Modal C)."""
    resp = auth_client(picker_user).get(f"/claims/block-preview/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_active_claim"] is False
    assert data["role"] is None
    assert data["inside_grace_window"] is False
    assert data["listing_title"] is None


def test_block_preview_picker_far_pickup(
    auth_client, picker_user, giver_user, db_session
):
    """Current user is picker, pickup >2h away → role=picker, inside_grace_window=False (Modal A)."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_pickup_at(
        db_session, claim.id,
        status="pickup_scheduled",
        pickup_at=datetime.now(timezone.utc) + timedelta(hours=4),
    )
    resp = auth_client(picker_user).get(f"/claims/block-preview/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_active_claim"] is True
    assert data["role"] == "picker"
    assert data["inside_grace_window"] is False
    assert data["listing_title"] == "Block Test Listing"


def test_block_preview_picker_near_pickup(
    auth_client, picker_user, giver_user, db_session
):
    """Current user is picker, pickup <2h away → role=picker, inside_grace_window=True (Modal B)."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_pickup_at(
        db_session, claim.id,
        status="pickup_scheduled",
        pickup_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    resp = auth_client(picker_user).get(f"/claims/block-preview/{giver_user.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_active_claim"] is True
    assert data["role"] == "picker"
    assert data["inside_grace_window"] is True
    assert data["listing_title"] == "Block Test Listing"


def test_block_preview_current_user_is_giver(
    auth_client, picker_user, giver_user, db_session
):
    """Current user is giver with active claim from target → role=giver, inside_grace_window=False (Modal A path)."""
    listing = _make_listing(db_session, giver_user)
    claim = _make_authorized_claim(db_session, listing, picker_user)
    _set_pickup_at(
        db_session, claim.id,
        status="pickup_scheduled",
        pickup_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    resp = auth_client(giver_user).get(f"/claims/block-preview/{picker_user.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_active_claim"] is True
    assert data["role"] == "giver"
    assert data["inside_grace_window"] is False
    assert data["listing_title"] == "Block Test Listing"

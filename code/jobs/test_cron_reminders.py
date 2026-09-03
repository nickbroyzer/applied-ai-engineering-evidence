import uuid
from datetime import date, datetime, timedelta

import httpx

from app import models
from app.services import notification_service


def _patch_httpx_client(mocker, *, status_code: int = 200, raise_exc: Exception | None = None):
    """
    Patch app.services.notification_service.httpx.Client so the context manager's
    .post() returns a mock response with the given status_code, or raises raise_exc.
    Returns the mock_post for call assertions.
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = status_code
    # send_push reads the response body (_expo_rejection): a 200 with no ok ticket
    # is treated as a refusal, so the success mock must carry a real Expo body.
    mock_response.json.return_value = {"data": [{"status": "ok"}]}
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server error",
            request=mocker.MagicMock(),
            response=mock_response,
        )
    else:
        mock_response.raise_for_status.return_value = None

    mock_client_instance = mocker.MagicMock()
    if raise_exc is not None:
        mock_client_instance.post.side_effect = raise_exc
    else:
        mock_client_instance.post.return_value = mock_response

    mock_client_cls = mocker.patch.object(notification_service.httpx, "Client")
    mock_client_cls.return_value.__enter__.return_value = mock_client_instance
    return mock_client_instance.post


def _give_user_token(db_session, user):
    user.expo_push_token = f"ExponentPushToken[{uuid.uuid4().hex[:10]}]"
    db_session.commit()
    db_session.refresh(user)


def _make_listing(db_session, giver, *, status="active", title="Listing", expires_at=None):
    if expires_at is None:
        expires_at = datetime.utcnow() + timedelta(days=7)
    listing = models.Listing(
        giver_id=giver.id,
        title=title,
        description="An item for test pickup.",
        category="Other",
        photo_urls=["https://example.com/x.jpg"],
        location_lat=37.7749,
        location_lng=-122.4194,
        location_lat_approx=37.7760,
        location_lng_approx=-122.4182,
        status=status,
        ai_generated=False,
        expires_at=expires_at,
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


def _idempotency_count(db_session, notification_type, entity_id):
    return (
        db_session.query(models.NotificationIdempotency)
        .filter(
            models.NotificationIdempotency.notification_type == notification_type,
            models.NotificationIdempotency.entity_id == entity_id,
            models.NotificationIdempotency.date_bucket == date.today(),
        )
        .count()
    )


def test_listing_expiring_sends_giver_push_in_window(
    mocker, db_session, auth_client, picker_user, giver_user,
):
    _give_user_token(db_session, giver_user)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    listing = _make_listing(
        db_session, giver_user,
        status="active", expires_at=expires_at,
    )
    mock_post = _patch_httpx_client(mocker, status_code=200)

    picker_user.is_admin = True
    db_session.commit()
    resp = auth_client(picker_user).post("/admin/send-listing-expiring-reminders")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"sent_count": 1, "skipped_count": 0}
    assert mock_post.call_count == 1
    assert _idempotency_count(db_session, "listing_expiring", listing.id) == 1


def test_listing_expiring_skips_outside_window(
    mocker, db_session, auth_client, picker_user, giver_user,
):
    _give_user_token(db_session, giver_user)
    now = datetime.utcnow()
    _make_listing(
        db_session, giver_user,
        status="active", title="Before", expires_at=now + timedelta(hours=22),
    )
    in_window = _make_listing(
        db_session, giver_user,
        status="active", title="InWindow", expires_at=now + timedelta(hours=24),
    )
    _make_listing(
        db_session, giver_user,
        status="active", title="After", expires_at=now + timedelta(hours=26),
    )
    mock_post = _patch_httpx_client(mocker, status_code=200)

    picker_user.is_admin = True
    db_session.commit()
    resp = auth_client(picker_user).post("/admin/send-listing-expiring-reminders")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"sent_count": 1, "skipped_count": 0}
    assert mock_post.call_count == 1
    assert _idempotency_count(db_session, "listing_expiring", in_window.id) == 1


def test_listing_expiring_skips_inactive_listing(
    mocker, db_session, auth_client, picker_user, giver_user,
):
    _give_user_token(db_session, giver_user)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    _make_listing(
        db_session, giver_user,
        status="claimed", expires_at=expires_at,
    )
    mock_post = _patch_httpx_client(mocker, status_code=200)

    picker_user.is_admin = True
    db_session.commit()
    resp = auth_client(picker_user).post("/admin/send-listing-expiring-reminders")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"sent_count": 0, "skipped_count": 0}
    assert mock_post.call_count == 0


def test_listing_expiring_idempotent_within_day(
    mocker, db_session, auth_client, picker_user, giver_user,
):
    _give_user_token(db_session, giver_user)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    _make_listing(
        db_session, giver_user,
        status="active", expires_at=expires_at,
    )
    mock_post = _patch_httpx_client(mocker, status_code=200)

    picker_user.is_admin = True
    db_session.commit()
    first = auth_client(picker_user).post("/admin/send-listing-expiring-reminders")
    assert first.status_code == 200, first.text
    assert first.json() == {"sent_count": 1, "skipped_count": 0}
    assert mock_post.call_count == 1

    second = auth_client(picker_user).post("/admin/send-listing-expiring-reminders")
    assert second.status_code == 200, second.text
    assert second.json() == {"sent_count": 0, "skipped_count": 1}
    assert mock_post.call_count == 1

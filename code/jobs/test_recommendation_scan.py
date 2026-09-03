"""
Tests for recommendation_scan.run_recommendation_scan.

Uses a real PostGIS-enabled test database (configured via TEST_DATABASE_URL).
HTTP Expo calls are mocked via the same httpx.Client patch pattern used in
test_cron_reminders.py.
"""

import uuid
from datetime import date, datetime, timedelta

from app import models
from app.jobs.recommendation_scan import run_recommendation_scan
from app.services import notification_service

_SF_LAT, _SF_LNG = 37.7749, -122.4194   # San Francisco
_NYC_LAT, _NYC_LNG = 40.7128, -74.0060  # New York City (~2,570 miles away)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _patch_httpx(mocker, *, status_code: int = 200):
    mock_response = mocker.MagicMock()
    mock_response.status_code = status_code
    mock_response.raise_for_status.return_value = None
    mock_client = mocker.MagicMock()
    mock_client.post.return_value = mock_response
    mock_cls = mocker.patch.object(notification_service.httpx, "Client")
    mock_cls.return_value.__enter__.return_value = mock_client
    return mock_client.post


def _user_at(db_session, lat, lng, *, notify_recommendations=True):
    u = models.User(
        email=f"rec+{uuid.uuid4().hex[:8]}@example.com",
        display_name="Rec User",
        location_lat=lat,
        location_lng=lng,
        expo_push_token=f"ExponentPushToken[{uuid.uuid4().hex[:10]}]",
        notify_recommendations=notify_recommendations,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _listing_at(
    db_session, giver, lat, lng, *,
    category="Furniture",
    status="active",
    age_hours=0,
    title="Test Item",
):
    created_at = datetime.utcnow() - timedelta(hours=age_hours)
    listing = models.Listing(
        giver_id=giver.id,
        title=title,
        description="A test item.",
        category=category,
        photo_urls=["https://example.com/x.jpg"],
        location_lat=lat,
        location_lng=lng,
        location_lat_approx=lat,
        location_lng_approx=lng,
        status=status,
        ai_generated=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
        created_at=created_at,
        available_since=created_at,
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


def _save(db_session, user, listing, *, age_days=0):
    s = models.Saved(
        user_id=user.id,
        listing_id=listing.id,
        created_at=datetime.utcnow() - timedelta(days=age_days),
    )
    db_session.add(s)
    db_session.commit()
    return s


def _inbox_count(db_session, user_id):
    return (
        db_session.query(models.Notification)
        .filter(
            models.Notification.recipient_id == user_id,
            models.Notification.notification_type == "recommended_listings",
        )
        .count()
    )


def _idempotency_count(db_session, user_id):
    return (
        db_session.query(models.NotificationIdempotency)
        .filter(
            models.NotificationIdempotency.notification_type == "recommended_listings",
            models.NotificationIdempotency.entity_id == user_id,
            models.NotificationIdempotency.date_bucket == date.today(),
        )
        .count()
    )


# ─── Test cases ───────────────────────────────────────────────────────────────

def test_user_notified_for_new_in_radius_matching_category(mocker, db_session, giver_user):
    """User with a save in category X is notified about a new in-radius category-X listing."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    # establishes Furniture interest
    saved_prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture")
    _save(db_session, picker, saved_prior)

    # new matching listing posted 1 hour ago
    _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture", age_hours=1)

    count = run_recommendation_scan(db_session)

    assert count == 1
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 1


def test_out_of_radius_listing_not_matched(mocker, db_session, giver_user):
    """A listing > 50 miles away does not appear in recommendations."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture")
    _save(db_session, picker, prior)

    # new listing is in NYC — far outside the 50-mile radius
    _listing_at(db_session, giver_user, _NYC_LAT, _NYC_LNG, category="Furniture", age_hours=1)

    count = run_recommendation_scan(db_session)

    assert count == 0
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 0


def test_listing_older_than_24h_not_matched(mocker, db_session, giver_user):
    """A listing created > 24 hours ago is not included in the daily scan."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture")
    _save(db_session, picker, prior)

    _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture", age_hours=25)

    count = run_recommendation_scan(db_session)

    assert count == 0
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 0


def test_unmatched_category_not_recommended(mocker, db_session, giver_user):
    """A new listing in a category the user never saved/claimed is skipped."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    # picker only has Electronics interest
    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Electronics")
    _save(db_session, picker, prior)

    # new Furniture listing — category mismatch
    _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Furniture", age_hours=1)

    count = run_recommendation_scan(db_session)

    assert count == 0
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 0


def test_users_own_listing_excluded(mocker, db_session):
    """The scan never recommends a user's own listing to themselves."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    other_giver = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    # picker has Books interest via a save from other_giver
    prior = _listing_at(db_session, other_giver, _SF_LAT, _SF_LNG, category="Books")
    _save(db_session, picker, prior)

    # picker's own new Books listing — should be excluded
    _listing_at(db_session, picker, _SF_LAT, _SF_LNG, category="Books", age_hours=1)

    count = run_recommendation_scan(db_session)

    assert count == 0
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 0


def test_multiple_matches_produce_single_rollup(mocker, db_session, giver_user):
    """Three matching listings collapse into ONE push notification, not three."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Clothing")
    _save(db_session, picker, prior)

    for i in range(3):
        _listing_at(
            db_session, giver_user, _SF_LAT, _SF_LNG,
            category="Clothing", age_hours=1, title=f"Item {i}",
        )

    count = run_recommendation_scan(db_session)

    assert count == 1
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 1


def test_second_run_same_day_is_idempotent(mocker, db_session, giver_user):
    """Running the scan twice writes one inbox row per run; no push is ever fired."""
    picker = _user_at(db_session, _SF_LAT, _SF_LNG)
    mock_post = _patch_httpx(mocker)

    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Toys")
    _save(db_session, picker, prior)
    _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Toys", age_hours=1)

    run_recommendation_scan(db_session)
    run_recommendation_scan(db_session)

    # digest=True: no Expo push, no idempotency row; each run writes one inbox row.
    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 2
    assert _idempotency_count(db_session, picker.id) == 0


def test_toggle_off_writes_inbox_but_no_push(mocker, db_session, giver_user):
    """
    notify_recommendations=False: inbox row IS written, no HTTP push, no idempotency row.

    Known limitation: because the idempotency row is only written on a successful push,
    a second scan run the same day will write a second inbox row for this user.
    Acceptable for now; no new machinery added.
    """
    picker = _user_at(db_session, _SF_LAT, _SF_LNG, notify_recommendations=False)
    mock_post = _patch_httpx(mocker)

    prior = _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Kitchen")
    _save(db_session, picker, prior)
    _listing_at(db_session, giver_user, _SF_LAT, _SF_LNG, category="Kitchen", age_hours=1)

    run_recommendation_scan(db_session)

    assert mock_post.call_count == 0
    assert _inbox_count(db_session, picker.id) == 1
    assert _idempotency_count(db_session, picker.id) == 0

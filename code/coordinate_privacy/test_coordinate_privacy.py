import math
import uuid
from datetime import datetime, timedelta

import pytest

from app.services.coordinate_privacy import (
    _REVEAL_STATUSES,
    generate_approximate_point,
    should_reveal_true_location,
)

LAT = 47.6253
LNG = -122.3222
LID = uuid.UUID("12345678-1234-5678-1234-567812345678")
LID2 = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# --- existing unit tests ---

def test_distance_in_range():
    out_lat, out_lng = generate_approximate_point(LAT, LNG, LID)
    d = haversine(LAT, LNG, out_lat, out_lng)
    assert 119 <= d <= 251, f"distance {d:.1f}m out of range"


def test_seeded_stability():
    assert generate_approximate_point(LAT, LNG, LID) == generate_approximate_point(LAT, LNG, LID)


def test_different_ids_differ():
    assert generate_approximate_point(LAT, LNG, LID) != generate_approximate_point(LAT, LNG, LID2)


def test_output_bounds():
    out_lat, out_lng = generate_approximate_point(LAT, LNG, LID)
    assert -90.0 <= out_lat <= 90.0
    assert -180.0 < out_lng <= 180.0


# --- create_listing populates approx columns ---

def test_create_listing_populates_approx_columns(auth_client, giver_user, db_session):
    import app.models as models

    payload = {
        "title": "Privacy Test Item",
        "description": "Checking approx columns are set on create.",
        "category": "Other",
        "photo_urls": ["https://example.com/img.jpg"],
        "location_lat": LAT,
        "location_lng": LNG,
        "deadline_kind": "no_rush",
    }
    resp = auth_client(giver_user).post("/listings", json=payload)
    assert resp.status_code == 201, resp.text
    listing_id = uuid.UUID(resp.json()["id"])

    row = db_session.query(models.Listing).filter(models.Listing.id == listing_id).first()
    assert row is not None
    assert row.location_lat_approx is not None
    assert row.location_lng_approx is not None
    # approx must differ from true (deterministic offset of 120–250 m)
    assert row.location_lat_approx != row.location_lat
    assert row.location_lng_approx != row.location_lng


# --- nearby feed returns approx, not true coords ---

def test_nearby_returns_approx_not_true_coords(client, active_listing):
    resp = client.get(
        "/listings/nearby",
        params={"lat": active_listing.location_lat, "lng": active_listing.location_lng, "radius_km": 1},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 1
    item = next(i for i in items if i["id"] == str(active_listing.id))
    # Feed must return approx values
    assert item["location_lat"] == pytest.approx(active_listing.location_lat_approx, abs=1e-9)
    assert item["location_lng"] == pytest.approx(active_listing.location_lng_approx, abs=1e-9)
    # And approx differs from true
    assert item["location_lat"] != pytest.approx(active_listing.location_lat, abs=1e-9)


# --- reveal resolver: should_reveal_true_location ---

def _make_claim(db_session, listing_id, picker_id, status):
    import app.models as models

    claim = models.Claim(
        listing_id=listing_id,
        picker_id=picker_id,
        status=status,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


def test_resolver_stranger_gets_approx(db_session, active_listing, picker_user):
    result = should_reveal_true_location(
        active_listing.id, picker_user.id, active_listing.giver_id, db_session
    )
    assert result is False


def test_resolver_giver_gets_true(db_session, active_listing, giver_user):
    result = should_reveal_true_location(
        active_listing.id, giver_user.id, active_listing.giver_id, db_session
    )
    assert result is True


@pytest.mark.parametrize("reveal_status", sorted(_REVEAL_STATUSES))
def test_resolver_claim_holder_reveal_status(db_session, active_listing, picker_user, reveal_status):
    _make_claim(db_session, active_listing.id, picker_user.id, reveal_status)
    result = should_reveal_true_location(
        active_listing.id, picker_user.id, active_listing.giver_id, db_session
    )
    assert result is True


@pytest.mark.parametrize("non_reveal_status", ["pending_payment", "no_show", "cancelled"])
def test_resolver_claim_holder_non_reveal_status(
    db_session, active_listing, picker_user, non_reveal_status
):
    _make_claim(db_session, active_listing.id, picker_user.id, non_reveal_status)
    result = should_reveal_true_location(
        active_listing.id, picker_user.id, active_listing.giver_id, db_session
    )
    assert result is False

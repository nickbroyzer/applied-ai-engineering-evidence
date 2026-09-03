"""Phase 6 STEP 2 slice (b) — scam detection router-wiring integration tests.

Six listing tests (L-1 .. L-6) cover the create/get/nearby paths with the four
listing-creation rules that fire in slice (b) (rules 1, 2, 6 — rule 5 is the
deferred stub). Four message tests (M-1 .. M-4) cover the rule 3 send-block
path. The slice (a) unit tests in test_scam_detection.py remain the regression
guard for the rule engine itself.
"""
from datetime import datetime, timedelta

from sqlalchemy import text

from app import models


# ---------------------------------------------------------------------------
# Listing wiring tests
# ---------------------------------------------------------------------------

def _post_listing(client, *, title="Free couch", description="Lightly used.",
                  category="Other", lat=37.7749, lng=-122.4194,
                  ai_generated=True):
    return client.post(
        "/listings",
        json={
            "title": title,
            "description": description,
            "category": category,
            "photo_urls": ["https://example.com/1.jpg"],
            "location_lat": lat,
            "location_lng": lng,
            "ai_generated": ai_generated,
            "deadline_kind": "no_rush",
        },
    )


def _seed_nearby_listings(db_session, giver_user, count, *,
                          lat=37.7749, lng=-122.4194):
    # The DB column created_at uses server_default CURRENT_TIMESTAMP, which
    # rule 2 compares against `datetime.utcnow() - 1h`. Set created_at
    # explicitly to a UTC-naive timestamp so the comparison is timezone-clean
    # regardless of session TimeZone setting.
    now = datetime.utcnow()
    for i in range(count):
        listing = models.Listing(
            giver_id=giver_user.id,
            title=f"Prior {i}",
            description="Prior listing for GPS spam test.",
            category="Other",
            photo_urls=["https://example.com/p.jpg"],
            location_lat=lat,
            location_lng=lng,
            location_lat_approx=lat + 0.001,
            location_lng_approx=lng + 0.001,
            status="active",
            ai_generated=True,
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(listing)
    db_session.commit()


def test_create_listing_rule2_hides_and_flags(
    auth_client, giver_user, db_session, report_in_db,
):
    """L-2 — three prior listings at same lat/lng fires rule 2."""
    _seed_nearby_listings(db_session, giver_user, count=3)
    resp = auth_client(giver_user).post(
        "/listings",
        json={
            "title": "Plain item",
            "description": "Another listing here.",
            "category": "Other",
            "photo_urls": ["https://example.com/1.jpg"],
            "location_lat": 37.7749,
            "location_lng": -122.4194,
            "ai_generated": True,
            "deadline_kind": "no_rush",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["under_review"] is False
    reports = report_in_db(giver_user.id)
    assert len(reports) == 1
    assert reports[0].triggered_rule == "rule_2"


def test_create_listing_rule6_hides_and_flags(
    auth_client, giver_user, report_in_db,
):
    """L-3 — currency symbol in title fires rule 6."""
    resp = auth_client(giver_user).post(
        "/listings",
        json={
            "title": "$50 value laptop",
            "description": "Working laptop.",
            "category": "Electronics",
            "photo_urls": ["https://example.com/1.jpg"],
            "location_lat": 37.7749,
            "location_lng": -122.4194,
            "ai_generated": True,
            "deadline_kind": "no_rush",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["under_review"] is False
    reports = report_in_db(giver_user.id)
    assert len(reports) == 1
    assert reports[0].triggered_rule == "rule_6"


def test_create_listing_clean_no_flag(
    auth_client, giver_user, report_in_db,
):
    """L-5 — AI-generated, clean text, no GPS spam — no rules fire."""
    resp = auth_client(giver_user).post(
        "/listings",
        json={
            "title": "Free couch",
            "description": "Lightly used, comes with cushions.",
            "category": "Furniture",
            "photo_urls": ["https://example.com/1.jpg"],
            "location_lat": 37.7749,
            "location_lng": -122.4194,
            "ai_generated": True,
            "deadline_kind": "no_rush",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["under_review"] is False
    assert report_in_db(giver_user.id) == []


def test_flagged_listing_still_in_nearby_feed(
    auth_client, giver_user, db_session,
):
    """L-6 — a flagged listing stays visible in /listings/nearby (D265: no post-time hiding)."""
    client = auth_client(giver_user)
    resp = client.post(
        "/listings",
        json={
            "title": "$50 laptop",
            "description": "Working laptop.",
            "category": "Electronics",
            "photo_urls": ["https://example.com/1.jpg"],
            "location_lat": 37.7749,
            "location_lng": -122.4194,
            "ai_generated": True,
            "deadline_kind": "no_rush",
        },
    )
    assert resp.status_code == 201, resp.text
    listing_id = resp.json()["id"]
    assert resp.json()["status"] == "active"

    nearby = client.get(
        "/listings/nearby",
        params={"lat": 37.7749, "lng": -122.4194, "radius_km": 1.0},
    )
    assert nearby.status_code == 200, nearby.text
    ids = [item["id"] for item in nearby.json()["items"]]
    assert listing_id in ids


# ---------------------------------------------------------------------------
# Message wiring tests (rule 3)
# ---------------------------------------------------------------------------

def test_send_message_rule3_venmo_blocked_and_flagged(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """M-1 — venmo keyword in body returns 400 + writes auto-flag report."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "send me on venmo"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["message"] == "Message could not be sent. Please rephrase."
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    reports = report_in_db(picker_user.id)
    assert len(reports) == 1
    assert reports[0].source == "auto"
    assert reports[0].triggered_rule == "rule_3"


def test_send_message_rule3_phone_number_blocked_and_flagged(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """M-2 — phone-number-like body returns 400 + writes auto-flag report."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "call me at 415-555-1234"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["category"] == "phone"
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    reports = report_in_db(picker_user.id)
    assert len(reports) == 1
    assert reports[0].triggered_rule == "rule_3"


def test_send_message_rule3_phone_solicitation_blocked_category(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — phone solicitation with no digits still blocks, category 'phone'."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "what's your number?"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["category"] == "phone"
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_rule3_payment_blocked_category(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 — off-platform payment phrase blocks, category 'payment'."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "send me on venmo"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["category"] == "payment"
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_clean_content_succeeds(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """M-3 — clean body returns 201, writes Message, no Report."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "Is this still available?"},
    )
    assert resp.status_code == 201, resp.text
    db_session.expire_all()
    assert db_session.query(models.Message).count() == 1
    assert report_in_db(picker_user.id) == []


def test_send_message_rule3_email_blocked(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — email address blocked, no message persisted."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "email me at nick@example.com"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["message"] == "Message could not be sent. Please rephrase."
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    reports = report_in_db(picker_user.id)
    assert len(reports) == 1
    assert reports[0].triggered_rule == "rule_3"
    assert resp.json()["detail"]["category"] == "contact"


def test_send_message_rule3_scheduling_blocked_category(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Category mapping — scheduling-intent block returns detail.category == 'scheduling'."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "let's meet Monday at 3pm"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["message"] == "Message could not be sent. Please rephrase."
    assert resp.json()["detail"]["category"] == "scheduling"
    db_session.expire_all()
    assert db_session.query(models.Message).count() == 0


def test_send_message_rule3_handle_blocked(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — social handle blocked, message persisted self-addressed."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "add me on instagram"},
    )
    assert resp.status_code == 400, resp.text
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_bare_signal_word_not_blocked(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Bare 'signal' (no cue) does not hard-block — narrowed to avoid false positives."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "give me a signal when you're there"},
    )
    assert resp.status_code == 201, resp.text
    db_session.expire_all()
    assert db_session.query(models.Message).count() == 1
    assert report_in_db(picker_user.id) == []


def test_send_message_cued_signal_blocked_category(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — 'signal' with a contact cue still blocks, category 'contact'."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "hit me up on signal"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["category"] == "contact"
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_rule3_link_blocked(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — external link blocked, message persisted self-addressed."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "check this out https://example.com/deal"},
    )
    assert resp.status_code == 400, resp.text
    db_session.expire_all()
    messages = db_session.query(models.Message).all()
    assert len(messages) == 1
    assert messages[0].deflect_category is not None
    assert messages[0].recipient_id == messages[0].sender_id
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_rule3_scheduling_blocked(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Rule 3 extension — high-confidence scheduling proposal blocked."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "Can you do Monday morning?"},
    )
    assert resp.status_code == 400, resp.text
    db_session.expire_all()
    assert db_session.query(models.Message).count() == 0
    assert len(report_in_db(picker_user.id)) == 1


def test_send_message_tier2_address_sends_and_hints(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
    db_session,
):
    """Tier 2 — address-in-chat sends normally, no Report, response carries hint."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "I'm at 742 Evergreen Terrace"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hint"] == {"category": "address"}
    db_session.expire_all()
    assert db_session.query(models.Message).count() == 1
    assert report_in_db(picker_user.id) == []


def test_send_message_tier2_cancel_sends_and_hints(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
):
    """Tier 2 — cancel intent sends normally with a hint."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "sorry, I need to cancel"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hint"] == {"category": "cancel"}
    assert report_in_db(picker_user.id) == []


def test_send_message_tier2_confirm_sends_and_hints(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
):
    """Tier 2 — confirm intent sends normally with a hint."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "got it thanks"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hint"] == {"category": "confirm"}
    assert report_in_db(picker_user.id) == []


def test_send_message_plain_chatter_no_hint(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
):
    """Plain chatter — no Tier 1 block, no Tier 2 hint."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "Is this still available?"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["hint"] is None
    assert report_in_db(picker_user.id) == []


def test_send_message_rule3_report_fields_correct(
    auth_client, picker_user, authorized_claim, active_listing, report_in_db,
):
    """M-4 — Report row has every expected field."""
    resp = auth_client(picker_user).post(
        f"/messages/{active_listing.id}",
        json={"content": "send me on venmo"},
    )
    assert resp.status_code == 400
    reports = report_in_db(picker_user.id)
    assert len(reports) == 1
    r = reports[0]
    assert r.reported_user_id == picker_user.id
    assert r.reporter_id is None
    assert r.reason == "scam"
    assert r.source == "auto"
    assert r.triggered_rule == "rule_3"
    assert r.listing_id == active_listing.id
    assert r.description and isinstance(r.description, str)

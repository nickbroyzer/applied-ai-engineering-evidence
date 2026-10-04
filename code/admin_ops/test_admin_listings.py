"""Admin listings list — GET /admin/listings in the LISTINGS seed shape."""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app import models
from app.services import standing_notices


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


@pytest.fixture(autouse=True)
def sent_emails(monkeypatch) -> list[dict]:
    recorded: list[dict] = []

    def _fake_send_email(*, to, subject, html, text=None):
        recorded.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr(standing_notices, "send_email", _fake_send_email)
    return recorded


def test_active_listing_lists_with_zero_counts(
    auth_client, admin_user, active_listing, giver_user,
):
    resp = auth_client(admin_user).get("/admin/listings")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(active_listing.id))

    assert row["st"] == "active"
    assert row["ref"] == "L-" + str(active_listing.id)[:6].upper()
    assert row["giver"] == giver_user.display_name
    assert row["views"] == 0
    assert row["saves"] == 0
    assert row["claims"] == 0


def test_saved_and_claim_rows_are_counted(
    auth_client, admin_user, active_listing, picker_user, db_session,
):
    db_session.add(models.Saved(listing_id=active_listing.id, user_id=picker_user.id))
    db_session.add(
        models.Claim(
            listing_id=active_listing.id,
            picker_id=picker_user.id,
            status="cancelled",
        )
    )
    db_session.commit()

    resp = auth_client(admin_user).get("/admin/listings")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(active_listing.id))

    assert row["saves"] == 1
    assert row["claims"] == 1


def test_listing_expiring_within_24_hours(
    auth_client, admin_user, active_listing, db_session,
):
    active_listing.expires_at = datetime.utcnow() + timedelta(hours=1)
    db_session.commit()

    resp = auth_client(admin_user).get("/admin/listings")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(active_listing.id))

    assert row["st"] == "expiring"


def test_non_admin_is_forbidden(auth_client, other_picker_user):
    resp = auth_client(other_picker_user).get("/admin/listings")
    assert resp.status_code == 403


def test_listing_record_returns_expected_shape(
    auth_client, admin_user, active_listing,
):
    resp = auth_client(admin_user).get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 200
    row = resp.json()

    assert row["ref"] == "L-" + str(active_listing.id)[:6].upper()
    assert isinstance(row["photos"], list)
    assert row["description"] == active_listing.description
    assert row["lat"] == active_listing.location_lat
    assert row["lng"] == active_listing.location_lng
    assert isinstance(row["claims"], list)
    assert isinstance(row["flags"], list)
    assert isinstance(row["messages"], int)
    assert isinstance(row["category_avg_views"], int)


def test_listing_record_reports_live_claim_ref(
    auth_client, admin_user, active_listing, picker_user, db_session,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    resp = auth_client(admin_user).get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 200
    row = resp.json()

    assert row["live_claim_ref"] == "ZLB-" + str(claim.id)[:6].upper()


def test_listing_record_includes_auto_flag(
    auth_client, admin_user, active_listing, db_session,
):
    db_session.add(
        models.Report(
            reported_user_id=active_listing.giver_id,
            listing_id=active_listing.id,
            reason="scam",
            source="auto",
            triggered_rule="rule_stock_photo",
        )
    )
    db_session.commit()

    resp = auth_client(admin_user).get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 200
    row = resp.json()

    assert len(row["flags"]) == 1
    assert row["flags"][0]["rule"] == "rule_stock_photo"


def test_listing_record_flag_carries_rule_label(
    auth_client, admin_user, active_listing, db_session,
):
    db_session.add(
        models.Report(
            reported_user_id=active_listing.giver_id,
            listing_id=active_listing.id,
            reason="scam",
            source="auto",
            triggered_rule="rule_stock_photo",
        )
    )
    db_session.commit()

    resp = auth_client(admin_user).get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 200
    row = resp.json()

    assert row["flags"][0]["rule_label"] == "rule_stock_photo"


def test_listing_record_unknown_id_404s(auth_client, admin_user):
    resp = auth_client(admin_user).get(f"/admin/listings/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_listing_record_non_admin_is_forbidden(auth_client, other_picker_user, active_listing):
    resp = auth_client(other_picker_user).get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 403


def _listing_actions(db_session, action):
    return (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.action == action)
        .all()
    )


def test_test_tag_sets_flag_and_records(auth_client, admin_user, active_listing, db_session):
    client = auth_client(admin_user)

    resp = client.post(f"/admin/listings/{active_listing.id}/test", json={"is_test": True})
    assert resp.status_code == 200, resp.text
    assert resp.json()["test"] is True

    row = next(r for r in client.get("/admin/listings").json() if r["id"] == str(active_listing.id))
    assert row["test"] is True

    actions = _listing_actions(db_session, "listing_test")
    assert len(actions) == 1
    assert actions[0].details["listing_id"] == str(active_listing.id)


def test_test_tag_can_be_removed(auth_client, admin_user, active_listing, db_session):
    client = auth_client(admin_user)
    assert client.post(f"/admin/listings/{active_listing.id}/test", json={"is_test": True}).status_code == 200

    resp = client.post(f"/admin/listings/{active_listing.id}/test", json={"is_test": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["test"] is False
    assert len(_listing_actions(db_session, "listing_test")) == 2


def test_deactivate_removes_and_emails_giver(
    auth_client, admin_user, active_listing, giver_user, db_session, sent_emails,
):
    client = auth_client(admin_user)

    resp = client.post(
        f"/admin/listings/{active_listing.id}/deactivate",
        json={"reason": "Selling a free item for cash."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "removed"

    db_session.expire_all()
    assert db_session.get(models.Listing, active_listing.id).status == "removed"

    row = next(r for r in client.get("/admin/listings").json() if r["id"] == str(active_listing.id))
    assert row["st"] == "deactivated"

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == giver_user.email
    assert sent_emails[0]["subject"] == f"Listing removed · {active_listing.title}"
    assert sent_emails[0]["text"].startswith(f"Listing removed\n\nHi User,\n\nItem: {active_listing.title}\n\nSelling a free item for cash.")
    assert "Reference L-" in sent_emails[0]["text"]

    assert len(_listing_actions(db_session, "listing_deactivate")) == 1


def test_deactivate_claimed_listing_is_409(
    auth_client, admin_user, active_listing, db_session, sent_emails,
):
    db_session.execute(
        text("UPDATE listings SET status='claimed' WHERE id=:lid"), {"lid": active_listing.id},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(admin_user).post(
        f"/admin/listings/{active_listing.id}/deactivate", json={"reason": "Test"},
    )
    assert resp.status_code == 409
    assert sent_emails == []

    db_session.expire_all()
    assert db_session.get(models.Listing, active_listing.id).status == "claimed"


def test_deactivate_blank_reason_is_422(auth_client, admin_user, active_listing):
    resp = auth_client(admin_user).post(
        f"/admin/listings/{active_listing.id}/deactivate", json={"reason": "   "},
    )
    assert resp.status_code == 422


def test_listing_actions_non_admin_forbidden(auth_client, picker_user, active_listing):
    client = auth_client(picker_user)
    assert client.post(f"/admin/listings/{active_listing.id}/test", json={"is_test": True}).status_code == 403
    assert client.post(
        f"/admin/listings/{active_listing.id}/deactivate", json={"reason": "Test"},
    ).status_code == 403

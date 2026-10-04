"""Phase 9-1 D65 + D67 — Admin dispute respond/resolve endpoints."""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app import models
from app.services import standing_notices


_REASON = "z" * 100


@pytest.fixture(autouse=True)
def sent_emails(monkeypatch) -> list[dict]:
    recorded: list[dict] = []

    def _fake_send_email(*, to, subject, html, text=None):
        recorded.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr(standing_notices, "send_email", _fake_send_email)
    return recorded


def _file_dispute(db_session, claim, picker, *, status="pending"):
    dispute = models.Dispute(
        claim_id=claim.id,
        filer_user_id=picker.id,
        reason_text=_REASON,
        acknowledged=True,
        status=status,
    )
    db_session.add(dispute)
    db_session.commit()
    db_session.refresh(dispute)
    return dispute


def test_respond_pending_dispute_marks_responded(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(f"/admin/disputes/{dispute.id}/respond")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "responded"
    db_session.expire_all()
    fresh = db_session.get(models.Dispute, dispute.id)
    assert fresh.responded_at is not None


def test_respond_on_non_pending_returns_409(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user, status="responded")
    resp = auth_client(giver_user).post(f"/admin/disputes/{dispute.id}/respond")
    assert resp.status_code == 409


def test_respond_unknown_returns_404(auth_client, db_session, giver_user):
    giver_user.is_admin = True
    db_session.commit()
    resp = auth_client(giver_user).post(f"/admin/disputes/{uuid.uuid4()}/respond")
    assert resp.status_code == 404


def test_resolve_upheld_picker_writes_dispute_lost_giver_event(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
    trust_events_for, active_listing,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "upheld_picker"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolution"] == "upheld_picker"

    # Trust event written for the giver
    events = trust_events_for(giver_user.id, "dispute_lost_giver")
    assert len(events) == 1


def test_resolve_upheld_giver_writes_dispute_lost_picker_event(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
    trust_events_for,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "upheld_giver"},
    )
    assert resp.status_code == 200, resp.text
    events = trust_events_for(picker_user.id, "dispute_lost_picker")
    assert len(events) == 1


def test_resolve_dismissed_writes_no_trust_event(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
    trust_events_for,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "dismissed"},
    )
    assert resp.status_code == 200, resp.text

    picker_events = trust_events_for(picker_user.id, "dispute_lost_picker")
    giver_events = trust_events_for(giver_user.id, "dispute_lost_giver")
    assert picker_events == []
    assert giver_events == []


def test_resolve_already_resolved_returns_409(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user, status="resolved")
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "dismissed"},
    )
    assert resp.status_code == 409


def test_resolve_invalid_resolution_returns_422(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "bogus_value"},
    )
    assert resp.status_code == 422


def test_resolve_unknown_returns_404(auth_client, db_session, giver_user):
    giver_user.is_admin = True
    db_session.commit()
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{uuid.uuid4()}/resolve",
        json={"resolution": "dismissed"},
    )
    assert resp.status_code == 404


def test_upheld_picker_refunds_captured_claim(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
    mocker,
):
    """Nick 2026-08-11, superseding D61: an upheld picker's captured fee is refunded
    by the resolution itself, not by dashboard hand-work."""
    giver_user.is_admin = True
    db_session.execute(
        text("UPDATE claims SET captured_at=:t WHERE id=:cid"),
        {"cid": authorized_claim.id, "t": datetime.utcnow()},
    )
    db_session.commit()
    # Raw SQL bypasses the identity map and expire_on_commit is False, so the
    # loaded Claim keeps a stale captured_at without this — same convention as
    # the authorized_claim fixture's own raw update.
    db_session.expire_all()

    refund = mocker.MagicMock()
    refund.id = "re_test_refund_1"
    refund_create = mocker.patch(
        "app.services.stripe_service.stripe.Refund.create",
        return_value=refund,
    )

    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "upheld_picker"},
    )
    assert resp.status_code == 200, resp.text

    assert refund_create.call_count == 1
    _, kwargs = refund_create.call_args
    assert kwargs["idempotency_key"] == f"refund_claim_{authorized_claim.id}"

    db_session.expire_all()
    fresh = db_session.get(models.Claim, authorized_claim.id)
    assert fresh.refund_id == "re_test_refund_1"
    assert fresh.refunded_at is not None


def test_upheld_picker_without_capture_resolves_without_refund(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
    mocker,
):
    """A claim whose hold was never captured has nothing to return — the resolution
    proceeds and Stripe's refund API is never called."""
    giver_user.is_admin = True
    db_session.commit()

    refund_create = mocker.patch(
        "app.services.stripe_service.stripe.Refund.create",
    )

    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "upheld_picker"},
    )
    assert resp.status_code == 200, resp.text
    refund_create.assert_not_called()


def test_list_disputes_shows_claim_ref_and_party(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)

    resp = auth_client(giver_user).get("/admin/disputes")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(dispute.id))

    assert row["ref"] == "ZLB-" + str(authorized_claim.id)[:6].upper()
    assert row["party"] == "Picker"
    assert row["at"] is not None
    assert row["responded"] is None


def test_list_disputes_non_admin_is_forbidden(auth_client, giver_user):
    resp = auth_client(giver_user).get("/admin/disputes")
    assert resp.status_code == 403


def test_resolve_with_body_emails_filer_and_records_action(
    auth_client, db_session, picker_user, giver_user, authorized_claim, sent_emails,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={
            "resolution": "dismissed",
            "note": "no evidence of no-show",
            "subject": "Custom subject line",
            "body": "First paragraph.\n\nSecond paragraph.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["notice_sent"] is True

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == picker_user.email
    assert sent_emails[0]["subject"] == "Custom subject line"
    assert "Reference ZLB-" + str(authorized_claim.id)[:6].upper() in sent_emails[0]["html"]

    action = (
        db_session.query(models.AdminAction)
        .filter_by(subject_user_id=picker_user.id, action="dispute_decision")
        .one()
    )
    assert action.notice_sent is True
    assert action.reason == "dismissed · no evidence of no-show"


def test_resolve_without_body_sends_structured_email(
    auth_client, db_session, picker_user, giver_user, authorized_claim, sent_emails,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "dismissed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["notice_sent"] is True

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == picker_user.email
    assert f"Item: {authorized_claim.listing.title}" in sent_emails[0]["html"]
    assert "Decision: Dismissed — nothing changes, the $2.00 fee stands." in sent_emails[0]["html"]

    action = (
        db_session.query(models.AdminAction)
        .filter_by(subject_user_id=picker_user.id, action="dispute_decision")
        .one_or_none()
    )
    assert action is not None


def test_message_both_sends_two_emails_and_records_two_rows(
    auth_client, db_session, picker_user, giver_user, authorized_claim, sent_emails,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/message",
        json={
            "to": "both",
            "subject": "A quick update",
            "heading": "An update on your dispute",
            "body": "Hi there.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] == 2

    assert len(sent_emails) == 2
    recipients = {email["to"] for email in sent_emails}
    assert recipients == {picker_user.email, giver_user.email}
    assert all("An update on your dispute" in email["html"] for email in sent_emails)

    actions = (
        db_session.query(models.AdminAction)
        .filter_by(action="dispute_email")
        .all()
    )
    assert len(actions) == 2


def test_message_on_pending_dispute_marks_responded(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    giver_user.is_admin = True
    db_session.commit()
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    assert dispute.status == "pending"
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/message",
        json={"to": "filer", "subject": "Update", "body": "Hi."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "responded"
    assert body["responded_at"] is not None

    db_session.expire_all()
    fresh = db_session.get(models.Dispute, dispute.id)
    assert fresh.status == "responded"
    assert fresh.responded_at is not None


def test_message_unknown_dispute_returns_404(auth_client, db_session, giver_user):
    giver_user.is_admin = True
    db_session.commit()
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{uuid.uuid4()}/message",
        json={"to": "filer", "subject": "Update", "body": "Hi."},
    )
    assert resp.status_code == 404


def test_message_non_admin_is_forbidden(
    auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    dispute = _file_dispute(db_session, authorized_claim, picker_user)
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/message",
        json={"to": "filer", "subject": "Update", "body": "Hi."},
    )
    assert resp.status_code == 403

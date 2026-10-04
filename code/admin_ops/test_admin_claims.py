"""Admin claims list — GET /admin/claims in the CLAIMS seed shape."""
import uuid

import pytest
from sqlalchemy import text

from app import models


_REASON = "z" * 100


def _file_dispute(db_session, claim, filer):
    dispute = models.Dispute(
        claim_id=claim.id,
        filer_user_id=filer.id,
        reason_text=_REASON,
        acknowledged=True,
    )
    db_session.add(dispute)
    db_session.commit()
    db_session.refresh(dispute)
    return dispute


def _seed_message(db_session, *, sender, recipient, listing, content="Hello"):
    msg = models.Message(
        listing_id=listing.id,
        sender_id=sender.id,
        recipient_id=recipient.id,
        content=content,
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


def test_completed_claim_with_photo_lists_as_done_photo(
    auth_client, admin_user, pickup_scheduled_claim, active_listing, db_session,
):
    db_session.execute(
        text(
            "UPDATE claims SET status='completed', completed_at=timezone('utc', now()), "
            "captured_at=timezone('utc', now()), completion_photo_url=:url WHERE id=:cid"
        ),
        {"url": "https://img.example/completions/done.jpg", "cid": pickup_scheduled_claim.id},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(admin_user).get("/admin/claims")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(pickup_scheduled_claim.id))

    assert row["st"] == "done"
    assert row["how"] == "photo"
    assert row["item"] == active_listing.title
    assert row["ref"] == "ZLB-" + str(pickup_scheduled_claim.id)[:6].upper()

    timeline = row["timeline"]
    assert timeline[0]["title"] == "Claim placed"
    assert timeline[-1]["title"] == "Completed · pickup photo taken"
    assert timeline[-1]["note"] == "$2.00 captured"


def _spent_credit(db_session, user, claim) -> models.Credit:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id, kind="giveaway", earned_at=now, expires_at=now + timedelta(days=90),
        used_at=now, used_claim_id=claim.id,
    )
    db_session.add(credit)
    db_session.commit()
    db_session.refresh(credit)
    return credit


@pytest.mark.parametrize(
    "status, stamp, title",
    [
        ("completed", "completed_at", "Completed · confirmed by the giver"),
        ("no_show", "no_show_at", "Marked no-show by the giver"),
        ("auto_captured", "auto_captured_at", "Captured by the sweeper · pickup window passed"),
    ],
)
def test_released_claim_timeline_note_reads_credit_used(
    auth_client, admin_user, pickup_scheduled_claim, picker_user, db_session, status, stamp, title,
):
    """D548: a closed claim with credit_id set and captured_at null spent its credit and
    the hold was released; the timeline note says so instead of "$2.00 captured"."""
    credit = _spent_credit(db_session, picker_user, pickup_scheduled_claim)
    db_session.execute(
        text(
            f"UPDATE claims SET status=:status, {stamp}=timezone('utc', now()), credit_id=:c "
            "WHERE id=:cid"
        ),
        {"status": status, "c": credit.id, "cid": pickup_scheduled_claim.id},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(admin_user).get("/admin/claims")
    assert resp.status_code == 200
    row = next(r for r in resp.json() if r["id"] == str(pickup_scheduled_claim.id))
    entry = next(e for e in row["timeline"] if e["title"] == title)
    assert entry["note"] == "credit used · hold released"


def test_uncovered_no_show_on_lapsed_hold_timeline_note_reads_no_fee(
    auth_client, admin_user, pickup_scheduled_claim, db_session,
):
    """D548: no captured_at and no credit means nothing was taken."""
    db_session.execute(
        text("UPDATE claims SET status='no_show', no_show_at=timezone('utc', now()) WHERE id=:cid"),
        {"cid": pickup_scheduled_claim.id},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(admin_user).get("/admin/claims")
    assert resp.status_code == 200
    row = next(r for r in resp.json() if r["id"] == str(pickup_scheduled_claim.id))
    entry = next(e for e in row["timeline"] if e["title"] == "Marked no-show by the giver")
    assert entry["note"] == "no fee captured"


def test_authorized_claim_lists_as_live_with_no_how(
    auth_client, admin_user, authorized_claim,
):
    resp = auth_client(admin_user).get("/admin/claims")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(authorized_claim.id))

    assert row["st"] == "live"
    assert row["how"] == ""

    timeline = row["timeline"]
    assert timeline[-1]["title"] == "Waiting for the appointment"


def test_pending_payment_claim_is_absent(
    auth_client, admin_user, pending_payment_claim, picker_user, active_listing, db_session,
):
    abandoned_cancelled_claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="cancelled",
        authorized_at=None,
    )
    held_then_cancelled_claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="cancelled",
    )
    db_session.add_all([abandoned_cancelled_claim, held_then_cancelled_claim])
    db_session.commit()
    db_session.execute(
        text("UPDATE claims SET authorized_at=timezone('utc', now()) WHERE id=:cid"),
        {"cid": held_then_cancelled_claim.id},
    )
    db_session.commit()
    db_session.refresh(held_then_cancelled_claim)

    resp = auth_client(admin_user).get("/admin/claims")
    assert resp.status_code == 200
    rows = resp.json()
    ids = [r["id"] for r in rows]

    assert str(pending_payment_claim.id) not in ids
    assert str(abandoned_cancelled_claim.id) not in ids

    held_row = next(r for r in rows if r["id"] == str(held_then_cancelled_claim.id))
    assert held_row["st"] == "rel"


def test_non_admin_is_forbidden(auth_client, other_picker_user):
    resp = auth_client(other_picker_user).get("/admin/claims")
    assert resp.status_code == 403


def test_claim_record_for_authorized_claim(
    auth_client, admin_user, authorized_claim,
):
    resp = auth_client(admin_user).get(f"/admin/claims/{authorized_claim.id}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["ref"] == "ZLB-" + str(authorized_claim.id)[:6].upper()
    assert body["item"]
    assert isinstance(body["photos"], list)
    assert isinstance(body["messages"], list)
    assert body["dispute"] is None
    assert body["notes"] == []


def test_claim_record_with_picker_dispute(
    auth_client, admin_user, authorized_claim, picker_user, db_session,
):
    dispute = _file_dispute(db_session, authorized_claim, picker_user)

    resp = auth_client(admin_user).get(f"/admin/claims/{authorized_claim.id}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["dispute"]["id"] == str(dispute.id)
    assert body["dispute"]["party"] == "Picker"
    assert body["dispute"]["reason"] == _REASON


def test_claim_record_lists_messages_with_sender_name_oldest_first(
    auth_client, admin_user, authorized_claim, active_listing, picker_user, giver_user, db_session,
):
    first = _seed_message(
        db_session, sender=picker_user, recipient=giver_user, listing=active_listing, content="Is this still here?",
    )
    _seed_message(
        db_session, sender=giver_user, recipient=picker_user, listing=active_listing, content="Yep!",
    )

    resp = auth_client(admin_user).get(f"/admin/claims/{authorized_claim.id}")
    assert resp.status_code == 200
    body = resp.json()

    messages = body["messages"]
    assert len(messages) == 2
    assert messages[0]["id"] == str(first.id)
    assert messages[0]["sender"] == picker_user.display_name
    assert messages[0]["text"] == "Is this still here?"
    assert messages[1]["sender"] == giver_user.display_name


def test_claim_record_unknown_id_is_404(auth_client, admin_user):
    resp = auth_client(admin_user).get(f"/admin/claims/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_claim_record_non_admin_is_forbidden(auth_client, other_picker_user, authorized_claim):
    resp = auth_client(other_picker_user).get(f"/admin/claims/{authorized_claim.id}")
    assert resp.status_code == 403

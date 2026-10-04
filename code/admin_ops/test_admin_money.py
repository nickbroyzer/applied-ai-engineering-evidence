"""Admin money list — GET /admin/money in the seed shape."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app import models


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


def test_pending_payment_claim_appears_with_ref_and_item(
    auth_client, admin_user, pending_payment_claim, active_listing,
):
    resp = auth_client(admin_user).get("/admin/money")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    row = next(r for r in rows if r["claim_id"] == str(pending_payment_claim.id))

    assert row["ref"] == "ZLB-" + str(pending_payment_claim.id)[:6].upper()
    assert row["item"] == active_listing.title


def test_claim_in_other_status_is_absent(
    auth_client, admin_user, authorized_claim,
):
    resp = auth_client(admin_user).get("/admin/money")
    assert resp.status_code == 200
    ids = [r["claim_id"] for r in resp.json()]
    assert str(authorized_claim.id) not in ids


def test_kind_is_five_for_a_claim_just_created(
    auth_client, admin_user, pending_payment_claim, db_session,
):
    # claimed_at comes from the claims table's CURRENT_TIMESTAMP server default,
    # which Postgres localizes to the session TimeZone rather than true UTC
    # (see backend/lessons.md 2026-06-30). Rebind it to real UTC "now" so this
    # test doesn't depend on the test DB's session TimeZone offset.
    db_session.execute(
        text("UPDATE claims SET claimed_at = (now() AT TIME ZONE 'utc') WHERE id=:cid"),
        {"cid": pending_payment_claim.id},
    )
    db_session.commit()
    db_session.expire_all()

    resp = auth_client(admin_user).get("/admin/money")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["claim_id"] == str(pending_payment_claim.id))

    assert row["kind"] == "five"


def test_non_admin_is_forbidden(auth_client, picker_user):
    resp = auth_client(picker_user).get("/admin/money")
    assert resp.status_code == 403


_RETRIEVE = "app.services.stripe_service.stripe.PaymentIntent.retrieve"


def _real_shaped_pi_id() -> str:
    """A 24+ char id, so is_synthetic_payment_intent_id treats it as possibly-live."""
    return f"pi_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


def _stripe_intent(pi_id: str, *, status: str, amount_capturable: int):
    """A real Stripe object: the webhook handler pulls the id out with a dict lookup."""
    import stripe as _stripe
    return _stripe.PaymentIntent.construct_from(
        {
            "id": pi_id,
            "status": status,
            "amount_capturable": amount_capturable,
        },
        "sk_test",
    )


def _set_claim(db_session, claim_id, *, pi_id=None, claimed_at=None):
    if pi_id is not None:
        db_session.execute(
            text("UPDATE claims SET stripe_payment_intent_id=:pid WHERE id=:cid"),
            {"cid": claim_id, "pid": pi_id},
        )
    if claimed_at is not None:
        db_session.execute(
            text("UPDATE claims SET claimed_at=:t WHERE id=:cid"),
            {"cid": claim_id, "t": claimed_at},
        )
    db_session.commit()
    db_session.expire_all()


def test_requires_capture_reads_as_webhook_missing(
    auth_client, admin_user, pending_payment_claim, db_session, mocker,
):
    pi_id = _real_shaped_pi_id()
    _set_claim(db_session, pending_payment_claim.id, pi_id=pi_id)
    mocker.patch(_RETRIEVE, return_value=_stripe_intent(pi_id, status="requires_capture", amount_capturable=200))

    resp = auth_client(admin_user).get("/admin/money")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["claim_id"] == str(pending_payment_claim.id))

    assert row["stripe"] == "requires_capture"
    assert row["kind"] == "webhook"
    assert row["payment_intent"] == pi_id


def test_resync_live_hold_promotes_and_records(
    auth_client, admin_user, pending_payment_claim, db_session, mocker,
):
    pi_id = _real_shaped_pi_id()
    _set_claim(db_session, pending_payment_claim.id, pi_id=pi_id)
    mocker.patch(_RETRIEVE, return_value=_stripe_intent(pi_id, status="requires_capture", amount_capturable=200))

    resp = auth_client(admin_user).post(f"/admin/money/{pending_payment_claim.id}/resync", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["before"] == "pending_payment"
    assert body["after"] == "authorized"

    db_session.expire_all()
    assert db_session.get(models.Claim, pending_payment_claim.id).status == "authorized"

    actions = db_session.query(models.AdminAction).filter(models.AdminAction.action == "money_resync").all()
    assert len(actions) == 1
    assert actions[0].details["stripe"] == "requires_capture"


def test_resync_canceled_cancels_and_relists(
    auth_client, admin_user, pending_payment_claim, active_listing, db_session, mocker,
):
    pi_id = _real_shaped_pi_id()
    db_session.execute(text("UPDATE listings SET status='claimed' WHERE id=:lid"), {"lid": active_listing.id})
    _set_claim(db_session, pending_payment_claim.id, pi_id=pi_id)
    mocker.patch(_RETRIEVE, return_value=_stripe_intent(pi_id, status="canceled", amount_capturable=0))

    resp = auth_client(admin_user).post(f"/admin/money/{pending_payment_claim.id}/resync", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["after"] == "cancelled"

    db_session.expire_all()
    assert db_session.get(models.Claim, pending_payment_claim.id).status == "cancelled"
    assert db_session.get(models.Listing, active_listing.id).status == "active"


def test_resync_other_status_is_409(
    auth_client, admin_user, pending_payment_claim, db_session, mocker,
):
    pi_id = _real_shaped_pi_id()
    _set_claim(db_session, pending_payment_claim.id, pi_id=pi_id)
    mocker.patch(_RETRIEVE, return_value=_stripe_intent(pi_id, status="requires_payment_method", amount_capturable=0))

    resp = auth_client(admin_user).post(f"/admin/money/{pending_payment_claim.id}/resync", json={})
    assert resp.status_code == 409

    db_session.expire_all()
    assert db_session.get(models.Claim, pending_payment_claim.id).status == "pending_payment"


def test_resync_not_pending_is_409(auth_client, admin_user, authorized_claim):
    resp = auth_client(admin_user).post(f"/admin/money/{authorized_claim.id}/resync", json={})
    assert resp.status_code == 409


def test_sweep_old_claim_cancels_and_records(
    auth_client, admin_user, pending_payment_claim, db_session, mock_stripe_pi_cancel,
):
    _set_claim(db_session, pending_payment_claim.id, claimed_at=datetime.utcnow() - timedelta(minutes=6))

    resp = auth_client(admin_user).post(f"/admin/money/{pending_payment_claim.id}/sweep", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["outcome"] == "cancelled"

    db_session.expire_all()
    assert db_session.get(models.Claim, pending_payment_claim.id).status == "cancelled"
    actions = db_session.query(models.AdminAction).filter(models.AdminAction.action == "money_sweep").all()
    assert len(actions) == 1


def test_sweep_young_claim_is_409(
    auth_client, admin_user, pending_payment_claim, db_session, mock_stripe_pi_cancel,
):
    _set_claim(db_session, pending_payment_claim.id, claimed_at=datetime.utcnow() - timedelta(minutes=1))

    resp = auth_client(admin_user).post(f"/admin/money/{pending_payment_claim.id}/sweep", json={})
    assert resp.status_code == 409

    db_session.expire_all()
    assert db_session.get(models.Claim, pending_payment_claim.id).status == "pending_payment"


def test_money_fix_routes_non_admin_forbidden(auth_client, picker_user, pending_payment_claim):
    client = auth_client(picker_user)
    assert client.post(f"/admin/money/{pending_payment_claim.id}/resync", json={}).status_code == 403
    assert client.post(f"/admin/money/{pending_payment_claim.id}/sweep", json={}).status_code == 403


def test_sweep_reads_latest_pending_sweeper_run(
    auth_client, admin_user, pending_payment_claim, db_session,
):
    earlier = datetime.now(timezone.utc) - timedelta(minutes=20)
    later = datetime.now(timezone.utc) - timedelta(minutes=10)
    for started in (earlier, later):
        db_session.add(
            models.JobRun(
                job="pending_payment_sweeper",
                started_at=started,
                finished_at=started + timedelta(seconds=1),
                result="ok",
            )
        )
    db_session.commit()

    resp = auth_client(admin_user).get("/admin/money")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["claim_id"] == str(pending_payment_claim.id))

    assert datetime.fromisoformat(row["sweep"]) == later

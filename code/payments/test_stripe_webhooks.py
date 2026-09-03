"""Phase 4a layer 6d test suite — Stripe webhook handler + listing-status-sync (T-LS-1)."""
import logging
import uuid
from datetime import datetime, timedelta

import pytest
import stripe
from sqlalchemy import text

from app import models
from app.config import settings


def _amount_capturable_event(pi_id: str) -> dict:
    return {
        "type": "payment_intent.amount_capturable_updated",
        "data": {"object": {"id": pi_id}},
    }


def _canceled_event(pi_id: str) -> dict:
    return {
        "type": "payment_intent.canceled",
        "data": {"object": {"id": pi_id}},
    }


def _payment_failed_event(pi_id: str, code: str, decline_code: str) -> dict:
    return {
        "type": "payment_intent.payment_failed",
        "data": {
            "object": {
                "id": pi_id,
                "last_payment_error": {
                    "code": code,
                    "decline_code": decline_code,
                    "message": "Card was declined.",
                },
            }
        },
    }


def test_webhook_400_when_signature_header_missing(client):
    resp = client.post("/webhooks/stripe", content=b"{}")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing Stripe-Signature header"


def test_webhook_400_when_secret_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=fake"},
        content=b"{}",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Webhook not configured"


def test_webhook_400_when_payload_invalid(client, stripe_construct_event):
    stripe_construct_event.side_effect = ValueError("bad payload")
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=fake"},
        content=b"not-json",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid payload"


def test_webhook_400_when_signature_invalid(client, stripe_construct_event):
    stripe_construct_event.side_effect = stripe.error.SignatureVerificationError(
        "bad sig", "t=1,v1=bad"
    )
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=bad"},
        content=b"{}",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid signature"


def test_webhook_unhandled_event_type_returns_200(client, stripe_construct_event):
    stripe_construct_event.return_value = {
        "type": "customer.created",
        "data": {"object": {"id": "cus_test_123"}},
    }
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    assert resp.json() == {"received": True}


def test_TLS_1_amount_capturable_updated_authorizes_claim_and_marks_listing_claimed(
    client, stripe_construct_event, pending_payment_claim, active_listing,
    claim_in_db, listing_in_db,
):
    """T-LS-1 — primary authorize webhook flips claim → authorized and listing → claimed."""
    pi_id = pending_payment_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _amount_capturable_event(pi_id)
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    claim = claim_in_db(pending_payment_claim.id)
    assert claim.status == "authorized"
    assert claim.authorized_at is not None
    listing = listing_in_db(active_listing.id)
    assert listing.status == "claimed"


def test_amount_capturable_updated_idempotent_when_already_authorized(
    client, stripe_construct_event, authorized_claim, active_listing,
    claim_in_db, listing_in_db,
):
    """Webhook idempotency — replay does not thrash claim or listing."""
    pi_id = authorized_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _amount_capturable_event(pi_id)
    first_authorized_at = authorized_claim.authorized_at

    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "authorized"
    assert claim.authorized_at == first_authorized_at
    listing = listing_in_db(active_listing.id)
    assert listing.status == "claimed"


def test_amount_capturable_updated_unknown_pi_id_no_writes(
    client, stripe_construct_event, db_session,
):
    stripe_construct_event.return_value = _amount_capturable_event("pi_test_unknown")
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    db_session.expire_all()
    assert db_session.query(models.Claim).count() == 0


def test_amount_capturable_updated_missing_pi_id_in_payload_no_writes(
    client, stripe_construct_event, pending_payment_claim, listing_in_db,
    active_listing, claim_in_db,
):
    stripe_construct_event.return_value = {
        "type": "payment_intent.amount_capturable_updated",
        "data": {"object": {}},
    }
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    claim = claim_in_db(pending_payment_claim.id)
    assert claim.status == "pending_payment"
    listing = listing_in_db(active_listing.id)
    assert listing.status == "active"


def test_payment_intent_canceled_logs_only_no_state_change(
    client, stripe_construct_event, authorized_claim, db_session,
    claim_in_db, active_listing, listing_in_db,
):
    """Move claim to cancelled first, then fire canceled webhook → no state change."""
    db_session.execute(
        text("UPDATE claims SET status='cancelled' WHERE id=:cid"),
        {"cid": authorized_claim.id},
    )
    db_session.execute(
        text("UPDATE listings SET status='active' WHERE id=:lid"),
        {"lid": active_listing.id},
    )
    db_session.commit()
    pi_id = authorized_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _canceled_event(pi_id)

    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "cancelled"
    listing = listing_in_db(active_listing.id)
    assert listing.status == "active"


def test_D62_alarm_fires_when_canceled_arrives_after_window(
    client, stripe_construct_event, authorized_claim, db_session,
    claim_in_db, mocker,
):
    """D62 + D70 — claim still authorized when Stripe auto-voids past T+24h.

    Flips claim to cancelled and emits the dedicated alarm event name.
    """
    db_session.execute(
        text(
            "UPDATE claims SET pickup_scheduled_at = (timezone('utc', now()) - "
            "INTERVAL '25 hours') WHERE id=:cid"
        ),
        {"cid": authorized_claim.id},
    )
    db_session.commit()
    pi_id = authorized_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _canceled_event(pi_id)

    error_spy = mocker.spy(
        __import__("app.routers.stripe_webhooks", fromlist=["logger"]).logger,
        "error",
    )

    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )

    assert resp.status_code == 200
    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "cancelled"

    error_payloads = [
        call.args[0] for call in error_spy.call_args_list if call.args
    ]
    assert any(
        "stripe_autovoid_after_window" in p for p in error_payloads
    ), f"expected alarm event in error logs; got: {error_payloads}"


def test_D62_no_alarm_when_canceled_arrives_inside_window(
    client, stripe_construct_event, authorized_claim, db_session,
    claim_in_db, mocker,
):
    """Cancel webhook arriving while still inside the 24h window does not flip claim."""
    db_session.execute(
        text(
            "UPDATE claims SET pickup_scheduled_at = (timezone('utc', now()) - "
            "INTERVAL '23 hours') WHERE id=:cid"
        ),
        {"cid": authorized_claim.id},
    )
    db_session.commit()
    pi_id = authorized_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _canceled_event(pi_id)

    error_spy = mocker.spy(
        __import__("app.routers.stripe_webhooks", fromlist=["logger"]).logger,
        "error",
    )

    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )

    assert resp.status_code == 200
    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "authorized"

    error_payloads = [
        call.args[0] for call in error_spy.call_args_list if call.args
    ]
    assert not any(
        "stripe_autovoid_after_window" in p for p in error_payloads
    )


def test_D62_no_alarm_when_already_cancelled(
    client, stripe_construct_event, authorized_claim, db_session,
    claim_in_db, mocker,
):
    """Backend-initiated cancel path: claim already cancelled before webhook → no alarm."""
    db_session.execute(
        text(
            "UPDATE claims SET status='cancelled', pickup_scheduled_at = "
            "(timezone('utc', now()) - INTERVAL '25 hours') WHERE id=:cid"
        ),
        {"cid": authorized_claim.id},
    )
    db_session.commit()
    pi_id = authorized_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _canceled_event(pi_id)

    error_spy = mocker.spy(
        __import__("app.routers.stripe_webhooks", fromlist=["logger"]).logger,
        "error",
    )

    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )

    assert resp.status_code == 200
    claim = claim_in_db(authorized_claim.id)
    assert claim.status == "cancelled"

    error_payloads = [
        call.args[0] for call in error_spy.call_args_list if call.args
    ]
    assert not any(
        "stripe_autovoid_after_window" in p for p in error_payloads
    )


def test_payment_intent_payment_failed_logs_warning_returns_200(
    client, stripe_construct_event, pending_payment_claim, claim_in_db,
):
    pi_id = pending_payment_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _payment_failed_event(
        pi_id, "card_declined", "generic_decline",
    )
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    claim = claim_in_db(pending_payment_claim.id)
    assert claim.status == "pending_payment"


def test_payment_intent_payment_failed_pushes_to_picker(
    mocker, client, stripe_construct_event, pending_payment_claim, claim_in_db,
):
    mock_push = mocker.patch("app.routers.stripe_webhooks.send_push")
    pi_id = pending_payment_claim.stripe_payment_intent_id
    stripe_construct_event.return_value = _payment_failed_event(
        pi_id, "card_declined", "generic_decline",
    )
    resp = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )
    assert resp.status_code == 200
    mock_push.assert_called_once()
    call = mock_push.call_args
    assert call.args[1] == pending_payment_claim.picker_id
    assert call.args[5] == "payment_failed"
    assert call.args[6] == pending_payment_claim.id

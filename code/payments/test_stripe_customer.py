"""Phase 9-1 §14 — Stripe Customer creation at first claim (D66)."""
import uuid

from app import models
from app.services.stripe_service import (
    CLAIM_AMOUNT_CENTS,
    CLAIM_CURRENCY,
    create_payment_intent,
    ensure_stripe_customer,
)


def test_ensure_stripe_customer_happy_path(
    db_session, picker_user, mock_stripe_customer_create,
):
    customer_id = ensure_stripe_customer(picker_user, db_session)

    assert mock_stripe_customer_create.call_count == 1
    _, kwargs = mock_stripe_customer_create.call_args
    assert kwargs["email"] == picker_user.email
    assert kwargs["metadata"] == {"user_id": str(picker_user.id)}
    assert kwargs["idempotency_key"] == f"customer_{picker_user.id}"

    db_session.expire_all()
    refreshed = db_session.get(models.User, picker_user.id)
    assert refreshed.stripe_customer_id == customer_id


def test_ensure_stripe_customer_idempotency_key_uniqueness(
    db_session, picker_user, other_picker_user, mock_stripe_customer_create,
):
    ensure_stripe_customer(picker_user, db_session)
    ensure_stripe_customer(other_picker_user, db_session)

    assert mock_stripe_customer_create.call_count == 2
    keys = [
        call.kwargs["idempotency_key"]
        for call in mock_stripe_customer_create.call_args_list
    ]
    assert keys == [
        f"customer_{picker_user.id}",
        f"customer_{other_picker_user.id}",
    ]
    assert len(set(keys)) == 2


def test_ensure_stripe_customer_existing_customer_returns_same_id(
    db_session, picker_user, mock_stripe_customer_create,
):
    picker_user.stripe_customer_id = "cus_pre_existing_123"
    db_session.add(picker_user)
    db_session.commit()

    returned = ensure_stripe_customer(picker_user, db_session)

    assert returned == "cus_pre_existing_123"
    assert mock_stripe_customer_create.call_count == 0


def test_create_payment_intent_passes_customer_and_setup_future_usage(
    db_session,
    picker_user,
    active_listing,
    mock_stripe_pi_create,
    mock_stripe_customer_create,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="pending_payment",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    create_payment_intent(claim.id, picker_user.id, db_session)

    assert mock_stripe_customer_create.call_count == 1
    assert mock_stripe_pi_create.call_count == 1
    _, kwargs = mock_stripe_pi_create.call_args
    assert kwargs["amount"] == CLAIM_AMOUNT_CENTS
    assert kwargs["currency"] == CLAIM_CURRENCY
    assert kwargs["capture_method"] == "manual"
    assert kwargs["setup_future_usage"] == "off_session"

    db_session.expire_all()
    refreshed_user = db_session.get(models.User, picker_user.id)
    assert refreshed_user.stripe_customer_id is not None
    assert kwargs["customer"] == refreshed_user.stripe_customer_id

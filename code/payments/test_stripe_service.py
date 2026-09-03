"""Phase 4a layer 6d — direct unit coverage for stripe_service edge paths."""
import logging
import uuid
from datetime import datetime, timezone

import pytest
import stripe

from app import models
from app.services.stripe_service import (
    CLAIM_AMOUNT_CENTS,
    CLAIM_CURRENCY,
    StripeServiceError,
    _hold_expires_at_from_payment_intent,
    cancel_payment_intent,
    capture_payment_intent,
    create_payment_intent,
)


def test_create_pi_uses_idempotency_key_and_metadata(
    db_session, picker_user, active_listing, mock_stripe_pi_create,
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

    assert mock_stripe_pi_create.call_count == 1
    _, kwargs = mock_stripe_pi_create.call_args
    assert kwargs["amount"] == CLAIM_AMOUNT_CENTS
    assert kwargs["currency"] == CLAIM_CURRENCY
    assert kwargs["capture_method"] == "manual"
    assert kwargs["idempotency_key"] == f"pi_claim_{claim.id}"
    metadata = kwargs["metadata"]
    assert metadata["claim_id"] == str(claim.id)
    assert metadata["listing_id"] == str(active_listing.id)
    assert metadata["picker_id"] == str(picker_user.id)


def test_capture_returns_none_when_amount_capturable_below_200(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id="pi_test_underfunded",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(amount_capturable=50, status="requires_capture"),
    )
    capture_mock = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
    )

    result = capture_payment_intent(claim.id, db_session)

    assert result is None
    capture_mock.assert_not_called()
    db_session.refresh(claim)
    assert claim.status == "authorized"
    assert claim.captured_at is None


def test_cancel_idempotent_when_pi_already_canceled(
    db_session, picker_user, active_listing, mocker,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id="pi_test_already_canceled",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        side_effect=stripe.error.InvalidRequestError(
            "PaymentIntent has already been canceled.",
            param=None,
            code="payment_intent_unexpected_state",
        ),
    )

    cancel_payment_intent(claim.id, "picker_cancel", db_session)


def test_capture_invalid_reason_raises_value_error(
    db_session, picker_user, active_listing,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()

    with pytest.raises(ValueError):
        capture_payment_intent(claim.id, db_session, reason="bogus_reason")


def test_capture_post_window_writes_auto_captured_status_and_timestamp(
    db_session, picker_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()

    capture_payment_intent(claim.id, db_session, reason="post_window")
    db_session.commit()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "auto_captured"
    assert fresh.auto_captured_at is not None
    assert fresh.captured_at is not None


def test_capture_post_window_underfunded_logs_dedicated_event_at_error_level(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(amount_capturable=50, status="requires_capture"),
    )
    capture_spy = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
    )

    error_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "error",
    )
    warning_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "warning",
    )

    result = capture_payment_intent(claim.id, db_session, reason="post_window")

    assert result is None
    capture_spy.assert_not_called()

    error_payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any(
        "post_window_capture_underfunded_likely_stripe_autovoid" in p
        for p in error_payloads
    )
    # Verify it did NOT log at warning level (the non-post_window path)
    warning_payloads = [c.args[0] for c in warning_spy.call_args_list if c.args]
    assert not any(
        "stripe_capture_skipped_underfunded" in p
        for p in warning_payloads
    )


def test_capture_adopts_already_captured_intent_without_recapturing(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """a3 — money moved at Stripe but the local write was lost. The next run must
    adopt Stripe's record, not re-capture and not report an auto-void."""
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(
            status="succeeded", amount_capturable=0, amount_received=200,
        ),
    )
    capture_spy = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
    )
    error_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "error",
    )

    result = capture_payment_intent(claim.id, db_session, reason="post_window")
    db_session.commit()

    assert result is not None
    capture_spy.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "auto_captured"
    assert fresh.auto_captured_at is not None
    assert fresh.captured_at is not None

    error_payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any(
        "stripe_capture_divergence_already_captured" in p for p in error_payloads
    )


def test_capture_does_not_adopt_succeeded_intent_below_fee(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """A succeeded intent that received less than the fee is NOT the a3 case and must
    fall through to the existing underfunded skip, leaving the claim untouched."""
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()

    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(
            status="succeeded", amount_capturable=50, amount_received=50,
        ),
    )
    capture_spy = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
    )

    result = capture_payment_intent(claim.id, db_session, reason="post_window")

    assert result is None
    capture_spy.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.captured_at is None


def test_hold_expires_at_reads_nested_capture_before(mocker, stripe_pi_factory):
    capture_before_ts = 1_800_000_000
    pi = stripe_pi_factory()
    pi.latest_charge = {
        "id": "ch_test_nested",
        "payment_method_details": {"card": {"capture_before": capture_before_ts}},
    }

    result = _hold_expires_at_from_payment_intent(pi)

    assert result == datetime.fromtimestamp(capture_before_ts, tz=timezone.utc)


def test_hold_expires_at_none_when_payment_method_details_absent(
    mocker, stripe_pi_factory,
):
    pi = stripe_pi_factory()
    pi.latest_charge = {"id": "ch_test_no_pmd"}
    warning_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "warning",
    )

    result = _hold_expires_at_from_payment_intent(pi)

    assert result is None
    warning_payloads = [c.args[0] for c in warning_spy.call_args_list if c.args]
    assert any("stripe_capture_before_missing" in p for p in warning_payloads)


def test_hold_expires_at_none_when_card_absent(mocker, stripe_pi_factory):
    pi = stripe_pi_factory()
    pi.latest_charge = {
        "id": "ch_test_no_card",
        "payment_method_details": {},
    }
    warning_spy = mocker.spy(
        __import__("app.services.stripe_service", fromlist=["logger"]).logger,
        "warning",
    )

    result = _hold_expires_at_from_payment_intent(pi)

    assert result is None
    warning_payloads = [c.args[0] for c in warning_spy.call_args_list if c.args]
    assert any("stripe_capture_before_missing" in p for p in warning_payloads)


def test_hold_expires_at_none_when_capture_before_not_a_number(
    mocker, stripe_pi_factory,
):
    pi = stripe_pi_factory()
    pi.latest_charge = {
        "id": "ch_test_bad_type",
        "payment_method_details": {"card": {"capture_before": "not-a-timestamp"}},
    }

    result = _hold_expires_at_from_payment_intent(pi)

    assert result is None

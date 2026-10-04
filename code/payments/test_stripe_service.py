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
    cancel_payment_intent,
    capture_payment_intent,
    create_payment_intent,
    retrieve_payment_intent_status,
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

    result, _ = _hold_expiry_and_card_fingerprint_from_payment_intent(pi)

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

    result, _ = _hold_expiry_and_card_fingerprint_from_payment_intent(pi)

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

    result, _ = _hold_expiry_and_card_fingerprint_from_payment_intent(pi)

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

    result, _ = _hold_expiry_and_card_fingerprint_from_payment_intent(pi)

    assert result is None


def _real_shaped_pi_id() -> str:
    return f"pi_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


def test_retrieve_status_returns_stripe_status(mocker):
    retrieve = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=mocker.MagicMock(status="requires_capture"),
    )
    pid = _real_shaped_pi_id()

    assert retrieve_payment_intent_status(pid) == "requires_capture"
    retrieve.assert_called_once_with(pid)


def test_retrieve_status_none_on_error(mocker):
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        side_effect=Exception("stripe is down"),
    )

    assert retrieve_payment_intent_status(_real_shaped_pi_id()) is None


def test_retrieve_status_none_for_synthetic_id(mocker):
    retrieve = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve")

    assert retrieve_payment_intent_status("pi_test_0123456789abcdef") is None
    retrieve.assert_not_called()


# ---------------------------------------------------------------------------
# D539 step 3, slice 2 — a completion covered by a Zelbi credit releases the hold
# instead of charging it, inside capture_payment_intent. A no-show, a late cancel and
# the 24-hour auto-capture charge exactly as before. Never charge-then-refund.
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from app.services.stripe_service import (  # noqa: E402
    CARD_CONFLICT_ALERT_KIND,
    CREDIT_RELEASE_METADATA_KEY,
)


def _give_credit(
    db_session, user, *, kind="giveaway", used_at=None, used_card_fingerprint=None,
) -> models.Credit:
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id, kind=kind, earned_at=now, expires_at=now + timedelta(days=90),
        used_at=used_at, used_card_fingerprint=used_card_fingerprint,
    )
    db_session.add(credit)
    db_session.commit()
    db_session.refresh(credit)
    return credit


def _covered_claim(
    db_session, listing, picker, *, status="authorized", kind="giveaway", card_fingerprint=None,
):
    """An authorized claim carrying a reserved credit, as checkout leaves it; with
    card_fingerprint, as the authorize webhook leaves it (D542 slice 2)."""
    credit = _give_credit(db_session, picker, kind=kind)
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status=status,
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
        credit_id=credit.id,
        card_fingerprint=card_fingerprint,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim, credit


def _stripe_logger():
    return __import__("app.services.stripe_service", fromlist=["logger"]).logger


def test_covered_completion_releases_hold_instead_of_capturing(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(a) pickup_completed + reserved credit + requires_capture → mark, then cancel;
    capture never called; completed with captured_at null; credit spent; non-None."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        return_value=stripe_pi_factory(pi_id=pid, status="canceled", amount_capturable=0),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    assert result.status == "canceled"
    modify.assert_called_once_with(pid, metadata={CREDIT_RELEASE_METADATA_KEY: str(claim.id)})
    cancel.assert_called_once_with(pid)
    capture.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.completed_at is not None
    assert fresh.captured_at is None
    assert fresh.auto_captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id


def test_covered_completion_adopts_already_captured_intent_and_leaves_credit_unused(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(b) money already moved at Stripe → a3 adopt: charged, credit stays unused,
    no release attempted. Never charge-then-refund."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(status="succeeded", amount_capturable=0, amount_received=200),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    modify.assert_not_called()
    cancel.assert_not_called()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is not None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is None
    assert fresh_credit.used_claim_id is None


@pytest.mark.parametrize(
    "reason, expected_status, stamp",
    [
        ("pickup_completed", "completed", "completed_at"),
        ("post_window", "auto_captured", "auto_captured_at"),
    ],
)
def test_canceled_intent_with_our_mark_adopts_the_release(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
    reason, expected_status, stamp,
):
    """(c) the release happened but the local write was lost: adopt it with no Stripe
    write, log the divergence, spend the credit. Reachable from every caller, so the
    sweeper (post_window) reconciles instead of looping on the underfunded error. D548:
    the adopt writes the status for the caller's reason, the way a live release does."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pi = stripe_pi_factory(status="canceled", amount_capturable=0)
    pi.metadata = {CREDIT_RELEASE_METADATA_KEY: str(claim.id)}
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve", return_value=pi)
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")
    error_spy = mocker.spy(_stripe_logger(), "error")

    result = capture_payment_intent(claim.id, db_session, reason=reason)
    db_session.commit()

    assert result is not None
    modify.assert_not_called()
    cancel.assert_not_called()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == expected_status
    assert getattr(fresh, stamp) is not None
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id
    payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any("stripe_release_divergence_already_released" in p for p in payloads)
    assert not any("post_window_capture_underfunded_likely_stripe_autovoid" in p for p in payloads)


def test_canceled_intent_without_our_mark_keeps_todays_behaviour(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(c2) a canceled intent with no mark is Stripe's own cancel: the underfunded
    skip as today, claim and credit untouched."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pi = stripe_pi_factory(status="canceled", amount_capturable=0)
    pi.metadata = {"claim_id": str(claim.id)}
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve", return_value=pi)
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")
    warning_spy = mocker.spy(_stripe_logger(), "warning")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")

    assert result is None
    modify.assert_not_called()
    cancel.assert_not_called()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.captured_at is None
    assert fresh.completed_at is None
    assert db_session.get(models.Credit, credit.id).used_at is None
    payloads = [c.args[0] for c in warning_spy.call_args_list if c.args]
    assert any("stripe_capture_skipped_underfunded" in p for p in payloads)


def _unexpected_state():
    return stripe.error.InvalidRequestError(
        "This PaymentIntent could not be canceled because it has a status of succeeded.",
        param=None,
        code="payment_intent_unexpected_state",
    )


def test_release_losing_a_race_to_a_capture_is_charged_with_credit_unused(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(d) cancel raises payment_intent_unexpected_state and the re-read shows
    succeeded: the money moved, so the claim is charged and the credit unused. The
    swallow inside cancel_payment_intent would have recorded 'free by credit' here."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        side_effect=[
            stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
            stripe_pi_factory(pi_id=pid, status="succeeded", amount_capturable=0, amount_received=200),
        ],
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel", side_effect=_unexpected_state(),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")
    error_spy = mocker.spy(_stripe_logger(), "error")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    assert result.status == "succeeded"
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is not None
    assert db_session.get(models.Credit, credit.id).used_at is None
    payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any("stripe_capture_divergence_already_captured" in p for p in payloads)


@pytest.mark.parametrize("again_status", ["canceled", "requires_capture", "processing"])
def test_release_unexpected_state_with_unknown_reread_raises(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory, again_status,
):
    """(d) cancel raises payment_intent_unexpected_state and the re-read is anything
    but succeeded: nothing is written either way; the caller gets StripeServiceError."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pid = claim.stripe_payment_intent_id
    again = stripe_pi_factory(pi_id=pid, status=again_status, amount_capturable=0)
    again.metadata = {}
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        side_effect=[
            stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
            again,
        ],
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel", side_effect=_unexpected_state(),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    with pytest.raises(StripeServiceError):
        capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.rollback()

    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.captured_at is None
    assert fresh.completed_at is None
    assert db_session.get(models.Credit, credit.id).used_at is None


def test_release_other_cancel_error_raises_without_writing(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(amount_capturable=200, status="requires_capture"),
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        side_effect=stripe.error.APIConnectionError("simulated"),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    with pytest.raises(StripeServiceError):
        capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.rollback()

    capture.assert_not_called()
    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "authorized"
    assert db_session.get(models.Credit, credit.id).used_at is None


def test_no_show_with_reserved_credit_releases_hold_and_uses_credit_up(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(e) D548: a no-show on a covered claim releases the hold instead of charging;
    the credit is used up on this claim and captured_at stays null."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        return_value=stripe_pi_factory(pi_id=pid, status="canceled", amount_capturable=0),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    result = capture_payment_intent(claim.id, db_session, reason="no_show")
    db_session.commit()

    assert result is not None
    assert result.status == "canceled"
    modify.assert_called_once_with(pid, metadata={CREDIT_RELEASE_METADATA_KEY: str(claim.id)})
    cancel.assert_called_once_with(pid)
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "no_show"
    assert fresh.no_show_at is not None
    assert fresh.captured_at is None
    assert fresh.completed_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id


def test_post_window_with_reserved_credit_releases_hold_and_uses_credit_up(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(f) D548: the 24-hour silence completion on a covered claim releases the hold
    instead of charging; status auto_captured, captured_at null, credit used up."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user)
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        return_value=stripe_pi_factory(pi_id=pid, status="canceled", amount_capturable=0),
    )
    capture = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    result = capture_payment_intent(claim.id, db_session, reason="post_window")
    db_session.commit()

    assert result is not None
    assert result.status == "canceled"
    modify.assert_called_once_with(pid, metadata={CREDIT_RELEASE_METADATA_KEY: str(claim.id)})
    cancel.assert_called_once_with(pid)
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "auto_captured"
    assert fresh.auto_captured_at is not None
    assert fresh.captured_at is None
    assert fresh.completed_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id


def test_completion_without_credit_captures_as_before(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """(g) no credit → the release branch is never entered."""
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
        return_value=stripe_pi_factory(amount_capturable=200, status="requires_capture"),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    capture = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
        return_value=stripe_pi_factory(status="succeeded", amount_capturable=0),
    )

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    capture.assert_called_once()
    modify.assert_not_called()
    cancel.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is not None


# ---------------------------------------------------------------------------
# D542 slice 2 — the card rule, checked when a giveaway credit is spent. The card that
# pays the hold is read from the authorization's charge (the same read as the hold
# expiry) and stored on the claim; a giveaway credit is tied to it before its hold is
# released; a second person's giveaway credit on the same card loses the unique index
# and the pickup is charged with the credit left unused.
# ---------------------------------------------------------------------------

from app.routers.stripe_webhooks import _handle_amount_capturable_updated  # noqa: E402
from app.services.stripe_service import (  # noqa: E402
    _hold_expiry_and_card_fingerprint_from_payment_intent,
)

CARD_F = "fp_test_card_F"
CAPTURE_BEFORE_TS = 1_800_000_000


def _charge(*, fingerprint=CARD_F, capture_before=CAPTURE_BEFORE_TS) -> dict:
    card = {"capture_before": capture_before}
    if fingerprint is not None:
        card["fingerprint"] = fingerprint
    return {"id": "ch_test_one", "payment_method_details": {"card": card}}


def _as_utc(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def test_hold_expiry_and_fingerprint_read_from_one_inline_charge(stripe_pi_factory, mocker):
    charge_retrieve = mocker.patch("app.services.stripe_service.stripe.Charge.retrieve")
    pi = stripe_pi_factory()
    pi.latest_charge = _charge()

    expiry, fingerprint = _hold_expiry_and_card_fingerprint_from_payment_intent(pi)

    assert expiry == datetime.fromtimestamp(CAPTURE_BEFORE_TS, tz=timezone.utc)
    assert fingerprint == CARD_F
    charge_retrieve.assert_not_called()


def test_authorize_webhook_stores_card_fingerprint_and_hold_expiry_from_one_charge(
    db_session, pending_payment_claim, mocker,
):
    mocker.patch("app.routers.stripe_webhooks.send_push")
    charge_retrieve = mocker.patch(
        "app.services.stripe_service.stripe.Charge.retrieve", return_value=_charge(),
    )
    pi_retrieve = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve")
    pid = pending_payment_claim.stripe_payment_intent_id

    _handle_amount_capturable_updated(db_session, {"id": pid, "latest_charge": "ch_test_one"})

    charge_retrieve.assert_called_once_with("ch_test_one")
    pi_retrieve.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, pending_payment_claim.id)
    assert fresh.status == "authorized"
    assert fresh.card_fingerprint == CARD_F
    assert _as_utc(fresh.hold_expires_at) == datetime.fromtimestamp(CAPTURE_BEFORE_TS, tz=timezone.utc)


def test_authorize_webhook_without_fingerprint_still_authorizes_with_null_card(
    db_session, pending_payment_claim, mocker,
):
    mocker.patch("app.routers.stripe_webhooks.send_push")
    charge_retrieve = mocker.patch(
        "app.services.stripe_service.stripe.Charge.retrieve",
        return_value=_charge(fingerprint=None),
    )
    pid = pending_payment_claim.stripe_payment_intent_id

    _handle_amount_capturable_updated(db_session, {"id": pid, "latest_charge": "ch_test_one"})

    charge_retrieve.assert_called_once()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, pending_payment_claim.id)
    assert fresh.status == "authorized"
    assert fresh.card_fingerprint is None
    assert fresh.hold_expires_at is not None


def _release_mocks(mocker, stripe_pi_factory, pid):
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
    )
    modify = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    cancel = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        return_value=stripe_pi_factory(pi_id=pid, status="canceled", amount_capturable=0),
    )
    capture = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.capture",
        return_value=stripe_pi_factory(pi_id=pid, status="succeeded", amount_capturable=0),
    )
    return modify, cancel, capture


def test_covered_completion_on_an_unused_card_releases_and_stamps_the_card(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=CARD_F)
    modify, cancel, capture = _release_mocks(mocker, stripe_pi_factory, claim.stripe_payment_intent_id)

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None and result.status == "canceled"
    modify.assert_called_once()
    cancel.assert_called_once()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id
    assert fresh_credit.used_card_fingerprint == CARD_F


def _card_conflict_alerts(db_session) -> list[models.WatcherEvent]:
    db_session.expire_all()
    return (
        db_session.query(models.WatcherEvent)
        .filter(models.WatcherEvent.kind == CARD_CONFLICT_ALERT_KIND)
        .all()
    )


def test_card_that_spent_another_persons_giveaway_credit_is_still_released_with_an_alert(
    db_session, picker_user, other_picker_user, active_listing, mocker, stripe_pi_factory,
):
    """D548 addendum (c): the card decision was made at the pay tap, so a conflict found at
    completion (a race between two pay taps on one card) never charges. The hold is
    released, the credit is used up with used_card_fingerprint left null, and the conflict
    is logged at error level with a Control Center alert."""
    _give_credit(
        db_session, other_picker_user,
        used_at=datetime.now(timezone.utc), used_card_fingerprint=CARD_F,
    )
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=CARD_F)
    modify, cancel, capture = _release_mocks(mocker, stripe_pi_factory, claim.stripe_payment_intent_id)
    error_spy = mocker.spy(_stripe_logger(), "error")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None and result.status == "canceled"
    modify.assert_called_once()
    cancel.assert_called_once()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.completed_at is not None
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id
    assert fresh_credit.used_card_fingerprint is None
    payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any("giveaway_credit_card_conflict_at_release" in p for p in payloads)
    alerts = _card_conflict_alerts(db_session)
    assert len(alerts) == 1
    assert alerts[0].family == "account"
    assert alerts[0].ref == str(claim.id)
    assert alerts[0].payload["credit_id"] == str(credit.id)


def test_referral_credit_on_a_card_that_spent_a_giveaway_credit_is_released(
    db_session, picker_user, other_picker_user, active_listing, mocker, stripe_pi_factory,
):
    _give_credit(
        db_session, other_picker_user,
        used_at=datetime.now(timezone.utc), used_card_fingerprint=CARD_F,
    )
    claim, credit = _covered_claim(
        db_session, active_listing, picker_user, kind="referral", card_fingerprint=CARD_F,
    )
    modify, cancel, capture = _release_mocks(mocker, stripe_pi_factory, claim.stripe_payment_intent_id)

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None and result.status == "canceled"
    cancel.assert_called_once()
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_card_fingerprint is None


def test_claim_with_no_fingerprint_is_released_without_the_card_check(
    db_session, picker_user, other_picker_user, active_listing, mocker, stripe_pi_factory,
):
    _give_credit(
        db_session, other_picker_user,
        used_at=datetime.now(timezone.utc), used_card_fingerprint=CARD_F,
    )
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=None)
    modify, cancel, capture = _release_mocks(mocker, stripe_pi_factory, claim.stripe_payment_intent_id)

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None and result.status == "canceled"
    cancel.assert_called_once()
    capture.assert_not_called()
    db_session.expire_all()
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_card_fingerprint is None


def test_release_losing_a_race_to_a_capture_takes_the_card_stamp_off(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    """The stamp lands before the Stripe writes; when the release loses to a capture the
    credit stays unused, so it must not keep the card either."""
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=CARD_F)
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        side_effect=[
            stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
            stripe_pi_factory(pi_id=pid, status="succeeded", amount_capturable=0, amount_received=200),
        ],
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel", side_effect=_unexpected_state(),
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None and result.status == "succeeded"
    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).captured_at is not None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is None
    assert fresh_credit.used_card_fingerprint is None


def _adopt_mocks(mocker, stripe_pi_factory, claim):
    pi = stripe_pi_factory(status="canceled", amount_capturable=0)
    pi.metadata = {CREDIT_RELEASE_METADATA_KEY: str(claim.id)}
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve", return_value=pi)
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.cancel")
    return mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")


def test_adopted_release_stamps_the_card(
    db_session, picker_user, active_listing, mocker, stripe_pi_factory,
):
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=CARD_F)
    capture = _adopt_mocks(mocker, stripe_pi_factory, claim)

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_card_fingerprint == CARD_F


def test_adopted_release_with_a_card_conflict_still_adopts_and_leaves_the_field_null(
    db_session, picker_user, other_picker_user, active_listing, mocker, stripe_pi_factory,
):
    _give_credit(
        db_session, other_picker_user,
        used_at=datetime.now(timezone.utc), used_card_fingerprint=CARD_F,
    )
    claim, credit = _covered_claim(db_session, active_listing, picker_user, card_fingerprint=CARD_F)
    capture = _adopt_mocks(mocker, stripe_pi_factory, claim)
    error_spy = mocker.spy(_stripe_logger(), "error")

    result = capture_payment_intent(claim.id, db_session, reason="pickup_completed")
    db_session.commit()

    assert result is not None
    capture.assert_not_called()
    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "completed"
    assert fresh.completed_at is not None
    assert fresh.captured_at is None
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is not None
    assert fresh_credit.used_claim_id == claim.id
    assert fresh_credit.used_card_fingerprint is None
    payloads = [c.args[0] for c in error_spy.call_args_list if c.args]
    assert any("giveaway_credit_card_conflict_on_adopt" in p for p in payloads)
    assert any("stripe_release_divergence_already_released" in p for p in payloads)
    assert len(_card_conflict_alerts(db_session)) == 1

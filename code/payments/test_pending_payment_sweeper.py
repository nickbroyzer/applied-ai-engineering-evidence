"""Pending-payment sweeper — abandoned pending_payment claims (Nick, 2026-08-10)."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text

from app import models
from app.jobs.pending_payment_sweeper import run_pending_payment_sweeper


def _make_claim(db_session, listing, picker, *, status, claimed_offset_minutes: float):
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="pending_payment",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    claimed_at = datetime.utcnow() + timedelta(minutes=claimed_offset_minutes)
    db_session.execute(
        text("UPDATE claims SET status=:s, claimed_at=:t WHERE id=:cid"),
        {"cid": claim.id, "s": status, "t": claimed_at},
    )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(models.Claim, claim.id)


def test_pending_payment_past_window_is_cancelled_and_listing_relisted(
    db_session, picker_user, active_listing, mock_stripe_pi_cancel,
):
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pending_payment", claimed_offset_minutes=-6,
    )
    db_session.execute(
        text("UPDATE listings SET status='claimed' WHERE id=:lid"),
        {"lid": active_listing.id},
    )
    db_session.commit()
    db_session.expire_all()

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 1
    assert result.errored == 0

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "cancelled"
    assert fresh_claim.cancelled_at is not None

    fresh_listing = db_session.get(models.Listing, active_listing.id)
    assert fresh_listing.status == "active"


def test_pending_payment_inside_window_is_untouched(
    db_session, picker_user, active_listing, mock_stripe_pi_cancel,
):
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pending_payment", claimed_offset_minutes=-2,
    )

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 0
    assert result.errored == 0

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "pending_payment"
    assert fresh_claim.cancelled_at is None


def test_authorized_claim_never_touched_however_old(
    db_session, picker_user, active_listing, mock_stripe_pi_cancel,
):
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized", claimed_offset_minutes=-60 * 24,
    )

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 0
    assert result.errored == 0
    mock_stripe_pi_cancel.assert_not_called()

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "authorized"
    assert fresh_claim.cancelled_at is None


def test_listing_already_moved_on_is_left_alone(
    db_session, picker_user, active_listing, mock_stripe_pi_cancel,
):
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pending_payment", claimed_offset_minutes=-6,
    )
    db_session.execute(
        text("UPDATE listings SET status='expired' WHERE id=:lid"),
        {"lid": active_listing.id},
    )
    db_session.commit()
    db_session.expire_all()

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 1
    assert result.errored == 0

    db_session.expire_all()
    fresh_claim = db_session.get(models.Claim, claim.id)
    assert fresh_claim.status == "cancelled"

    fresh_listing = db_session.get(models.Listing, active_listing.id)
    assert fresh_listing.status == "expired"


def _real_shaped_pi_id() -> str:
    """A 24+ char id, so is_synthetic_payment_intent_id treats it as possibly-live and
    the sweeper actually reads Stripe. The existing helper builds 16-char ids, which
    are correctly skipped — these tests need the opposite branch."""
    return f"pi_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


def _stripe_intent(pi_id: str, *, status: str, amount_capturable: int):
    """A real Stripe object, not a MagicMock: the webhook handler pulls the id out with
    a dict lookup and refuses anything that is not text, which a MagicMock's .get would
    return. construct_from produces a genuine dict subclass."""
    import stripe as _stripe
    return _stripe.PaymentIntent.construct_from(
        {
            "id": pi_id,
            "status": status,
            "amount_capturable": amount_capturable,
        },
        "sk_test",
    )


def test_live_hold_is_promoted_not_cancelled(
    db_session, picker_user, active_listing, mocker, mock_stripe_pi_cancel,
):
    """a4 — the authorize webhook never arrived but the picker DID pay. The claim must
    be promoted to authorized, not cancelled out from under him."""
    pi_id = _real_shaped_pi_id()
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="pending_payment",
        stripe_payment_intent_id=pi_id,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    db_session.execute(
        text("UPDATE claims SET claimed_at=:t WHERE id=:cid"),
        {"cid": claim.id, "t": datetime.utcnow() - timedelta(minutes=6)},
    )
    db_session.commit()
    db_session.expire_all()

    mocker.patch(
        "app.jobs.pending_payment_sweeper.stripe.PaymentIntent.retrieve",
        return_value=_stripe_intent(
            pi_id, status="requires_capture", amount_capturable=200
        ),
    )

    result = run_pending_payment_sweeper(db_session)

    assert result.promoted == 1
    assert result.cancelled == 0
    mock_stripe_pi_cancel.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.authorized_at is not None
    assert fresh.cancelled_at is None


def test_no_live_hold_still_cancels(
    db_session, picker_user, active_listing, mocker, mock_stripe_pi_cancel,
):
    """The guard must not swallow genuine abandonment: an intent with no capturable
    hold still takes the five-minute cancellation."""
    pi_id = _real_shaped_pi_id()
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="pending_payment",
        stripe_payment_intent_id=pi_id,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    db_session.execute(
        text("UPDATE claims SET claimed_at=:t WHERE id=:cid"),
        {"cid": claim.id, "t": datetime.utcnow() - timedelta(minutes=6)},
    )
    db_session.commit()
    db_session.expire_all()

    mocker.patch(
        "app.jobs.pending_payment_sweeper.stripe.PaymentIntent.retrieve",
        return_value=_stripe_intent(
            pi_id, status="requires_payment_method", amount_capturable=0
        ),
    )

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 1
    assert result.promoted == 0

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "cancelled"
    assert fresh.cancelled_at is not None

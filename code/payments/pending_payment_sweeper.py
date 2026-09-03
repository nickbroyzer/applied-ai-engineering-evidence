"""
Abandoned pending_payment claims sweeper.

Nick, 2026-08-10: a claim left in pending_payment for more than
PENDING_PAYMENT_TIMEOUT is abandoned — most commonly the picker opened
checkout and the app was killed before the client-side cancel ran, or before
Stripe ever confirmed. No other job selects on pending_payment, so nothing
else was releasing these. This sweep cancels the PaymentIntent, cancels the
claim, and relists the listing.

a4 GUARD: a claim can also sit in pending_payment because the authorize webhook
was never delivered, in which case the picker DID pay and a live hold exists.
Before cancelling, the sweep reads the PaymentIntent's true state: a live hold at
the full fee is promoted through the webhook handler instead of cancelled, and a
claim whose state cannot be read is left alone rather than written off.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Claim, Listing
from app.routers.stripe_webhooks import _handle_amount_capturable_updated
from app.services.stripe_service import (
    CLAIM_AMOUNT_CENTS,
    StripeServiceError,
    _configure_stripe,
    cancel_payment_intent,
    is_synthetic_payment_intent_id,
)

logger = logging.getLogger(__name__)

PENDING_PAYMENT_TIMEOUT = timedelta(minutes=5)


@dataclass
class PendingPaymentSweeperResult:
    cancelled: int
    errored: int
    promoted: int = 0


def _eligible_claims(db: Session, now: datetime) -> list[Claim]:
    threshold = now - PENDING_PAYMENT_TIMEOUT
    return (
        db.query(Claim)
        .filter(
            Claim.status == "pending_payment",
            Claim.claimed_at < threshold,
        )
        .all()
    )


def _retrieve_intent(claim: Claim):
    """Read the claim's PaymentIntent from Stripe, but ONLY when a hold could exist
    behind it. Returns None — meaning 'no hold possible, proceed to cancel' — when the
    claim carries no intent id, or an id that cannot be one Stripe issued. That reuses
    the same convention cancel_payment_intent applies, so the two paths cannot disagree
    about which ids are real. Raises on any Stripe failure: a claim whose true state
    cannot be read must NOT be cancelled, or a live hold is orphaned."""
    pid = claim.stripe_payment_intent_id
    if is_synthetic_payment_intent_id(pid):
        return None
    _configure_stripe()
    stripe.api_key = settings.stripe_api_key
    return stripe.PaymentIntent.retrieve(pid)


def _is_live_hold(intent) -> bool:
    """True only for an authorized, uncaptured hold covering the full claim fee."""
    if getattr(intent, "status", None) != "requires_capture":
        return False
    capturable = getattr(intent, "amount_capturable", None)
    return capturable is not None and int(capturable) >= CLAIM_AMOUNT_CENTS


def run_pending_payment_sweeper(db: Session) -> PendingPaymentSweeperResult:
    """Cancel claims abandoned in pending_payment past the timeout and relist."""
    # Naive UTC for comparison against TIMESTAMP WITHOUT TIME ZONE columns
    # (matches the convention used elsewhere in the codebase).
    now = datetime.utcnow()

    cancelled = 0
    errored = 0
    promoted = 0

    for claim in _eligible_claims(db, now):
        # a4 — the money's true home is Stripe, not this row. Read it before
        # deciding this claim was abandoned.
        try:
            intent = _retrieve_intent(claim)
        except Exception:
            errored += 1
            logger.exception(
                "pending_payment_sweeper_intent_read_failure claim_id=%s",
                str(claim.id),
            )
            continue

        if intent is not None and _is_live_hold(intent):
            logger.error(
                json.dumps(
                    {
                        "event": "pending_payment_divergence_live_hold",
                        "claim_id": str(claim.id),
                        "payment_intent_id": claim.stripe_payment_intent_id,
                        "action": "promoted to authorized; authorize webhook was never applied",
                    }
                )
            )
            try:
                _handle_amount_capturable_updated(db, intent)
            except Exception:
                db.rollback()
                errored += 1
                logger.exception(
                    "pending_payment_sweeper_promote_failure claim_id=%s",
                    str(claim.id),
                )
            else:
                promoted += 1
            continue

        try:
            cancel_payment_intent(claim.id, "pending_payment_abandoned", db)
        except StripeServiceError:
            db.rollback()
            errored += 1
            logger.error(
                json.dumps(
                    {
                        "event": "pending_payment_sweeper_stripe_error",
                        "claim_id": str(claim.id),
                    }
                )
            )
            continue

        listing = db.get(Listing, claim.listing_id)
        claim.status = "cancelled"
        claim.cancelled_at = datetime.now(timezone.utc)
        db.add(claim)
        if listing is not None and listing.status == "claimed":
            listing.status = "active"
            listing.available_since = datetime.utcnow()

        try:
            db.commit()
        except Exception:
            db.rollback()
            errored += 1
            logger.exception("pending_payment_sweeper_commit_failure")
            continue

        cancelled += 1
        logger.info(
            json.dumps(
                {
                    "event": "pending_payment_sweeper_cancelled",
                    "claim_id": str(claim.id),
                }
            )
        )

    return PendingPaymentSweeperResult(
        cancelled=cancelled, errored=errored, promoted=promoted
    )

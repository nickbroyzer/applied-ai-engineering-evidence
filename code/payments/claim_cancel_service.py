import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Claim, Listing, TrustEvent
from app.services.stripe_service import (
    StripeServiceError,
    cancel_payment_intent,
    capture_payment_intent,
)
from app.services.strike_service import check_and_apply_strike
from app.services.trust_service import recalculate_trust

logger = logging.getLogger(__name__)

ACTIVE_CLAIM_STATUSES = ("pending_payment", "authorized", "pickup_scheduled")
_GRACE_WINDOW_SECONDS = 2 * 60 * 60


def cancel_claim_for_initiator(
    db: Session,
    claim: Claim,
    listing: Listing,
    initiator_id: UUID,
    *,
    suppress_giver_trust_event: bool = False,
    bypass_grace_window: bool = False,
) -> None:
    """
    Core cancel logic shared by the manual cancel endpoint and the block handler.

    Applies the 2-hour grace window rule: if the initiator is the picker and a
    pickup is scheduled within 2h, the $2 hold is captured (late-cancel penalty);
    otherwise it is released. Does NOT commit — caller is responsible for committing
    and handling post-cancel notifications.

    bypass_grace_window=True (block handler only) skips the grace window
    entirely regardless of pickup proximity: the hold is always released, no
    late_cancel trust event is filed, and no strike is applied. Per Nick's
    2026-08-10 ruling, blocking someone never costs the picker money and never
    files a strike — the consented fee disclosure promises the hold is
    released on a block, with no exception for timing.

    Raises StripeServiceError on Stripe failures (with the same messages the cancel
    endpoint uses so the router can produce identical API responses).
    """
    is_picker = claim.picker_id == initiator_id
    is_giver = listing.giver_id == initiator_id

    inside_grace_window = False
    if (
        not bypass_grace_window
        and is_picker
        and claim.status in ("authorized", "pickup_scheduled")
        and claim.pickup_scheduled_at is not None
    ):
        sched = claim.pickup_scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        delta_seconds = (sched - datetime.now(timezone.utc)).total_seconds()
        inside_grace_window = delta_seconds < _GRACE_WINDOW_SECONDS

    if inside_grace_window:
        try:
            capture_payment_intent(claim.id, db, reason="no_show")
        except StripeServiceError:
            raise StripeServiceError("Payment capture failed")
        if listing is not None:
            listing.status = "active"
            listing.available_since = datetime.utcnow()
        db.add(
            TrustEvent(
                user_id=claim.picker_id,
                event_type="late_cancel",
                related_listing_id=claim.listing_id,
            )
        )
        recalculate_trust(db, claim.picker_id)
        try:
            check_and_apply_strike(db, claim.picker_id)
        except StripeServiceError:
            raise StripeServiceError("Strike enforcement failed")
    else:
        if claim.status in ACTIVE_CLAIM_STATUSES:
            try:
                cancel_payment_intent(
                    claim.id,
                    "picker_cancel" if is_picker else "giver_cancel",
                    db,
                )
            except StripeServiceError:
                raise StripeServiceError("Payment cancellation failed")
        prior_status = claim.status
        claim.status = "cancelled"
        claim.cancelled_at = datetime.now(timezone.utc)
        db.add(claim)
        if prior_status in ("authorized", "pickup_scheduled") and listing is not None:
            listing.status = "active"
            listing.available_since = datetime.utcnow()
        if is_giver and not suppress_giver_trust_event:
            db.add(
                TrustEvent(
                    user_id=initiator_id,
                    event_type="giver_cancelled_listing",
                    related_listing_id=claim.listing_id,
                )
            )
            recalculate_trust(db, initiator_id)

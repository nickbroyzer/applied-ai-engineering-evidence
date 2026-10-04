import logging
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.jobs.listing_expiry import expire_active_listings
from app.jobs.listing_expiry import (
    send_listing_expiring_reminders as run_listing_expiring_reminders,
)
from app.jobs.pickup_reminder import run_pickup_reminder
from app.jobs.post_window_sweeper import run_post_window_sweeper
from app.models import Claim, Dispute, Listing, TrustEvent, User
from app.schemas.datetimes import UtcDateTime
from app.services.standing_notices import send_branded
from app.services.strike_service import check_and_apply_dispute_suspension
from app.services.stripe_service import StripeServiceError, refund_captured_claim
from app.services.trust_service import recalculate_trust

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


class ExpireListingsResponse(BaseModel):
    expired_count: int


class SendPickupRemindersResponse(BaseModel):
    sent_count: int
    skipped_count: int


class SendListingExpiringRemindersResponse(BaseModel):
    sent_count: int
    skipped_count: int


class RunPostWindowSweeperResponse(BaseModel):
    captured: int
    skipped_underfunded: int
    errored: int
    auto_cancelled: int = 0
    reminders_sent: int = 0


class AdminDisputeResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    status: str
    resolution: str | None
    filed_at: UtcDateTime
    responded_at: UtcDateTime | None
    resolved_at: UtcDateTime | None
    notice_sent: bool = False

    model_config = {"from_attributes": True}


class AdminDisputeResolveBody(BaseModel):
    resolution: Literal["upheld_picker", "upheld_giver", "dismissed"]
    note: str = ""
    subject: str | None = None
    body: str | None = None


class AdminDisputeMessageBody(BaseModel):
    to: Literal["filer", "other", "both"]
    subject: str = Field(min_length=1)
    heading: str | None = None
    body: str = Field(min_length=1)


class AdminDisputeMessageResponse(BaseModel):
    sent: int
    status: str
    responded_at: UtcDateTime | None


@router.post("/expire-listings", response_model=ExpireListingsResponse)
def expire_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ExpireListingsResponse:
    count = expire_active_listings(db)
    return ExpireListingsResponse(expired_count=count)


@router.post("/send-pickup-reminders", response_model=SendPickupRemindersResponse)
def send_pickup_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SendPickupRemindersResponse:
    # D60 + D69 LOCKED: T-1h push-only reminders; T-24h logic removed.
    sent, skipped = run_pickup_reminder(db)
    return SendPickupRemindersResponse(sent_count=sent, skipped_count=skipped)


@router.post(
    "/run-post-window-sweeper",
    response_model=RunPostWindowSweeperResponse,
)
def run_post_window_sweeper_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RunPostWindowSweeperResponse:
    # D55 LOCKED — backstop sweeper exposed for Railway scheduled-job (5min cadence)
    # and for the Phase 9-1 gate-walk curl tests.
    result = run_post_window_sweeper(db)
    return RunPostWindowSweeperResponse(
        captured=result.captured,
        skipped_underfunded=result.skipped_underfunded,
        errored=result.errored,
        auto_cancelled=result.auto_cancelled,
        reminders_sent=result.reminders_sent,
    )


@router.post(
    "/send-listing-expiring-reminders",
    response_model=SendListingExpiringRemindersResponse,
)
def send_listing_expiring_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SendListingExpiringRemindersResponse:
    sent, skipped = run_listing_expiring_reminders(db)
    return SendListingExpiringRemindersResponse(sent_count=sent, skipped_count=skipped)


@router.post(
    "/disputes/{dispute_id}/respond",
    response_model=AdminDisputeResponse,
)
def respond_to_dispute(
    dispute_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminDisputeResponse:
    """D65 — operator marks 'we've responded'. pending → responded."""
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )
    if dispute.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute is not in pending status",
        )

    dispute.status = "responded"
    dispute.responded_at = datetime.utcnow()
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return AdminDisputeResponse.model_validate(dispute)


@router.post(
    "/disputes/{dispute_id}/resolve",
    response_model=AdminDisputeResponse,
)
def resolve_dispute(
    dispute_id: uuid.UUID,
    body: AdminDisputeResolveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminDisputeResponse:
    """D65 + D67 — operator resolves dispute; writes trust event and may suspend."""
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )
    if dispute.status not in ("pending", "responded"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute is already resolved",
        )

    claim = db.get(Claim, dispute.claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim for dispute not found",
        )
    listing = db.get(Listing, claim.listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing for claim not found",
        )

    now = datetime.utcnow()
    dispute.resolution = body.resolution
    dispute.status = "resolved"
    dispute.resolved_at = now
    db.add(dispute)

    # D63 / D67 — record trust event by resolution.
    suspended_picker_id: uuid.UUID | None = None
    if body.resolution == "upheld_picker":
        # Picker won; giver was wrong. If money was actually captured, refund it
        # HERE, before any write — a failed refund fails the whole resolution
        # (500, retryable, idempotent) rather than leaving a resolved dispute
        # whose refund silently never happened. Supersedes D61's manual-dashboard
        # remedy per Nick's 2026-08-11 ruling; D-entry pending. A claim with no
        # capture (hold released or lapsed) has nothing to return.
        if claim.captured_at is not None:
            try:
                refund_captured_claim(claim.id, db)
            except StripeServiceError:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Refund failed; dispute not resolved. Retry is safe.",
                ) from None
        db.add(
            TrustEvent(
                user_id=listing.giver_id,
                event_type="dispute_lost_giver",
                related_listing_id=claim.listing_id,
            )
        )
        recalculate_trust(db, listing.giver_id)
    elif body.resolution == "upheld_giver":
        db.add(
            TrustEvent(
                user_id=dispute.filer_user_id,
                event_type="dispute_lost_picker",
                related_listing_id=claim.listing_id,
            )
        )
        recalculate_trust(db, dispute.filer_user_id)
        suspended_picker_id = dispute.filer_user_id
    # dismissed → no event written

    filer = db.get(User, dispute.filer_user_id)
    reference = "ZLB-" + str(claim.id)[:6].upper()
    heading = "Dispute decided"
    subject = body.subject or f"Dispute decided · {listing.title}"
    reason = body.resolution + (f" · {body.note}" if body.note else "")
    if body.body:
        paragraphs = body.body.split("\n\n")
    else:
        decision_lines = {
            "upheld_picker": (
                "Decision: Upheld for you — the $2.00 claim fee has been refunded to "
                "your card; it shows within 5 to 10 business days depending on your bank."
            ),
            "upheld_giver": "Decision: The claim fee stands — the $2.00 will not be refunded.",
            "dismissed": "Decision: Dismissed — nothing changes, the $2.00 fee stands.",
        }
        closing_lines = {
            "upheld_picker": "Thank you for telling us what happened, and sorry the pickup fell through.",
            "upheld_giver": "If you have information we haven't seen, reply to this email.",
            "dismissed": "If something new comes up, reply to this email.",
        }
        paragraphs = [f"Item: {listing.title}", decision_lines[body.resolution]]
        if body.note:
            paragraphs.append(body.note)
        paragraphs.append(closing_lines[body.resolution])

    _, notice_sent = send_branded(
        db,
        actor=current_user,
        subject_user=filer,
        action="dispute_decision",
        reason=reason,
        heading=heading,
        paragraphs=paragraphs,
        reference=reference,
        subject=subject,
    )

    db.commit()
    db.refresh(dispute)

    if suspended_picker_id is not None:
        # D67 — apply suspension after the dispute row + trust event are
        # committed so the rolling-window count includes the new event.
        check_and_apply_dispute_suspension(
            db, suspended_picker_id, listing_id=listing.id, claim_id=claim.id
        )
        db.commit()

    response = AdminDisputeResponse.model_validate(dispute)
    response.notice_sent = notice_sent
    return response


@router.post(
    "/disputes/{dispute_id}/message",
    response_model=AdminDisputeMessageResponse,
)
def message_dispute(
    dispute_id: uuid.UUID,
    body: AdminDisputeMessageBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminDisputeMessageResponse:
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found",
        )
    claim = db.get(Claim, dispute.claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim for dispute not found",
        )
    listing = db.get(Listing, claim.listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing for claim not found",
        )

    filer_id = dispute.filer_user_id
    other_id = listing.giver_id if filer_id == claim.picker_id else claim.picker_id

    recipient_ids: list[uuid.UUID] = []
    if body.to in ("filer", "both"):
        recipient_ids.append(filer_id)
    if body.to in ("other", "both"):
        recipient_ids.append(other_id)

    reference = "ZLB-" + str(claim.id)[:6].upper()
    paragraphs = body.body.split("\n\n")
    sent_count = 0
    for recipient_id in recipient_ids:
        recipient = db.get(User, recipient_id)
        if recipient is None:
            continue
        _, sent = send_branded(
            db,
            actor=current_user,
            subject_user=recipient,
            action="dispute_email",
            reason=body.subject,
            heading=body.heading or body.subject,
            paragraphs=paragraphs,
            reference=reference,
            subject=body.subject,
        )
        if sent:
            sent_count += 1

    if dispute.status == "pending":
        dispute.status = "responded"
        dispute.responded_at = datetime.utcnow()
        db.add(dispute)

    db.commit()
    db.refresh(dispute)

    return AdminDisputeMessageResponse(
        sent=sent_count,
        status=dispute.status,
        responded_at=dispute.responded_at,
    )

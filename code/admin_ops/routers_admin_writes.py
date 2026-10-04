"""Admin writes — flag decisions, notes, listing actions and money-path fixes from the Control Center."""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.jobs.pending_payment_sweeper import _is_live_hold, _retrieve_intent, run_pending_payment_sweeper_for_claim
from app.models import AdminNote, Claim, Listing, Report, User
from app.routers.admin import require_admin
from app.routers.admin_actions import AdminActionBody, first_name
from app.routers.stripe_webhooks import _handle_amount_capturable_updated
from app.services.admin_notes import note_out, notes_for
from app.services.scam_detection import rule_definition
from app.services.standing_notices import record_action, send_branded

router = APIRouter(tags=["admin-writes"])
logger = logging.getLogger(__name__)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _flag_ref(report_id: Any) -> str:
    return "R-" + str(report_id)[:6].upper()


class FlagConfirmBody(BaseModel):
    note: str | None = None
    subject: str | None = None
    body: str | None = None


class FlagNoteBody(BaseModel):
    note: str | None = None


def _pending_auto_report(db: Session, report_id: uuid.UUID) -> tuple[Report, User]:
    report = db.get(Report, report_id)
    if report is None or report.source != "auto":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    if report.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Flag is already decided")
    user = db.get(User, report.reported_user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flagged user not found")
    return report, user


def _flag_out(report: Report, notice_sent: bool) -> dict[str, Any]:
    return {"report_id": str(report.id), "status": report.status, "notice_sent": notice_sent}


@router.post("/admin/flags/{report_id}/confirm")
def confirm_flag(
    report_id: uuid.UUID,
    body: FlagConfirmBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    report, user = _pending_auto_report(db, report_id)
    listing = db.get(Listing, report.listing_id) if report.listing_id is not None else None
    item = listing.title if listing is not None else "your Zelbi account"
    note = _clean(body.note)
    label, _ = rule_definition(report.triggered_rule)

    report.status = "resolved"
    report.resolved_at = datetime.utcnow()
    db.add(report)

    text_body = _clean(body.body)
    if text_body:
        paragraphs = [p for p in text_body.split("\n\n") if p.strip()]
    else:
        paragraphs = [f"Item: {item}"]
        paragraphs.append(note or "We noticed something in a recent listing or message of yours.")
        paragraphs.append(
            "Zelbi keeps everything (messages, pickup times and the claim fee) inside the app so "
            "both people are protected. This is a warning; a repeat can lead to a timeout or a suspension."
        )

    row, sent = send_branded(
        db,
        actor=current_user,
        subject_user=user,
        action="flag_warn",
        reason=note or label,
        heading="Warning",
        paragraphs=paragraphs,
        to_email="" if user.deleted_at is not None else None,
        reference=_flag_ref(report.id),
        subject=_clean(body.subject) or f"Warning · {item}",
    )
    row.details = {"report_id": str(report.id), "rule": report.triggered_rule}
    db.commit()
    return _flag_out(report, sent)


@router.post("/admin/flags/{report_id}/false-positive")
def false_positive_flag(
    report_id: uuid.UUID,
    body: FlagNoteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    report, user = _pending_auto_report(db, report_id)
    report.status = "dismissed"
    report.resolved_at = datetime.utcnow()
    db.add(report)
    row = record_action(
        db, actor=current_user, subject=user, action="flag_false_positive",
        reason=_clean(body.note) or "False positive",
    )
    row.details = {"report_id": str(report.id), "rule": report.triggered_rule}
    db.commit()
    return _flag_out(report, False)


@router.post("/admin/flags/{report_id}/escalate")
def escalate_flag(
    report_id: uuid.UUID,
    body: AdminActionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    report, user = _pending_auto_report(db, report_id)
    if not user.is_suspended:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suspend the user first")
    report.status = "resolved"
    report.resolved_at = datetime.utcnow()
    db.add(report)
    row = record_action(db, actor=current_user, subject=user, action="flag_escalate", reason=body.reason)
    row.details = {"report_id": str(report.id), "rule": report.triggered_rule}
    db.commit()
    return _flag_out(report, False)


_NOTE_SUBJECTS = {"claim": Claim, "user": User, "listing": Listing}


class NoteBody(BaseModel):
    subject_kind: Literal["claim", "user", "listing"]
    subject_id: uuid.UUID
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped


@router.post("/admin/notes", status_code=status.HTTP_201_CREATED)
def create_note(
    body: NoteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    if db.get(_NOTE_SUBJECTS[body.subject_kind], body.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    note = AdminNote(
        author_user_id=current_user.id,
        subject_kind=body.subject_kind,
        subject_id=body.subject_id,
        body=body.text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note_out(note, current_user.display_name)


@router.get("/admin/notes")
def list_notes(
    subject_kind: Literal["claim", "user", "listing"] = Query(...),
    subject_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    return notes_for(db, subject_kind, subject_id)


def _listing_ref(listing_id: Any) -> str:
    return "L-" + str(listing_id)[:6].upper()


class ListingTestBody(BaseModel):
    is_test: bool


_DEACTIVATABLE = ("active", "hidden_pending_review")


@router.post("/admin/listings/{listing_id}/test")
def set_listing_test(
    listing_id: uuid.UUID,
    body: ListingTestBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.is_test != body.is_test:
        giver = db.get(User, listing.giver_id)
        listing.is_test = body.is_test
        db.add(listing)
        row = record_action(
            db, actor=current_user, subject=giver, action="listing_test",
            reason="Tagged as test listing" if body.is_test else "Test tag removed",
        )
        row.details = {"listing_id": str(listing.id), "is_test": body.is_test}
        db.commit()
    return {"id": str(listing.id), "test": listing.is_test}


@router.post("/admin/listings/{listing_id}/deactivate")
def deactivate_listing(
    listing_id: uuid.UUID,
    body: AdminActionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.status not in _DEACTIVATABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active listing can be deactivated",
        )
    giver = db.get(User, listing.giver_id)
    before = listing.status
    # "removed" is the status delete_listing (listings.py) and users.py already use.
    # Photos are kept as evidence; nothing money-wise is touched: a listing with a
    # live claim is "claimed" and refused above.
    listing.status = "removed"
    db.add(listing)
    row, sent = send_branded(
        db,
        actor=current_user,
        subject_user=giver,
        action="listing_deactivate",
        reason=body.reason,
        heading="Listing removed",
        paragraphs=[f"Hi {first_name(giver)},", f"Item: {listing.title}", body.reason],
        to_email="" if giver.deleted_at is not None else None,
        reference=_listing_ref(listing.id),
        subject=f"Listing removed · {listing.title}",
    )
    row.details = {"listing_id": str(listing.id), "before": before, "after": "removed"}
    db.commit()
    return {"id": str(listing.id), "status": listing.status, "notice_sent": sent}


class MoneyFixBody(BaseModel):
    reason: str | None = None


def _pending_claim(db: Session, claim_id: uuid.UUID) -> tuple[Claim, User]:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim.status != "pending_payment":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Claim is no longer pending payment")
    picker = db.get(User, claim.picker_id)
    if picker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picker not found")
    return claim, picker


def _log_money_fix(event: str, claim: Claim, actor: User, before: str, after: str, **extra: Any) -> None:
    logger.info(json.dumps({
        "event": event, "claim_id": str(claim.id), "actor_user_id": str(actor.id),
        "before": before, "after": after, **extra,
    }))


@router.post("/admin/money/{claim_id}/resync")
def resync_claim_from_stripe(
    claim_id: uuid.UUID,
    body: MoneyFixBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    claim, picker = _pending_claim(db, claim_id)
    try:
        intent = _retrieve_intent(claim)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe could not be read; nothing changed") from None
    if intent is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This claim has no PaymentIntent Stripe issued")
    stripe_status = getattr(intent, "status", None)
    before = claim.status
    reason = _clean(body.reason) or f"Re-synced from Stripe: {stripe_status}"

    if _is_live_hold(intent):
        row = record_action(db, actor=current_user, subject=picker, action="money_resync", reason=reason)
        row.details = {"claim_id": str(claim.id), "before": before, "after": "authorized", "stripe": stripe_status}
        _handle_amount_capturable_updated(db, intent)  # commits the claim, listing and the action row
    elif stripe_status == "canceled":
        claim.status = "cancelled"
        claim.cancelled_at = datetime.now(timezone.utc)
        db.add(claim)
        listing = db.get(Listing, claim.listing_id)
        if listing is not None and listing.status == "claimed":
            listing.status = "active"
            listing.available_since = datetime.utcnow()
        row = record_action(db, actor=current_user, subject=picker, action="money_resync", reason=reason)
        row.details = {"claim_id": str(claim.id), "before": before, "after": "cancelled", "stripe": stripe_status}
        db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Stripe says {stripe_status}; nothing to re-sync")

    db.refresh(claim)
    _log_money_fix("admin_money_resync", claim, current_user, before, claim.status, stripe=stripe_status)
    return {"claim_id": str(claim.id), "before": before, "after": claim.status, "stripe": stripe_status}


@router.post("/admin/money/{claim_id}/sweep")
def sweep_one_claim(
    claim_id: uuid.UUID,
    body: MoneyFixBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    claim, picker = _pending_claim(db, claim_id)
    before = claim.status
    outcome = run_pending_payment_sweeper_for_claim(db, claim.id)
    if outcome is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a claim pending payment for over 5 minutes can be swept")
    db.refresh(claim)
    if outcome == "errored":
        _log_money_fix("admin_money_sweep_failed", claim, current_user, before, claim.status)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The sweeper could not finish this claim; nothing changed")
    row = record_action(db, actor=current_user, subject=picker, action="money_sweep", reason=_clean(body.reason) or f"Sweeper run for one claim: {outcome}")
    row.details = {"claim_id": str(claim.id), "before": before, "after": claim.status, "outcome": outcome}
    db.commit()
    _log_money_fix("admin_money_sweep", claim, current_user, before, claim.status, outcome=outcome)
    return {"claim_id": str(claim.id), "before": before, "after": claim.status, "outcome": outcome}

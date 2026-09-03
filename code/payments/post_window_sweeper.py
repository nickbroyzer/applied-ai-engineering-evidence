"""
D55 — Default-capture backstop sweeper (post-pickup window).
D105 — Auto-cancel at T+6d + T-24h reminder routing.

Runs on a Railway scheduled job at 5-minute cadence (configuration outside repo).
Picks up authorized/pickup_scheduled claims past the backstop threshold and
captures via Stripe with reason="post_window", landing them in auto_captured.

Threshold (D55 LOCKED, pinged branch amended by D444):
- geofence_confirmed_at IS NOT NULL → 2 hours after the LATER of pickup_scheduled_at
  and geofence_confirmed_at (an early ping never charges sooner than the appointment
  + 2h; a late ping gives the picker two full hours from arrival)
- geofence_confirmed_at IS NULL     → pickup_scheduled_at + 24 hours

D105 auto-cancel: authorized claims with no pickup coordination after 6 days
are voided (not captured) and relisted — no trust event, no strike.

On underfunded capture (Stripe auto-void already fired): log at error level
and skip — claim stays in its prior status; the D62 webhook alarm catches it
when Stripe's payment_intent.canceled webhook arrives.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Claim, Listing, TrustEvent, User
from app.services.block_service import is_blocked
from app.services.notification_service import send_push
from app.services.stripe_service import (
    StripeServiceError,
    cancel_payment_intent,
    capture_payment_intent,
)
from app.services.stripe_service import is_synthetic_payment_intent_id
from app.services.trust_service import recalculate_trust
from app.services.tz_service import format_local

logger = logging.getLogger(__name__)


@dataclass
class SweeperResult:
    captured: int
    skipped_underfunded: int
    errored: int
    auto_cancelled: int = field(default=0)
    reminders_sent: int = field(default=0)


def _eligible_claims(db: Session, now: datetime) -> list[Claim]:
    geofence_threshold = now - timedelta(hours=2)
    no_geofence_threshold = now - timedelta(hours=24)
    return (
        db.query(Claim)
        .filter(
            Claim.status.in_(("authorized", "pickup_scheduled")),
            Claim.pickup_scheduled_at.isnot(None),
            or_(
                and_(
                    Claim.geofence_confirmed_at.isnot(None),
                    Claim.pickup_scheduled_at < geofence_threshold,
                    # D444 — both must be older than 2h: "later of the two".
                    Claim.geofence_confirmed_at < geofence_threshold,
                ),
                and_(
                    Claim.geofence_confirmed_at.is_(None),
                    Claim.pickup_scheduled_at < no_geofence_threshold,
                ),
            ),
        )
        .all()
    )


def _eligible_for_auto_cancel(db: Session, now: datetime) -> list[Claim]:
    """Claims authorized > 6d ago with no completed pickup coordination (D105)."""
    threshold = now - timedelta(days=6)
    return (
        db.query(Claim)
        .filter(
            Claim.status == "authorized",
            Claim.authorized_at.isnot(None),
            Claim.authorized_at < threshold,
            or_(
                Claim.pickup_mode.is_(None),
                and_(
                    Claim.pickup_mode == "meet",
                    Claim.pickup_scheduled_at.is_(None),
                ),
            ),
        )
        .all()
    )


def _eligible_for_imminent_reminder(db: Session, now: datetime) -> list[Claim]:
    """Claims whose PICKUP is roughly a day away.

    Separate from the deadline nudges below, which select on how old the claim is. These
    reminders say "your pickup is coming up at 3pm", so they must be chosen by when the
    pickup is, not by when the claim was made. They shared the deadline query until
    2026-08-29, which also required status "authorized" — and every route that sets a
    pickup time writes "pickup_scheduled" in the same statement, so no claim could ever
    satisfy both and none of these four types had ever fired.
    """
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)
    return (
        db.query(Claim)
        .filter(
            Claim.status.in_(("authorized", "pickup_scheduled")),
            Claim.pickup_scheduled_at.isnot(None),
            Claim.pickup_scheduled_at >= window_start,
            Claim.pickup_scheduled_at < window_end,
        )
        .all()
    )


def _eligible_for_t_minus_24h_reminder(db: Session, now: datetime) -> list[Claim]:
    """Claims in the 24h window before the 6d auto-cancel threshold (D105)."""
    five_day = now - timedelta(days=5)
    six_day = now - timedelta(days=6)
    return (
        db.query(Claim)
        .filter(
            Claim.status == "authorized",
            Claim.authorized_at.isnot(None),
            Claim.authorized_at < five_day,
            Claim.authorized_at >= six_day,
        )
        .all()
    )


def _sync_listing_on_auto_captured(
    db: Session, listing: Listing, now: datetime
) -> None:
    listing.status = "completed"
    listing.completed_at = now
    db.add(listing)


def _send_picker_push(db: Session, claim: Claim, listing: Listing) -> None:
    try:
        send_push(
            db,
            claim.picker_id,
            "Pickup complete",
            "Your $2 claim fee was processed",
            {
                "type": "claim_auto_captured",
                "role": "picker",
                "claim_id": str(claim.id),
                "listing_id": str(listing.id),
            },
            "claim_auto_captured_picker",
            claim.id,
            digest=False,
        )
    except Exception:
        logger.exception("send_push_failed_claim_auto_captured_picker")


def _send_giver_push(db: Session, claim: Claim, listing: Listing) -> None:
    try:
        send_push(
            db,
            listing.giver_id,
            "Giveaway complete",
            listing.title,
            {
                "type": "claim_auto_captured",
                "role": "giver",
                "claim_id": str(claim.id),
                "listing_id": str(listing.id),
            },
            "claim_auto_captured_giver",
            claim.id,
            digest=False,
        )
    except Exception:
        logger.exception("send_push_failed_claim_auto_captured_giver")


def _release_blocked_claim(db: Session, claim: Claim, listing: Listing) -> bool:
    """Nick's 2026-08-10 ruling: blocking never costs the picker money. A claim whose
    parties have blocked each other must NOT be captured — but a block whose own
    cancellation failed at the Stripe call leaves the claim live and invisible to both
    sides, so this sweep is the only thing that can still reach it. Release the hold and
    close the claim instead of capturing. Returns True when the claim was handled.

    A hold that cannot be released is left exactly as it is rather than written off,
    matching cancel_payment_intent's own convention for an id Stripe cannot find."""
    if not is_blocked(db, claim.picker_id, listing.giver_id):
        return False

    if not is_synthetic_payment_intent_id(claim.stripe_payment_intent_id):
        try:
            cancel_payment_intent(claim.id, "block_ended_claim_swept", db)
        except StripeServiceError:
            db.rollback()
            logger.error(
                json.dumps(
                    {
                        "event": "blocked_claim_release_failed",
                        "claim_id": str(claim.id),
                        "payment_intent_id": claim.stripe_payment_intent_id,
                        "action": "left untouched for manual review; NOT captured",
                    }
                )
            )
            return True

    claim.status = "cancelled"
    claim.cancelled_at = datetime.now(timezone.utc)
    db.add(claim)
    if listing.status == "claimed":
        listing.status = "active"
        listing.available_since = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("blocked_claim_release_commit_failure")
        return True

    logger.error(
        json.dumps(
            {
                "event": "blocked_claim_released_not_captured",
                "claim_id": str(claim.id),
                "note": "block-initiated cancellation had failed and left this claim live",
            }
        )
    )
    return True


def _run_auto_cancels(db: Session, now: datetime) -> int:
    """Void + cancel claims that never completed pickup coordination after 6d (D105)."""
    auto_cancelled = 0
    for claim in _eligible_for_auto_cancel(db, now):
        listing = db.get(Listing, claim.listing_id)
        try:
            cancel_payment_intent(claim.id, "auto_cancel_no_pickup", db)
        except StripeServiceError as exc:
            db.rollback()
            # A real id Stripe cannot find means the hold may still be live on a
            # different account. The claim is NOT written off — it is left exactly as
            # it is and raised at error level under its own event name so it can be
            # alarmed on and resolved by a human. Every other Stripe failure keeps the
            # prior behaviour: log and move to the next claim.
            if getattr(exc, "code", None) == "resource_missing":
                logger.error(
                    json.dumps(
                        {
                            "event": "auto_cancel_orphaned_hold_suspected",
                            "claim_id": str(claim.id),
                            "payment_intent_id": claim.stripe_payment_intent_id,
                            "action": "left untouched for manual review",
                        }
                    )
                )
                continue
            logger.error(
                json.dumps(
                    {
                        "event": "auto_cancel_stripe_error",
                        "claim_id": str(claim.id),
                    }
                )
            )
            continue

        claim.status = "cancelled"
        if listing is not None:
            listing.status = "active"
            listing.available_since = datetime.utcnow()
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("auto_cancel_commit_failure")
            continue

        auto_cancelled += 1
        logger.info(
            json.dumps(
                {
                    "event": "auto_cancelled_no_pickup",
                    "claim_id": str(claim.id),
                }
            )
        )
        _send_auto_cancel_push(db, claim, listing, role="picker")
        _send_auto_cancel_push(db, claim, listing, role="giver")

    return auto_cancelled


def _send_auto_cancel_push(
    db: Session, claim: Claim, listing: Listing | None, *, role: str
) -> None:
    user_id = claim.picker_id if role == "picker" else (
        listing.giver_id if listing is not None else None
    )
    if user_id is None:
        return
    notification_type = f"claim_auto_cancelled_{role}"
    body = (
        "No pickup was arranged in time for this item."
        if role == "picker"
        else "No pickup was arranged in time. Item is relisted for others to claim."
    )
    try:
        send_push(
            db,
            user_id,
            "Pickup cancelled",
            body,
            {
                "type": "claim_auto_cancelled_no_pickup",
                "role": role,
                "claim_id": str(claim.id),
                "listing_id": str(claim.listing_id),
            },
            notification_type,
            claim.id,
            digest=False,
        )
    except Exception:
        logger.exception(f"send_push_failed_{notification_type}")


def _run_t_minus_24h_reminders(db: Session, now: datetime) -> int:
    """Send T-24h reminder pushes routed by pickup coordination state (D105)."""
    reminders_sent = 0
    for claim in _eligible_for_t_minus_24h_reminder(db, now):
        listing = db.get(Listing, claim.listing_id)
        if listing is None:
            continue

        sent = False
        if claim.pickup_mode is None:
            sent = _send_reminder(
                db, claim, listing.giver_id,
                "pickup_setup_reminder_giver",
                "Set a pickup window",
                "Choose in person or curbside",
                listing_id=str(listing.id),
            )
        elif claim.pickup_mode == "meet" and claim.pickup_scheduled_at is None:
            sent = _send_reminder(
                db, claim, claim.picker_id,
                "pickup_select_reminder_picker",
                "Choose a pickup time",
                listing.title,
                listing_id=str(listing.id),
            )

        if sent:
            reminders_sent += 1

    for claim in _eligible_for_imminent_reminder(db, now):
        listing = db.get(Listing, claim.listing_id)
        if listing is None:
            continue
        sent = False
        if claim.pickup_scheduled_at is not None:
            if claim.pickup_mode == "porch":
                sent_g = _send_reminder(
                    db, claim, listing.giver_id,
                    "pickup_imminent_reminder_giver_porch",
                    "Upcoming pickup tomorrow",
                    listing.title,
                    listing_id=str(listing.id),
                )
                sent_p = _send_reminder(
                    db, claim, claim.picker_id,
                    "pickup_imminent_reminder_picker_porch",
                    "Upcoming pickup tomorrow",
                    listing.title,
                    listing_id=str(listing.id),
                )
            else:
                sent_g = _send_reminder(
                    db, claim, listing.giver_id,
                    "pickup_imminent_reminder_giver",
                    "Upcoming pickup tomorrow",
                    listing.title,
                    listing_id=str(listing.id),
                )
                sent_p = _send_reminder(
                    db, claim, claim.picker_id,
                    "pickup_imminent_reminder_picker",
                    "Upcoming pickup tomorrow",
                    listing.title,
                    listing_id=str(listing.id),
                )
            sent = sent_g or sent_p

        if sent:
            reminders_sent += 1

    return reminders_sent


def _send_reminder(
    db: Session,
    claim: Claim,
    user_id,
    notification_type: str,
    title: str,
    body: str,
    listing_id: str | None = None,
) -> bool:
    data = {
        "type": notification_type,
        "claim_id": str(claim.id),
    }
    if listing_id is not None:
        data["listing_id"] = listing_id
    try:
        return send_push(
            db,
            user_id,
            title,
            body,
            data,
            notification_type,
            claim.id,
            digest=False,
        )
    except Exception:
        logger.exception(f"send_push_failed_{notification_type}")
        return False


def run_post_window_sweeper(db: Session) -> SweeperResult:
    """Sweep eligible claims: auto-cancel stalled, capture past-window, send T-24h reminders."""
    # Naive UTC for comparison against TIMESTAMP WITHOUT TIME ZONE columns
    # (matches the convention used elsewhere in the codebase).
    now = datetime.utcnow()

    # D105: void + cancel claims with no pickup coordination after 6d (before capture sweep).
    auto_cancelled = _run_auto_cancels(db, now)

    eligible = _eligible_claims(db, now)
    captured = 0
    skipped_underfunded = 0
    errored = 0

    for claim in eligible:
        listing = db.get(Listing, claim.listing_id)
        if listing is None:
            errored += 1
            logger.error(
                json.dumps(
                    {
                        "event": "post_window_sweeper_listing_missing",
                        "claim_id": str(claim.id),
                    }
                )
            )
            continue

        # Blocked parties: release, never capture (Nick 2026-08-10). Must sit ahead of
        # the capture call — this is the only path that can still reach a claim whose
        # block-time cancellation failed.
        if _release_blocked_claim(db, claim, listing):
            continue

        try:
            payment_intent = capture_payment_intent(
                claim.id, db, reason="post_window"
            )
        except StripeServiceError:
            db.rollback()
            errored += 1
            logger.error(
                json.dumps(
                    {
                        "event": "post_window_sweeper_capture_failure",
                        "claim_id": str(claim.id),
                    }
                )
            )
            continue

        if payment_intent is None:
            db.rollback()
            skipped_underfunded += 1
            logger.error(
                json.dumps(
                    {
                        "event": "post_window_sweeper_underfunded",
                        "claim_id": str(claim.id),
                    }
                )
            )
            continue

        # Listing sync + trust events — same outcome as a picker-confirmed
        # completion, since silence past the backstop window means the picker
        # got the item (D55 mechanic 4 framing).
        _sync_listing_on_auto_captured(db, listing, now)
        db.add(
            TrustEvent(
                user_id=claim.picker_id,
                event_type="pickup_completed",
                related_listing_id=claim.listing_id,
            )
        )
        picker = db.get(User, claim.picker_id)
        if picker is not None:
            picker.completed_pickups = (picker.completed_pickups or 0) + 1
        db.add(
            TrustEvent(
                user_id=listing.giver_id,
                event_type="giveaway_completed",
                related_listing_id=claim.listing_id,
            )
        )
        giver = db.get(User, listing.giver_id)
        if giver is not None:
            giver.completed_giveaways = (giver.completed_giveaways or 0) + 1
        recalculate_trust(db, claim.picker_id)
        recalculate_trust(db, listing.giver_id)
        try:
            db.commit()
        except Exception:
            db.rollback()
            errored += 1
            logger.exception("post_window_sweeper_commit_failure")
            continue

        captured += 1
        logger.info(
            json.dumps(
                {
                    "event": "post_window_sweeper_captured",
                    "claim_id": str(claim.id),
                    "listing_id": str(listing.id),
                }
            )
        )
        _send_picker_push(db, claim, listing)
        _send_giver_push(db, claim, listing)

    # D105: T-24h reminder routing (after capture sweep).
    reminders_sent = _run_t_minus_24h_reminders(db, now)

    return SweeperResult(
        captured=captured,
        skipped_underfunded=skipped_underfunded,
        errored=errored,
        auto_cancelled=auto_cancelled,
        reminders_sent=reminders_sent,
    )

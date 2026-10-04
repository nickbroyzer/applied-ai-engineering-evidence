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

from sqlalchemy import DateTime, and_, func, or_
from sqlalchemy.orm import Session

from app.models import Claim, Listing, Notification, TrustEvent, User
from app.routers.claims import completion_fee_push_body
from app.services.block_service import is_blocked
from app.services.collect_ask import COLLECT_ASK_DELAY, collect_ask_at
from app.services.credit_service import GIVEAWAY_CREDIT_PUSH_BODY, maybe_award_giveaway_credit
from app.services.referral_service import maybe_award_referral_credit
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
    collect_asks_sent: int = field(default=0)


def _pickup_end(claim_col=Claim.pickup_scheduled_at):
    """When the pickup is over, per claim. D524: a curbside pickup runs to
    pickup_window_ends_at (21:00 local on the set-out day), so the 24-hour capture wait
    starts there, not at the set-out time — the item goes OUT at the set-out time. Meet in
    person, and any curbside claim booked before the change, leave the column null and keep
    the old behaviour."""
    return func.coalesce(Claim.pickup_window_ends_at, claim_col)


def _eligible_claims(db: Session, now: datetime) -> list[Claim]:
    geofence_threshold = now - timedelta(hours=2)
    no_geofence_threshold = now - timedelta(hours=24)
    pickup_end = _pickup_end()
    return (
        db.query(Claim)
        .filter(
            Claim.status.in_(("authorized", "pickup_scheduled")),
            Claim.pickup_scheduled_at.isnot(None),
            or_(
                and_(
                    Claim.geofence_confirmed_at.isnot(None),
                    pickup_end < geofence_threshold,
                    # D444 — both must be older than 2h: "later of the two".
                    Claim.geofence_confirmed_at < geofence_threshold,
                ),
                and_(
                    Claim.geofence_confirmed_at.is_(None),
                    pickup_end < no_geofence_threshold,
                ),
            ),
        )
        .all()
    )


def _eligible_for_curbside_auto_cancel(db: Session, now: datetime) -> list[Claim]:
    """D524 — a curbside set-out time the picker never confirmed. The proposal sits in
    proposed_times with the claim still authorized; at the set-out time it is over. The hold
    is voided, the item relists, nobody is asked anything and no strike is filed. Separate
    from the 6-day rule above, which only looks at claims with no times at all."""
    return (
        db.query(Claim)
        .filter(
            Claim.status == "authorized",
            Claim.pickup_mode == "porch",
            Claim.pickup_scheduled_at.is_(None),
            Claim.proposed_times.isnot(None),
            func.jsonb_array_length(Claim.proposed_times) > 0,
            func.cast(func.jsonb_array_element_text(Claim.proposed_times, 0), DateTime) < now,
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
    # The body reads the claim after the write: a post_window capture is always charged,
    # but the lost-write adopt inside capture_payment_intent can land a covered
    # completion here (D539 (1)), and that push must not say a fee was taken.
    try:
        send_push(
            db,
            claim.picker_id,
            "Pickup complete",
            completion_fee_push_body(claim),
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


def _send_giver_push(db: Session, claim: Claim, listing: Listing, *, earned_credit: bool = False) -> None:
    try:
        send_push(
            db,
            listing.giver_id,
            "Giveaway complete",
            GIVEAWAY_CREDIT_PUSH_BODY if earned_credit else listing.title,
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
    """Void + cancel claims that never completed pickup coordination after 6d (D105), and
    curbside proposals the picker never confirmed by the set-out time (D524)."""
    auto_cancelled = 0
    for claim in _eligible_for_auto_cancel(db, now) + _eligible_for_curbside_auto_cancel(db, now):
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
    if claim.pickup_mode == "porch":
        # D524 — this one expired because the picker never confirmed the set-out time.
        picker = db.get(User, claim.picker_id)
        picker_name = (picker.display_name or "").strip() if picker is not None else ""
        item = listing.title if listing is not None else "Your item"
        giver_body = (
            f"{picker_name} didn't confirm. {item} is back on Zelbi."
            if picker_name
            else f"Not confirmed in time. {item} is back on Zelbi."
        )
        body = (
            "You didn't confirm the pickup time, so the claim was cancelled. Your $2 hold was released."
            if role == "picker"
            else giver_body
        )
    else:
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


def _eligible_for_collect_ask(db: Session, now: datetime) -> list[Claim]:
    """Booked pickups whose end is at least COLLECT_ASK_DELAY old, with no photo and no
    charge yet. The exact ask time is checked per claim in Python (it needs the item's
    timezone)."""
    return (
        db.query(Claim)
        .filter(
            Claim.status.in_(("authorized", "pickup_scheduled")),
            Claim.pickup_scheduled_at.isnot(None),
            Claim.completion_photo_url.is_(None),
            Claim.captured_at.is_(None),
            _pickup_end() < now - COLLECT_ASK_DELAY,
        )
        .all()
    )


def _run_collect_asks(db: Session, now: datetime) -> int:
    """Session 459 — push the giver "Was your item picked up?" once the ask time passes.
    Sent once per claim ever: the per-day idempotency guard is not enough, because a claim
    can stay open across two calendar days before the 24-hour capture."""
    sent = 0
    now_aware = now.replace(tzinfo=timezone.utc)
    for claim in _eligible_for_collect_ask(db, now):
        listing = db.get(Listing, claim.listing_id)
        if listing is None:
            continue
        if is_blocked(db, claim.picker_id, listing.giver_id):
            continue
        ask_at = collect_ask_at(claim, listing)
        if ask_at is None or ask_at > now_aware:
            continue
        already = (
            db.query(Notification.id)
            .filter(
                Notification.notification_type == "collect_ask_giver",
                Notification.target_id == claim.id,
            )
            .first()
        )
        if already is not None:
            continue
        if _send_reminder(
            db, claim, listing.giver_id,
            "collect_ask_giver",
            "Was your item picked up?",
            listing.title,
            listing_id=str(listing.id),
        ):
            sent += 1
    return sent


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
        awarded_credit = None
        if giver is not None:
            giver.completed_giveaways = (giver.completed_giveaways or 0) + 1
            awarded_credit = maybe_award_giveaway_credit(db, giver=giver, claim=claim)
            maybe_award_referral_credit(db, friend=giver, claim=claim)
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
        _send_giver_push(db, claim, listing, earned_credit=awarded_credit is not None)

    # Session 459: asked only after capture ran, so a claim closed this run is never asked.
    collect_asks_sent = _run_collect_asks(db, now)

    # D105: T-24h reminder routing (after capture sweep).
    reminders_sent = _run_t_minus_24h_reminders(db, now)

    return SweeperResult(
        captured=captured,
        skipped_underfunded=skipped_underfunded,
        errored=errored,
        auto_cancelled=auto_cancelled,
        reminders_sent=reminders_sent,
        collect_asks_sent=collect_asks_sent,
    )

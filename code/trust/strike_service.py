"""
D21 picker strike enforcement.

check_and_apply_strike inspects the rolling 30-day no_show event count for a
picker, and if the threshold (3) is reached, sets picker_timeout_until and
fans out cancellations across the picker's other in-flight claims.

Called from mark_no_show (per D21 survey Q3) and cancel_claim's inside-window
branch (per D25). Both call sites invoke this BEFORE db.commit; if any Stripe
cancel call inside the fan-out raises, the exception propagates and the
caller's existing rollback path undoes the entire transaction (per D21 survey
Amendment 1).
"""

import json
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Claim, Listing, TrustEvent, User
from app.services.email_templates import branded_email
from app.services.email_service import send_email
from app.services.notification_service import send_push
from app.services.standing_notices import record_action
from app.services.stripe_service import cancel_payment_intent

logger = logging.getLogger(__name__)

_FAN_OUT_STATUSES = ("pending_payment", "authorized", "pickup_scheduled")
_ROLLING_WINDOW_DAYS = 30
_TIMEOUT_DAYS = 7
_STRIKE_THRESHOLD = 3

# D67 LOCKED — picker-only auto-suspension thresholds (90-day rolling window
# of dispute_lost_picker trust events).
_DISPUTE_ROLLING_WINDOW_DAYS = 90
_DISPUTE_WARNING_THRESHOLD = 2
_DISPUTE_SUSPEND_THRESHOLD = 3

# D67 + §10 notification copy — verbatim push bodies.
_D67_WARNING_PUSH_TITLE = "Account warning"
_D67_WARNING_PUSH_BODY = "One more lost dispute will suspend your account."
_D67_SUSPENSION_PUSH_TITLE = "Account suspended"
_D67_SUSPENSION_PUSH_BODY = (
    "Your account has been suspended after losing 3 disputes in 90 days. "
    "Contact support if you believe this is in error."
)


def check_and_apply_strike(db: Session, picker_id: UUID) -> None:
    """
    Apply the strike rule for the given picker if they have hit the threshold.

    picker_timeout_until is written as a NAIVE UTC datetime to match the existing
    User model timestamp pattern (User.created_at, updated_at, last_active_at all
    use Column(DateTime) with no timezone). The create_claim enforcement gate
    must compare with datetime.utcnow(), not datetime.now(timezone.utc) — mixing
    naive and aware datetimes raises TypeError on comparison.
    """
    threshold_dt = datetime.utcnow() - timedelta(days=_ROLLING_WINDOW_DAYS)
    count = (
        db.query(TrustEvent)
        .filter(
            TrustEvent.user_id == picker_id,
            TrustEvent.event_type == "no_show",
            TrustEvent.created_at >= threshold_dt,
        )
        .count()
    )

    if count < _STRIKE_THRESHOLD:
        logger.debug(
            json.dumps(
                {
                    "event": "strike_below_threshold",
                    "picker_id": str(picker_id),
                    "no_show_count": count,
                }
            )
        )
        return

    now = datetime.utcnow()
    user = db.get(User, picker_id)
    if user is not None:
        user.picker_timeout_until = now + timedelta(days=_TIMEOUT_DAYS)
        db.add(user)

    fan_out_claims = (
        db.query(Claim)
        .filter(
            Claim.picker_id == picker_id,
            Claim.status.in_(_FAN_OUT_STATUSES),
        )
        .all()
    )

    for claim in fan_out_claims:
        cancel_payment_intent(claim.id, "picker_timeout", db)

    for claim in fan_out_claims:
        prior_status = claim.status
        claim.status = "cancelled"
        db.add(claim)
        if prior_status in ("authorized", "pickup_scheduled"):
            listing = db.get(Listing, claim.listing_id)
            if listing is not None:
                listing.status = "active"
                listing.available_since = datetime.utcnow()

    db.flush()

    if user is not None:
        until_date = (now + timedelta(days=_TIMEOUT_DAYS)).strftime("%b %-d, %Y")
        # PLACEHOLDER COPY — Nick's standard message replaces this.
        reason = (
            f"You missed three pickups in 30 days, so claims are paused until "
            f"{until_date}. Any other claims you had open were cancelled and "
            f"their holds released."
        )
        row = record_action(db, actor=None, subject=user, action="timeout", reason=reason)
        db.flush()
        try:
            send_push(
                db,
                user.id,
                "Claims paused for 7 days",
                reason,
                {"type": "picker_timeout"},
                "picker_timeout",
                user.id,
            )
            # notify() commits, which would flush this function's uncommitted
            # picker_timeout/fan-out writes early — replicated here without the
            # commit; the caller's own db.commit() carries notice_sent.
            if user.deleted_at is None and user.email:
                html_body, text_body = branded_email(
                    heading="Claims paused for 7 days",
                    paragraphs=[reason],
                    reference=str(row.id)[:8].upper(),
                )
                try:
                    send_email(
                        to=user.email,
                        subject="Claims paused for 7 days",
                        html=html_body,
                        text=text_body,
                    )
                    row.notice_sent = True
                except Exception as exc:
                    logger.warning(
                        "strike timeout notice failed to send: action_id=%s exc_class=%s",
                        row.id,
                        type(exc).__name__,
                    )
        except Exception:
            logger.exception("strike_timeout_notification_failed")

    logger.info(
        json.dumps(
            {
                "event": "strike_applied",
                "picker_id": str(picker_id),
                "no_show_count": count,
                "timeout_until": (now + timedelta(days=_TIMEOUT_DAYS)).isoformat(),
                "fan_out_count": len(fan_out_claims),
            }
        )
    )


def check_and_apply_dispute_suspension(
    db: Session,
    picker_id: UUID,
    *,
    listing_id: UUID | None = None,
    claim_id: UUID | None = None,
) -> None:
    """D67 — picker-only auto-suspension by 90-day rolling dispute count.

    Counts dispute_lost_picker trust events for this picker in the trailing
    90 days. At threshold 2, fires a warning push (no column write — internal
    flag only). At threshold 3, flips is_suspended=True and fires the
    suspension push. Idempotent: re-running on an already-suspended user
    does nothing; warning push is day-bucket idempotent via the existing
    notification_idempotency table.

    Caller (the admin /resolve handler) writes the dispute_lost_picker trust
    event before invoking this; this function only reads.
    """
    user = db.get(User, picker_id)
    if user is None:
        return

    threshold_dt = datetime.utcnow() - timedelta(days=_DISPUTE_ROLLING_WINDOW_DAYS)
    count = (
        db.query(TrustEvent)
        .filter(
            TrustEvent.user_id == picker_id,
            TrustEvent.event_type == "dispute_lost_picker",
            TrustEvent.created_at >= threshold_dt,
        )
        .count()
    )

    if count >= _DISPUTE_SUSPEND_THRESHOLD:
        if user.is_suspended:
            logger.info(
                json.dumps(
                    {
                        "event": "dispute_suspension_already_suspended",
                        "picker_id": str(picker_id),
                        "dispute_count_90d": count,
                    }
                )
            )
            return

        user.is_suspended = True
        user.suspension_reason = _D67_SUSPENSION_PUSH_BODY
        db.add(user)
        row = record_action(
            db, actor=None, subject=user, action="suspend", reason=_D67_SUSPENSION_PUSH_BODY
        )
        db.flush()
        logger.info(
            json.dumps(
                {
                    "event": "dispute_suspension_applied",
                    "picker_id": str(picker_id),
                    "dispute_count_90d": count,
                }
            )
        )
        try:
            send_push(
                db,
                user.id,
                _D67_SUSPENSION_PUSH_TITLE,
                _D67_SUSPENSION_PUSH_BODY,
                {"type": "auto_suspended", "reason": "dispute_threshold"},
                "auto_suspended",
                user.id,
            )
        except Exception:
            logger.exception("send_push_failed_dispute_suspension")

        # notify() commits; the same early-commit conflict as check_and_apply_strike
        # applies here (the admin /resolve caller commits after this returns), so
        # the notify body is replicated without its commit.
        if user.deleted_at is None and user.email:
            html_body, text_body = branded_email(
                heading="Account disabled",
                paragraphs=[_D67_SUSPENSION_PUSH_BODY],
                reference=str(row.id)[:8].upper(),
            )
            try:
                send_email(
                    to=user.email,
                    subject="Account disabled",
                    html=html_body,
                    text=text_body,
                )
                row.notice_sent = True
            except Exception as exc:
                logger.warning(
                    "dispute suspension notice failed to send: action_id=%s exc_class=%s",
                    row.id,
                    type(exc).__name__,
                )
        return

    if count >= _DISPUTE_WARNING_THRESHOLD:
        warn_row = record_action(
            db, actor=None, subject=user, action="warn", reason=_D67_WARNING_PUSH_BODY
        )
        db.flush()
        try:
            send_push(
                db,
                user.id,
                _D67_WARNING_PUSH_TITLE,
                _D67_WARNING_PUSH_BODY,
                {
                    "type": "dispute_warning",
                    **({"listing_id": str(listing_id)} if listing_id else {}),
                    **({"claim_id": str(claim_id)} if claim_id else {}),
                },
                "dispute_warning",
                user.id,
            )
        except Exception:
            logger.exception("send_push_failed_dispute_warning")

        if user.deleted_at is None and user.email:
            html_body, text_body = branded_email(
                heading="Account warning",
                paragraphs=[_D67_WARNING_PUSH_BODY],
                reference=str(warn_row.id)[:8].upper(),
            )
            try:
                send_email(
                    to=user.email,
                    subject="Account warning",
                    html=html_body,
                    text=text_body,
                )
                warn_row.notice_sent = True
            except Exception as exc:
                logger.warning(
                    "dispute warning notice failed to send: action_id=%s exc_class=%s",
                    warn_row.id,
                    type(exc).__name__,
                )
        return

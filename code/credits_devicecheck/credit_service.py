"""Zelbi credits — earning (D539 step 4, D542).

Slice 1: the first-giveaway credit. Every ending that completes a handoff earns it
(the picker's photo, the giver's yes, and the post-window sweeper's silence branches),
once per person, only while the ``giveaway_credit`` program switch is on. The write sits
inside the completion's own transaction, in a savepoint, so losing the once-per-person
index race never fails the completion. Nothing here commits; the caller's commit does.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Claim, Credit, DeletedEmailFingerprint, ProgramSwitch, User, WatcherEvent
from app.utils.email_fingerprint import email_fingerprint

logger = logging.getLogger(__name__)

# D543 (5): a DeviceCheck refusal is a Control Center abuse alert, written to watcher_events
# the way api_abuse.record_api_signal writes a single-account signal.
DEVICE_REFUSAL_FAMILY = "account"
DEVICE_REFUSAL_KIND = "giveaway_credit_device_refused"
# D549 (survey C5): an invite credit refused because its iPhone already used a friend's code.
INVITE_DEVICE_REFUSAL_KIND = "invite_credit_device_refused"
# The credit kinds that wait for the iPhone check: giveaway (bit0, D542 (4)) and invite (bit1, D549).
DEVICE_CHECKED_CREDIT_KINDS = ("giveaway", "invite")
DEVICE_REFUSAL_SEVERITY = 4  # api_abuse's severity for a single-account signal
DEVICE_REFUSAL_SOURCE = "zelbi"

GIVEAWAY_CREDIT_SWITCH = "giveaway_credit"
# D539 (3): a credit lives 90 days from the day it is earned.
GIVEAWAY_CREDIT_LIFETIME = timedelta(days=90)
# D542 (7): Nick approved this wording (Session 465) for the giver's "Giveaway complete"
# push when the completion earned them a credit; otherwise the body stays listing.title.
GIVEAWAY_CREDIT_PUSH_BODY = "You earned a Zelbi credit. Your next pickup is on us."


def _skip(claim: Claim, giver: User, reason: str) -> None:
    logger.info(
        json.dumps(
            {
                "event": "giveaway_credit_skipped",
                "claim_id": str(claim.id),
                "giver_id": str(giver.id),
                "reason": reason,
            }
        )
    )


def maybe_award_giveaway_credit(db: Session, *, giver: User, claim: Claim) -> Credit | None:
    """Write the giver's first-giveaway credit for a handoff that just completed.

    Returns the new Credit, or None with nothing written when: the ``giveaway_credit``
    switch is missing or off (a missing row reads as off); the giver is the claim's own
    picker; the giver's account is deleted; the giver's email deleted an account that held a
    giveaway credit (D542 (5)); or the giver has already earned one
    (``uq_credits_giveaway_per_user`` refuses the insert). The insert runs in a savepoint,
    so a lost race rolls back only the savepoint and the surrounding completion is
    untouched. Never commits.
    """
    switch = db.get(ProgramSwitch, GIVEAWAY_CREDIT_SWITCH)
    if switch is None or not switch.enabled:
        _skip(claim, giver, "switch_off")
        return None
    if claim.picker_id == giver.id:
        _skip(claim, giver, "self_claim")
        return None
    if giver.deleted_at is not None:
        _skip(claim, giver, "giver_deleted")
        return None
    # D542 (5): an email that deleted an account holding a giveaway credit earns no second one.
    earned_before_deletion = (
        db.query(DeletedEmailFingerprint.id)
        .filter(
            DeletedEmailFingerprint.email_hash == email_fingerprint(giver.email),
            DeletedEmailFingerprint.had_giveaway_credit.is_(True),
        )
        .first()
    )
    if earned_before_deletion is not None:
        _skip(claim, giver, "earned_before_deletion")
        return None

    now = datetime.now(timezone.utc)
    credit = Credit(
        user_id=giver.id,
        kind="giveaway",
        source_claim_id=claim.id,
        earned_at=now,
        expires_at=now + GIVEAWAY_CREDIT_LIFETIME,
    )
    try:
        with db.begin_nested():
            db.add(credit)
            db.flush()
    except IntegrityError:
        # Once per person: the partial unique index refused a second giveaway credit.
        # The savepoint alone is rolled back; the completion carries on.
        _skip(claim, giver, "already_earned")
        return None

    logger.info(
        json.dumps(
            {
                "event": "giveaway_credit_awarded",
                "claim_id": str(claim.id),
                "giver_id": str(giver.id),
                "credit_id": str(credit.id),
            }
        )
    )
    return credit


def pending_device_check_credit(db: Session, user_id: UUID) -> Credit | None:
    """The user's giveaway or invite credit still waiting for its iPhone check (D542 (4),
    D549 C5): unused, neither passed nor refused. None when there is nothing to check. With
    both kinds pending the giveaway credit comes first; the next app open checks the other."""
    return (
        db.query(Credit)
        .filter(
            Credit.user_id == user_id,
            Credit.kind.in_(DEVICE_CHECKED_CREDIT_KINDS),
            Credit.used_at.is_(None),
            Credit.device_checked_at.is_(None),
            Credit.device_check_refused_at.is_(None),
        )
        .order_by(Credit.kind.asc(), Credit.earned_at.asc())
        .first()
    )


def record_device_refusal_alert(
    db: Session, *, user_id: UUID, credit_id: UUID, kind: str = DEVICE_REFUSAL_KIND,
) -> None:
    """One Control Center abuse alert for a giveaway credit refused because its iPhone already
    earned one (D543 (5)), or, with ``kind=INVITE_DEVICE_REFUSAL_KIND``, an invite credit
    refused because its iPhone already used a friend's code (D549 C5). Same shape as
    api_abuse.record_api_signal: commits its own row, never raises; a second write for the
    same credit is refused by the unique source id."""
    source_id = f"devicecheck-refused:{credit_id}"
    try:
        db.add(
            WatcherEvent(
                family=DEVICE_REFUSAL_FAMILY,
                kind=kind,
                severity=DEVICE_REFUSAL_SEVERITY,
                who=str(user_id)[:200],
                ref=str(credit_id)[:500],
                source=DEVICE_REFUSAL_SOURCE,
                source_id=source_id[:120],
                payload={"credit_id": str(credit_id), "user_id": str(user_id)},
                state="pending",
                raised_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()  # already recorded for this credit
    except Exception:
        db.rollback()
        logger.exception("device_refusal_alert_write_failed source_id=%s", source_id)

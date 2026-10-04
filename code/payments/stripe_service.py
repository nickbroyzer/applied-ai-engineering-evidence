"""
Stripe PaymentIntent operations for per-claim authorization-without-capture (D7).

- create_payment_intent: creates a manual-capture PaymentIntent for CLAIM_AMOUNT_CENTS
  and stores its id on the claim. Moving claim status from pending_payment to
  authorized (and setting authorized_at) happens when the PaymentIntent is confirmed
  and requires capture — typically in the payment_intent.* webhook handler (layer 6c),
  not in this function.

- capture_payment_intent: captures the authorized hold after pickup; sets captured_at
  synchronously; transitions claim to completed. D539 (1): a completion covered by a
  reserved Zelbi credit RELEASES the hold instead (captured_at stays null, the credit is
  spent). D548 extends the release to no_show (a giver's report or a late cancel) and
  post_window: a pickup that starts with a credit never charges $2; the credit is used up.

- cancel_payment_intent: cancels an uncaptured PaymentIntent (no Refund). Claim status
  is updated by the caller; this function only calls Stripe and logs.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Claim, Credit, User, WatcherEvent

logger = logging.getLogger(__name__)

# LOCKED per D7 (10-implementation-plan.md decision D7)
CLAIM_AMOUNT_CENTS = 200
CLAIM_CURRENCY = "usd"

_CAPTURE_REASONS = ("pickup_completed", "no_show", "post_window")

# D539 step 3 (slice 2): the PaymentIntent metadata key written just before Zelbi releases
# a hold because a credit covered the completion. Its value is the claim id. A canceled
# intent carrying this mark is OUR release; one without it is Stripe's own cancel (hold
# expiry, auto-void) and must never be read as a covered completion.
CREDIT_RELEASE_METADATA_KEY = "zelbi_credit_release"


class StripeServiceError(Exception):
    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


def _is_stripe_backend_error(exc: BaseException) -> bool:
    return type(exc).__module__.startswith("stripe")


# A PaymentIntent id Stripe actually issued is "pi_" followed by 24 or more
# alphanumeric characters. Seeded and reproduction rows carry hand-written
# references that cannot match this, and those never had a hold behind them.
_REAL_PI_RE = re.compile(r"^pi_[A-Za-z0-9]{24,}$")


def is_synthetic_payment_intent_id(pid: str | None) -> bool:
    """True when `pid` cannot be an id Stripe issued, so no hold can exist behind it."""
    return not bool(pid) or _REAL_PI_RE.match(pid) is None


def _configure_stripe() -> None:
    if not (settings.stripe_api_key or "").strip():
        raise StripeServiceError("Stripe is not configured (stripe_api_key is empty)")


def _stripe_code_and_message(exc: BaseException) -> tuple[str | None, str]:
    if _is_stripe_backend_error(exc):
        code = getattr(exc, "code", None)
        if not isinstance(code, str):
            code = str(code) if code is not None else None
        message = (
            getattr(exc, "user_message", None)
            or getattr(exc, "message", None)
            or str(exc)
        )
        return (code, message)
    return (None, str(exc))


def _log_stripe_service_failure(
    event: str,
    claim_id: UUID,
    start_time: float,
    exc: StripeServiceError,
) -> None:
    """Single failure log: ai_service-style, with Stripe code/message when the cause is Stripe."""
    out: dict[str, Any] = {
        "event": event,
        "claim_id": str(claim_id),
        "latency_ms": int((time.perf_counter() - start_time) * 1000),
        "error_type": type(exc).__name__,
    }
    cause = exc.__cause__
    if cause is not None and _is_stripe_backend_error(cause):
        code, message = _stripe_code_and_message(cause)
        out["stripe_code"] = code
        out["message"] = message
    else:
        out["error_message"] = str(exc)
    logger.error(json.dumps(out))


def ensure_stripe_customer(user: User, db: Session) -> str:
    """
    Return the Stripe Customer id for `user`, creating one if absent (D66).

    Idempotency-keyed on the user id so retries don't create duplicates.
    On create, writes user.stripe_customer_id and flushes; caller controls commit.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    _configure_stripe()
    stripe.api_key = settings.stripe_api_key

    try:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
            idempotency_key=f"customer_{user.id}",
        )
    except Exception as e:
        if not _is_stripe_backend_error(e):
            raise
        _, message = _stripe_code_and_message(e)
        raise StripeServiceError(
            f"Stripe Customer.create failed: {message}",
        ) from e

    user.stripe_customer_id = customer.id
    db.add(user)
    db.flush()
    return customer.id


def _field(obj: Any, key: str) -> Any:
    """Read `key` off `obj`, supporting both dict-style and attribute-style access
    (the Stripe SDK returns objects that support both)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _hold_expiry_and_card_fingerprint_from_payment_intent(
    payment_intent: stripe.PaymentIntent,
) -> tuple[datetime | None, str | None]:
    """
    Read Stripe's per-hold capture_before AND the card fingerprint (D542 (3)) from the
    PaymentIntent's latest charge, in one charge read. capture_before and fingerprint both
    live at charge.payment_method_details.card, not at the top level of the charge —
    retrieve/expand as needed. Either value is None when the charge does not carry it; a
    missing fingerprint is never a failure.
    """
    stripe.api_key = settings.stripe_api_key

    def _from_charge(charge: Any) -> tuple[datetime | None, str | None]:
        if charge is None or isinstance(charge, str):
            return (None, None)
        pmd = _field(charge, "payment_method_details")
        card = _field(pmd, "card")
        fingerprint = _field(card, "fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            fingerprint = None
        capture_before = _field(card, "capture_before")
        if not isinstance(capture_before, (int, float)) or isinstance(capture_before, bool):
            logger.warning(
                json.dumps(
                    {
                        "event": "stripe_capture_before_missing",
                        "payment_intent_id": _field(payment_intent, "id"),
                        "charge_id": _field(charge, "id"),
                    }
                )
            )
            return (None, fingerprint)
        return (datetime.fromtimestamp(int(capture_before), tz=timezone.utc), fingerprint)

    charge = _field(payment_intent, "latest_charge")
    if isinstance(charge, str):
        try:
            charge = stripe.Charge.retrieve(charge)
        except Exception as exc:
            logger.warning(
                json.dumps(
                    {
                        "event": "stripe_hold_expiry_lookup_failed",
                        "payment_intent_id": _field(payment_intent, "id"),
                        "error": str(exc),
                    }
                )
            )
            return (None, None)
        return _from_charge(charge)

    expiry, fingerprint = _from_charge(charge)
    if expiry is not None:
        return (expiry, fingerprint)
    if charge is None:
        return (None, None)

    try:
        expanded = stripe.PaymentIntent.retrieve(
            _field(payment_intent, "id"),
            expand=["latest_charge"],
        )
    except Exception as exc:
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_hold_expiry_lookup_failed",
                    "payment_intent_id": _field(payment_intent, "id"),
                    "error": str(exc),
                }
            )
        )
        return (None, fingerprint)

    expanded_charge = _field(expanded, "latest_charge")
    if isinstance(expanded_charge, str):
        try:
            expanded_charge = stripe.Charge.retrieve(expanded_charge)
        except Exception as exc:
            logger.warning(
                json.dumps(
                    {
                        "event": "stripe_hold_expiry_lookup_failed",
                        "payment_intent_id": _field(payment_intent, "id"),
                        "error": str(exc),
                    }
                )
            )
            return (None, fingerprint)
    expiry, expanded_fingerprint = _from_charge(expanded_charge)
    return (expiry, expanded_fingerprint or fingerprint)


# An intent in one of these states never held money and never will: the pay tap may
# replace it with a fresh one (D549, survey A2). requires_capture (a live hold) and
# every later state still refuse a second intent on the claim.
_REPLACEABLE_PI_STATUSES = ("requires_payment_method", "requires_confirmation", "canceled")


def retrieve_payment_method(payment_method_id: str) -> stripe.PaymentMethod:
    """Read a PaymentMethod from Stripe. Raises StripeServiceError on any failure so the
    caller answers 502 rather than leaking a Stripe message."""
    _configure_stripe()
    stripe.api_key = settings.stripe_api_key
    try:
        return stripe.PaymentMethod.retrieve(payment_method_id)
    except Exception as e:
        if not _is_stripe_backend_error(e):
            raise
        _, message = _stripe_code_and_message(e)
        raise StripeServiceError(
            f"Stripe PaymentMethod.retrieve failed: {message}",
        ) from e


def create_payment_intent(
    claim_id: UUID,
    picker_user_id: UUID,
    db: Session,
    payment_method_id: str | None = None,
) -> stripe.PaymentIntent:
    """
    Create a PaymentIntent with capture_method='manual'. Per-hold auth expiry comes from
    Stripe capture_before on the charge (card-brand dependent; never assume a fixed day count).
    Store stripe_payment_intent_id on the claim. Does not move the claim to authorized; the
    webhook (or client reconciliation) should when the intent reaches requires_capture /
    card is authorized.

    D549 (survey A2): with payment_method_id, the intent is created at the pay tap for the
    card the picker chose, and the idempotency key carries the attempt — the same request
    retried returns the same intent, while a new attempt after a dead intent gets a new
    one. A dead intent already on the claim (requires_payment_method, requires_confirmation
    or canceled) is cancelled and replaced; any other state still refuses.
    """
    start_time = time.perf_counter()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise StripeServiceError("Claim not found")
        if claim.picker_id != picker_user_id:
            raise StripeServiceError("Picker does not own this claim")
        if claim.status != "pending_payment":
            raise StripeServiceError("Claim must be pending_payment to start payment")

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key

        replaced_pid: str | None = None
        if claim.stripe_payment_intent_id:
            existing_pid = claim.stripe_payment_intent_id
            try:
                existing = stripe.PaymentIntent.retrieve(existing_pid)
            except Exception as e:
                if not _is_stripe_backend_error(e):
                    raise
                _, message = _stripe_code_and_message(e)
                raise StripeServiceError(
                    f"Stripe PaymentIntent.retrieve failed: {message}",
                ) from e
            if existing.status not in _REPLACEABLE_PI_STATUSES:
                raise StripeServiceError("Claim already has a PaymentIntent")
            if existing.status != "canceled":
                cancel_payment_intent(claim_id, "replaced_at_pay_tap", db)
            replaced_pid = existing_pid
            claim.stripe_payment_intent_id = None
            db.add(claim)
            db.flush()
            logger.info(
                json.dumps(
                    {
                        "event": "stripe_create_pi_replacing_dead_intent",
                        "claim_id": str(claim_id),
                        "replaced_payment_intent_id": replaced_pid,
                        "replaced_status": existing.status,
                    }
                )
            )

        picker = db.get(User, picker_user_id)
        if picker is None:
            raise StripeServiceError("Picker user not found")
        customer_id = ensure_stripe_customer(picker, db)

        if payment_method_id is not None:
            idempotency_key = (
                f"pi_claim_{claim_id}_{payment_method_id}_{replaced_pid or 'first'}"
            )
        else:
            idempotency_key = f"pi_claim_{claim_id}"
        create_kwargs: dict = {}
        if payment_method_id is not None:
            create_kwargs["payment_method"] = payment_method_id

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=CLAIM_AMOUNT_CENTS,
                currency=CLAIM_CURRENCY,
                capture_method="manual",
                customer=customer_id,
                setup_future_usage="off_session",
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                idempotency_key=idempotency_key,
                metadata={
                    "claim_id": str(claim_id),
                    "listing_id": str(claim.listing_id),
                    "picker_id": str(picker_user_id),
                },
                **create_kwargs,
            )
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe PaymentIntent.create failed: {message}",
            ) from e

        claim.stripe_payment_intent_id = payment_intent.id
        db.add(claim)
        db.flush()

        logger.info(
            json.dumps(
                {
                    "event": "stripe_create_pi_ok",
                    "claim_id": str(claim_id),
                    "payment_intent_id": payment_intent.id,
                    "status": payment_intent.status,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                }
            )
        )
        return payment_intent
    except StripeServiceError as exc:
        _log_stripe_service_failure(
            "stripe_create_pi_failure", claim_id, start_time, exc
        )
        raise


_REUSABLE_PI_STATUSES = ("requires_payment_method", "requires_confirmation", "requires_action")


def get_reusable_client_secret(claim: Claim) -> str | None:
    """Return the client secret of a claim's existing PaymentIntent when it can
    still be confirmed, else None. Mirrors the retrieve already used by the
    card_declined branch in claims.py."""
    pid = claim.stripe_payment_intent_id
    if not pid:
        return None
    try:
        _configure_stripe()
        stripe.api_key = settings.stripe_api_key
        pi = stripe.PaymentIntent.retrieve(pid)
    except Exception:
        return None
    if pi.status in _REUSABLE_PI_STATUSES:
        return pi.client_secret
    return None


def retrieve_payment_intent_status(pid: str | None) -> str | None:
    """The PaymentIntent's status exactly as Stripe reports it — read only.

    None when the id cannot be one Stripe issued (no read is made) or when the read
    fails for any reason; callers show "not read" rather than guess."""
    if is_synthetic_payment_intent_id(pid):
        return None
    try:
        _configure_stripe()
        stripe.api_key = settings.stripe_api_key
        pi = stripe.PaymentIntent.retrieve(pid)
    except Exception:
        return None
    value = getattr(pi, "status", None)
    return value if isinstance(value, str) else None


def _apply_capture_outcome(claim: Claim, reason: str, now: datetime) -> None:
    """Write the claim's captured state for `reason`. Shared by the normal capture
    path and the already-captured reconciliation path so both land identical rows."""
    claim.captured_at = now
    if reason == "pickup_completed":
        claim.status = "completed"
        claim.completed_at = now
    elif reason == "no_show":
        claim.status = "no_show"
        claim.no_show_at = now
    elif reason == "post_window":
        # D58 LOCKED — auto_captured is sweeper-only; listing-status sync
        # to 'completed' is the caller's responsibility (sweeper job).
        claim.status = "auto_captured"
        claim.auto_captured_at = now


def _apply_release_outcome(claim: Claim, db: Session, reason: str, now: datetime) -> None:
    """D539 (1), D548: a pickup covered by a Zelbi credit that ended by `reason`. The hold
    was released, so the claim's status is written the way _apply_capture_outcome writes
    it for the same reason, with captured_at left null, and the reserved credit is spent on
    this claim in the same flush. Shared by the release path and the lost-write
    reconciliation so both land identical rows. Never touches captured_at: null still
    means no money moved, whatever the status says."""
    if reason == "pickup_completed":
        claim.status = "completed"
        claim.completed_at = now
    elif reason == "no_show":
        claim.status = "no_show"
        claim.no_show_at = now
    elif reason == "post_window":
        claim.status = "auto_captured"
        claim.auto_captured_at = now
    db.add(claim)
    credit = db.get(Credit, claim.credit_id) if claim.credit_id is not None else None
    if credit is not None:
        credit.used_at = now
        credit.used_claim_id = claim.id
        db.add(credit)
    db.flush()


# D542 (3), D549 (C4): the credit kinds whose spend is tied to one card.
CARD_STAMPED_CREDIT_KINDS = ("giveaway", "invite")


def _metadata_value(payment_intent: Any, key: str) -> str | None:
    """Read one metadata string off a PaymentIntent, whether the SDK object or a plain
    dict. Anything that is not a string reads as absent."""
    metadata = _field(payment_intent, "metadata")
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        value = metadata.get(key)
    else:
        value = getattr(metadata, key, None)
    return value if isinstance(value, str) else None


def _stamp_credit_card(db: Session, claim: Claim) -> bool:
    """D542 (3), D549 (C4): tie the reserved GIVEAWAY or INVITE credit to the card that paid
    this claim's hold. Writes credit.used_card_fingerprint = claim.card_fingerprint inside a
    savepoint. True when the stamp landed or the rule does not apply (no reserved credit, a
    referral credit, or a claim with no fingerprint). False when uq_credits_giveaway_card or
    uq_credits_invite_card refused it: another person's credit of that kind was already
    spent on this card. Only the savepoint is rolled back; the caller decides what the
    refusal means and logs it."""
    credit = db.get(Credit, claim.credit_id) if claim.credit_id is not None else None
    if credit is None or credit.kind not in CARD_STAMPED_CREDIT_KINDS or not claim.card_fingerprint:
        return True
    try:
        with db.begin_nested():
            credit.used_card_fingerprint = claim.card_fingerprint
            db.flush()
    except IntegrityError:
        db.expire(credit, ["used_card_fingerprint"])
        return False
    return True


# D548 addendum (c): a card conflict found at completion is a Control Center alert, written
# to watcher_events the way credit_service.record_device_refusal_alert does, but inside the
# caller's transaction (a savepoint), never committing on its own.
CARD_CONFLICT_ALERT_FAMILY = "account"
CARD_CONFLICT_ALERT_KIND = "giveaway_credit_card_conflict_at_release"
CARD_CONFLICT_ALERT_SEVERITY = 4
CARD_CONFLICT_ALERT_SOURCE = "zelbi"


def _record_card_conflict_alert(db: Session, claim: Claim, pid: str, event: str) -> None:
    """One alert per claim, in its own savepoint; a second write for the same claim hits
    the unique source id and is skipped quietly. Never commits."""
    source_id = f"credit-card-conflict:{claim.id}"
    try:
        with db.begin_nested():
            db.add(
                WatcherEvent(
                    family=CARD_CONFLICT_ALERT_FAMILY,
                    kind=CARD_CONFLICT_ALERT_KIND,
                    severity=CARD_CONFLICT_ALERT_SEVERITY,
                    who=str(claim.picker_id)[:200],
                    ref=str(claim.id)[:500],
                    source=CARD_CONFLICT_ALERT_SOURCE,
                    source_id=source_id[:120],
                    payload={
                        "claim_id": str(claim.id),
                        "credit_id": str(claim.credit_id) if claim.credit_id else None,
                        "payment_intent_id": pid,
                        "event": event,
                    },
                    state="pending",
                    raised_at=datetime.now(timezone.utc),
                )
            )
            db.flush()
    except IntegrityError:
        pass  # already recorded for this claim


def _stamp_card_or_log(db: Session, claim: Claim, pid: str, *, event: str) -> None:
    """D548 addendum (c): the card decision was made at the pay tap
    (claims.create_claim_payment_intent); completion only stamps. Stamp the card on the
    reserved giveaway or invite credit when it fits. On a conflict, which can only be a race between
    two pay taps on one card, leave used_card_fingerprint null, log it at error level under
    `event`, and record a Control Center alert inside the caller's transaction. The release
    goes ahead either way: a person who saw $0.00 is never charged. Shared by the release
    branch and the lost-write adopt so both land identical rows."""
    if _stamp_credit_card(db, claim):
        return
    logger.error(
        json.dumps(
            {
                "event": event,
                "claim_id": str(claim.id),
                "credit_id": str(claim.credit_id),
                "payment_intent_id": pid,
                "note": "released; used_card_fingerprint left null",
            }
        )
    )
    _record_card_conflict_alert(db, claim, pid, event)


def capture_payment_intent(
    claim_id: UUID,
    db: Session,
    reason: str = "pickup_completed",
) -> stripe.PaymentIntent | None:
    """
    Capture the full authorized amount. If amount_capturable is below CLAIM_AMOUNT_CENTS,
    log and return (expiration sweeper handles; no partial capture, no raise). On success,
    sets captured_at and branches the claim status write per `reason` (D24 res 2 + D58/D59):
      - "pickup_completed": status="completed", completed_at=now
      - "no_show": status="no_show", no_show_at=now
      - "post_window": status="auto_captured", auto_captured_at=now (D58)
    D539 (1): a claim with a reserved credit (claim.credit_id) and a hold still
    requires_capture releases the hold instead: the status write above for the same
    reason, captured_at left null, the credit's used_at/used_claim_id set. D548 extends
    the release from "pickup_completed" to "no_show" and "post_window": a pickup that
    starts with a credit never charges $2, and losing the credit is the penalty. The
    PaymentIntent is returned in that case too, never None, so callers go on to write the
    listing, trust events and counters as for a charged ending.
    D548 addendum (c): the card decision for a GIVEAWAY credit is made at the pay tap
    (claims.create_claim_payment_intent refuses the credit before any hold exists);
    completion only stamps the card on the credit. A conflict at the stamp is logged at
    error level with a Control Center alert, the field stays null, and the release goes
    ahead: nobody who saw $0.00 is charged.
    """
    if reason not in _CAPTURE_REASONS:
        raise ValueError(
            f"capture_payment_intent: invalid reason {reason!r}; "
            f"expected one of {_CAPTURE_REASONS}"
        )
    start_time = time.perf_counter()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise StripeServiceError("Claim not found")
        if not claim.stripe_payment_intent_id:
            raise StripeServiceError("Claim has no PaymentIntent to capture")
        if claim.status not in ("authorized", "pickup_scheduled"):
            raise StripeServiceError(
                "Claim must be authorized or pickup_scheduled to capture",
            )

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key
        pid = claim.stripe_payment_intent_id

        try:
            current = stripe.PaymentIntent.retrieve(pid)
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe PaymentIntent.retrieve failed: {message}",
            ) from e

        # a3 RECONCILIATION — Stripe already holds this claim's money while the claim
        # row does not record it: a capture whose local write was lost after the money
        # moved. Adopt Stripe's record rather than re-capturing. Without this branch the
        # next run reads zero capturable and reports an auto-void that never happened,
        # every run, forever. Sits ahead of the underfunded branch deliberately.
        pi_status = getattr(current, "status", None)
        amount_received = getattr(current, "amount_received", None)
        if (
            pi_status == "succeeded"
            and amount_received is not None
            and int(amount_received) >= CLAIM_AMOUNT_CENTS
        ):
            now = datetime.now(timezone.utc)
            _apply_capture_outcome(claim, reason, now)
            db.add(claim)
            db.flush()
            logger.error(
                json.dumps(
                    {
                        "event": "stripe_capture_divergence_already_captured",
                        "claim_id": str(claim_id),
                        "payment_intent_id": pid,
                        "amount_received": int(amount_received),
                        "reason": reason,
                        "note": "captured_at set to reconciliation time, not the original capture time",
                    }
                )
            )
            return current

        # D539 (1) LOST-WRITE ADOPT — the mirror of a3 for a credit release: the intent
        # is canceled AND carries our release mark for this claim, so Zelbi released the
        # hold for a covered completion but the local write was lost. Adopt the release.
        # Reachable from EVERY caller, the sweeper included: without it the sweeper would
        # read zero capturable on a still-live claim and report an auto-void every run,
        # forever. A canceled intent WITHOUT the mark is Stripe's own cancel and falls
        # through to today's handling unchanged.
        if (
            pi_status == "canceled"
            and _metadata_value(current, CREDIT_RELEASE_METADATA_KEY) == str(claim_id)
        ):
            now = datetime.now(timezone.utc)
            _apply_release_outcome(claim, db, reason, now)
            _stamp_card_or_log(db, claim, pid, event="giveaway_credit_card_conflict_on_adopt")
            logger.error(
                json.dumps(
                    {
                        "event": "stripe_release_divergence_already_released",
                        "claim_id": str(claim_id),
                        "payment_intent_id": pid,
                        "credit_id": str(claim.credit_id) if claim.credit_id else None,
                        "reason": reason,
                        "note": "completed_at set to reconciliation time, not the original release time",
                    }
                )
            )
            return current

        # D539 (1) RELEASE — a pickup covered by a reserved credit releases the hold
        # instead of charging it. D548 extends this from a completion to no_show and
        # post_window: every reason releases, and the credit is used up. The mark is
        # written to the intent BEFORE the cancel so a lost local write is recoverable
        # (adopt above) and Stripe's own expiries can never be mistaken for our release.
        # D548 addendum (c): the card decision was made at the pay tap; here the card is
        # only stamped on the giveaway credit (the index guard and the record for
        # _cards_of). A conflict is logged and alerted and the release still goes ahead:
        # the card rule never makes this branch fall through to a capture.
        if claim.credit_id is not None and pi_status == "requires_capture":
            _stamp_card_or_log(db, claim, pid, event="giveaway_credit_card_conflict_at_release")
            try:
                stripe.PaymentIntent.modify(
                    pid, metadata={CREDIT_RELEASE_METADATA_KEY: str(claim_id)},
                )
            except Exception as e:
                if not _is_stripe_backend_error(e):
                    raise
                _, message = _stripe_code_and_message(e)
                raise StripeServiceError(
                    f"Stripe PaymentIntent.modify failed: {message}",
                ) from e

            # Direct call on purpose. cancel_payment_intent swallows
            # payment_intent_unexpected_state as success, and that is also the error for
            # an intent captured between our retrieve and our cancel (the sweeper racing
            # this route); going through it would record "free by credit" on money taken.
            try:
                released = stripe.PaymentIntent.cancel(pid)
            except Exception as e:
                if not _is_stripe_backend_error(e):
                    raise
                code, message = _stripe_code_and_message(e)
                if code != "payment_intent_unexpected_state":
                    raise StripeServiceError(
                        f"Stripe PaymentIntent.cancel failed: {message}",
                    ) from e
                # The intent moved under us. Re-read: if it is succeeded the money moved
                # and the claim is charged with the credit unused (a3, never refund);
                # anything else is unknown and must not be written either way.
                try:
                    again = stripe.PaymentIntent.retrieve(pid)
                except Exception as e2:
                    if not _is_stripe_backend_error(e2):
                        raise
                    _, message2 = _stripe_code_and_message(e2)
                    raise StripeServiceError(
                        f"Stripe PaymentIntent.retrieve failed: {message2}",
                    ) from e2
                if getattr(again, "status", None) == "succeeded":
                    now = datetime.now(timezone.utc)
                    _apply_capture_outcome(claim, reason, now)
                    db.add(claim)
                    # The credit stays unused, so the card stamp written before the
                    # release attempt comes off: an unused credit never holds a card.
                    unused = db.get(Credit, claim.credit_id) if claim.credit_id else None
                    if unused is not None and unused.used_at is None:
                        unused.used_card_fingerprint = None
                    db.flush()
                    again_received = getattr(again, "amount_received", None)
                    logger.error(
                        json.dumps(
                            {
                                "event": "stripe_capture_divergence_already_captured",
                                "claim_id": str(claim_id),
                                "payment_intent_id": pid,
                                "amount_received": (
                                    int(again_received)
                                    if isinstance(again_received, int) else None
                                ),
                                "reason": reason,
                                "note": "release lost a race with a capture; charged, credit unused",
                            }
                        )
                    )
                    return again
                raise StripeServiceError(
                    f"Stripe PaymentIntent.cancel failed: {message}",
                    code=code,
                ) from e

            now = datetime.now(timezone.utc)
            _apply_release_outcome(claim, db, reason, now)
            logger.info(
                json.dumps(
                    {
                        "event": "stripe_release_ok",
                        "claim_id": str(claim_id),
                        "payment_intent_id": pid,
                        "credit_id": str(claim.credit_id),
                        "latency_ms": int((time.perf_counter() - start_time) * 1000),
                    }
                )
            )
            return released

        capturable = getattr(current, "amount_capturable", None)
        if capturable is not None and int(capturable) < CLAIM_AMOUNT_CENTS:
            payload = {
                "event": "stripe_capture_skipped_underfunded",
                "claim_id": str(claim_id),
                "payment_intent_id": pid,
                "amount_capturable": int(capturable),
                "expected_cents": CLAIM_AMOUNT_CENTS,
            }
            if reason == "post_window":
                # D59 LOCKED — post_window underfunded means Stripe likely auto-voided
                # the authorization before the sweeper got to it. Log at error level
                # with the dedicated event name so Railway log monitoring catches it.
                logger.error(
                    json.dumps(
                        {
                            **payload,
                            "event": "post_window_capture_underfunded_likely_stripe_autovoid",
                        }
                    )
                )
            else:
                logger.warning(json.dumps(payload))
            return None

        try:
            payment_intent = stripe.PaymentIntent.capture(pid, amount_to_capture=CLAIM_AMOUNT_CENTS)
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe PaymentIntent.capture failed: {message}",
            ) from e

        now = datetime.now(timezone.utc)
        _apply_capture_outcome(claim, reason, now)
        db.add(claim)
        db.flush()

        logger.info(
            json.dumps(
                {
                    "event": "stripe_capture_ok",
                    "claim_id": str(claim_id),
                    "payment_intent_id": payment_intent.id,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                }
            )
        )
        return payment_intent
    except StripeServiceError as exc:
        _log_stripe_service_failure(
            "stripe_capture_failure", claim_id, start_time, exc
        )
        raise


def refund_captured_claim(claim_id: UUID, db: Session) -> None:
    """
    Refund the FULL captured fee on a claim (D-entry pending, supersedes D61's
    manual-dashboard remedy — Nick 2026-08-11). Used by admin dispute resolution
    when the picker is upheld. Idempotent two ways: a claim already carrying
    refund_id returns without calling Stripe, and the Stripe call itself carries
    an idempotency key derived from the claim id, so a retry after a lost
    response cannot refund twice. Writes refund_id and refunded_at; does NOT
    commit — the caller owns the transaction so a failed refund fails the whole
    resolution rather than leaving a resolved dispute with no refund.
    Raises StripeServiceError on any failure, including a claim with no capture
    to refund — the caller must not treat those as success.
    """
    start_time = time.perf_counter()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise StripeServiceError("Claim not found")
        if claim.refund_id:
            logger.info(
                json.dumps(
                    {
                        "event": "stripe_refund_idempotent_skip",
                        "claim_id": str(claim_id),
                        "refund_id": claim.refund_id,
                    }
                )
            )
            return
        if claim.captured_at is None:
            raise StripeServiceError("Claim has no captured payment to refund")
        pid = claim.stripe_payment_intent_id
        if not pid:
            raise StripeServiceError("Claim has no PaymentIntent to refund")

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key

        try:
            refund = stripe.Refund.create(
                payment_intent=pid,
                idempotency_key=f"refund_claim_{claim_id}",
            )
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe Refund.create failed: {message}",
            ) from e

        claim.refund_id = refund.id
        claim.refunded_at = datetime.now(timezone.utc)
        db.add(claim)
        db.flush()

        logger.info(
            json.dumps(
                {
                    "event": "stripe_refund_ok",
                    "claim_id": str(claim_id),
                    "refund_id": refund.id,
                    "latency_ms": int((time.perf_counter() - start_time) * 1000),
                }
            )
        )
    except StripeServiceError as exc:
        _log_stripe_service_failure("stripe_refund_failure", claim_id, start_time, exc)
        raise


def cancel_payment_intent(claim_id: UUID, reason: str, db: Session) -> None:
    """
    Cancel an uncaptured PaymentIntent (no Refund / no Refund object). Idempotent if
    already canceled. reason is for logs only. Caller updates claim status to cancelled
    or no_show as appropriate.
    """
    start_time = time.perf_counter()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise StripeServiceError("Claim not found")
        pid = claim.stripe_payment_intent_id
        if not pid:
            logger.info(
                json.dumps(
                    {
                        "event": "stripe_cancel_skipped_no_pi",
                        "claim_id": str(claim_id),
                        "reason": reason,
                    }
                )
            )
            return

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key

        try:
            stripe.PaymentIntent.cancel(pid)
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            code, message = _stripe_code_and_message(e)
            mlow = (message or "").lower()
            # Idempotent: PI already canceled (Plan v1) or non-cancelable state
            if code == "payment_intent_unexpected_state" or (
                "already been canceled" in mlow or "already been cancelled" in mlow
            ):
                logger.debug(
                    json.dumps(
                        {
                            "event": "stripe_cancel_idempotent",
                            "claim_id": str(claim_id),
                            "payment_intent_id": pid,
                            "stripe_code": code,
                            "message": message,
                        }
                    )
                )
                return
            # resource_missing has two causes with opposite consequences: the id was
            # never real (safe — nothing to cancel), or the id is real but this API key
            # points at a different Stripe account (dangerous — a live hold would be
            # abandoned while the claim is written off). Only the first is forgiven, and
            # only when the id itself cannot be a Stripe id. Anything else raises with a
            # code the caller can act on.
            if code == "resource_missing":
                if is_synthetic_payment_intent_id(pid):
                    logger.info(
                        json.dumps(
                            {
                                "event": "stripe_cancel_synthetic_pi_forgiven",
                                "claim_id": str(claim_id),
                                "payment_intent_id": pid,
                                "message": message,
                            }
                        )
                    )
                    return
                raise StripeServiceError(
                    f"Stripe PaymentIntent.cancel failed: {message}",
                    code="resource_missing",
                ) from e
            raise StripeServiceError(
                f"Stripe PaymentIntent.cancel failed: {message}",
            ) from e

        logger.info(
            json.dumps(
                {
                    "event": "stripe_cancel_ok",
                    "claim_id": str(claim_id),
                    "payment_intent_id": pid,
                    "reason": reason,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                }
            )
        )
    except StripeServiceError as exc:
        _log_stripe_service_failure(
            "stripe_cancel_failure", claim_id, start_time, exc
        )
        raise

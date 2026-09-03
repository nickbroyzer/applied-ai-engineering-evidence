"""
Stripe PaymentIntent operations for per-claim authorization-without-capture (D7).

- create_payment_intent: creates a manual-capture PaymentIntent for CLAIM_AMOUNT_CENTS
  and stores its id on the claim. Moving claim status from pending_payment to
  authorized (and setting authorized_at) happens when the PaymentIntent is confirmed
  and requires capture — typically in the payment_intent.* webhook handler (layer 6c),
  not in this function.

- capture_payment_intent: captures the authorized hold after pickup; sets captured_at
  synchronously; transitions claim to completed.

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
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Claim, User

logger = logging.getLogger(__name__)

# LOCKED per D7 (10-implementation-plan.md decision D7)
CLAIM_AMOUNT_CENTS = 200
CLAIM_CURRENCY = "usd"

_CAPTURE_REASONS = ("pickup_completed", "no_show", "post_window")


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


def _hold_expires_at_from_payment_intent(
    payment_intent: stripe.PaymentIntent,
) -> datetime | None:
    """
    Read Stripe's per-hold capture_before from the PaymentIntent's latest charge.
    capture_before lives at charge.payment_method_details.card.capture_before, not
    at the top level of the charge — retrieve/expand as needed.
    """
    stripe.api_key = settings.stripe_api_key

    def _from_charge(charge: Any) -> datetime | None:
        if charge is None or isinstance(charge, str):
            return None
        pmd = _field(charge, "payment_method_details")
        card = _field(pmd, "card")
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
            return None
        return datetime.fromtimestamp(int(capture_before), tz=timezone.utc)

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
            return None
        return _from_charge(charge)

    expiry = _from_charge(charge)
    if expiry is not None:
        return expiry
    if charge is None:
        return None

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
        return None

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
            return None
    return _from_charge(expanded_charge)


def create_payment_intent(claim_id: UUID, picker_user_id: UUID, db: Session) -> stripe.PaymentIntent:
    """
    Create a PaymentIntent with capture_method='manual'. Per-hold auth expiry comes from
    Stripe capture_before on the charge (card-brand dependent; never assume a fixed day count).
    Store stripe_payment_intent_id on the claim. Does not move the claim to authorized; the
    webhook (or client reconciliation) should when the intent reaches requires_capture /
    card is authorized.
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
        if claim.stripe_payment_intent_id:
            raise StripeServiceError("Claim already has a PaymentIntent")

        picker = db.get(User, picker_user_id)
        if picker is None:
            raise StripeServiceError("Picker user not found")
        customer_id = ensure_stripe_customer(picker, db)

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=CLAIM_AMOUNT_CENTS,
                currency=CLAIM_CURRENCY,
                capture_method="manual",
                customer=customer_id,
                setup_future_usage="off_session",
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                idempotency_key=f"pi_claim_{claim_id}",
                metadata={
                    "claim_id": str(claim_id),
                    "listing_id": str(claim.listing_id),
                    "picker_id": str(picker_user_id),
                },
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


def confirm_payment_intent_off_session(
    claim_id: UUID, picker_user_id: UUID, db: Session
) -> stripe.PaymentIntent:
    """
    Confirm an existing PaymentIntent off-session using the picker's saved default
    payment method. Returns the PaymentIntent on success. Raises StripeServiceError
    with code="card_declined" if the card is declined so the router can fall back to
    PaymentSheet; raises StripeServiceError (no code) for all other failures.
    """
    start_time = time.perf_counter()
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise StripeServiceError("Claim not found")
        if claim.picker_id != picker_user_id:
            raise StripeServiceError("Picker does not own this claim")
        if not claim.stripe_payment_intent_id:
            raise StripeServiceError("Claim has no PaymentIntent")

        picker = db.get(User, picker_user_id)
        if picker is None:
            raise StripeServiceError("Picker user not found")
        if not picker.stripe_customer_id:
            raise StripeServiceError("No saved payment method")

        _configure_stripe()
        stripe.api_key = settings.stripe_api_key

        try:
            customer = stripe.Customer.retrieve(
                picker.stripe_customer_id,
                expand=["invoice_settings.default_payment_method"],
            )
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe Customer.retrieve failed: {message}",
            ) from e

        raw_pm = customer.invoice_settings.default_payment_method
        if not raw_pm:
            raise StripeServiceError("No saved payment method")
        pm_id = raw_pm if isinstance(raw_pm, str) else raw_pm.id

        try:
            payment_intent = stripe.PaymentIntent.confirm(
                claim.stripe_payment_intent_id,
                payment_method=pm_id,
                off_session=True,
            )
        except stripe.error.CardError as e:
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Card declined: {message}",
                code="card_declined",
            ) from e
        except Exception as e:
            if not _is_stripe_backend_error(e):
                raise
            _, message = _stripe_code_and_message(e)
            raise StripeServiceError(
                f"Stripe PaymentIntent.confirm failed: {message}",
            ) from e

        logger.info(
            json.dumps(
                {
                    "event": "stripe_confirm_off_session_ok",
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
            "stripe_confirm_off_session_failure", claim_id, start_time, exc
        )
        raise


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

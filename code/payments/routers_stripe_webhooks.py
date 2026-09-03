import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import stripe
from fastapi import APIRouter, HTTPException, Request, status
from stripe.error import SignatureVerificationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Claim, Listing, Saved
from app.services.notification_service import send_push
from app.services.stripe_service import _hold_expires_at_from_payment_intent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stripe"])


def _find_claim_by_payment_intent(db: Session, payment_intent_id: str) -> Claim | None:
    return (
        db.query(Claim)
        .filter(Claim.stripe_payment_intent_id == payment_intent_id)
        .first()
    )


def _handle_amount_capturable_updated(db: Session, obj: dict[str, Any]) -> None:
    pi_id = obj.get("id")
    if not isinstance(pi_id, str):
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_webhook_pi_missing_id",
                    "handler": "amount_capturable_updated",
                }
            )
        )
        return

    claim = _find_claim_by_payment_intent(db, pi_id)
    if claim is None:
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_webhook_claim_not_found",
                    "payment_intent_id": pi_id,
                    "handler": "amount_capturable_updated",
                }
            )
        )
        return

    if claim.status != "pending_payment":
        logger.info(
            json.dumps(
                {
                    "event": "stripe_webhook_authorize_idempotent_skip",
                    "claim_id": str(claim.id),
                    "current_status": claim.status,
                    "payment_intent_id": pi_id,
                }
            )
        )
        return

    claim.status = "authorized"
    claim.authorized_at = datetime.now(timezone.utc)
    hold_expires_at = _hold_expires_at_from_payment_intent(obj)
    if hold_expires_at is not None:
        claim.hold_expires_at = hold_expires_at
    db.add(claim)
    listing = db.get(Listing, claim.listing_id)
    if listing is not None:
        listing.status = "claimed"
        listing.claimed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        json.dumps(
            {
                "event": "stripe_webhook_claim_authorized",
                "claim_id": str(claim.id),
                "payment_intent_id": pi_id,
            }
        )
    )
    if listing is None:
        logger.warning(json.dumps({
            "event": "stripe_webhook_authorize_push_skipped_no_listing",
            "claim_id": str(claim.id),
            "payment_intent_id": pi_id,
        }))
    else:
        try:
            send_push(
                db,
                listing.giver_id,
                # The title carries WHAT HAPPENED; the body carries WHAT TO DO and never
                # repeats it. Neither names the item or the picker: the row already shows the
                # item's photo, and a display name is whatever length that person chose, so a
                # title built around one truncates for some people and not others. Nick's
                # ruling 2026-08-29, amending 2026-08-28 — a line that cannot fit without an
                # ellipsis does not belong in a notification, and a line whose length depends
                # on user input cannot be shortened into fitting.
                "You have a new claim",
                "Choose how to hand it off",
                {"type": "claim_authorized", "claim_id": str(claim.id), "listing_id": str(listing.id)},
                "claim_authorized",
                claim.id,
            )
        except Exception:
            logger.exception("send_push_failed_claim_authorized")

        savers = (
            db.query(Saved)
            .filter(Saved.listing_id == listing.id, Saved.user_id != claim.picker_id)
            .all()
        )
        for saved in savers:
            push_title = "Beaten to the punch 🏃"
            push_body = f'"{listing.title}" found a new home. Plenty of free finds left to grab.'
            try:
                send_push(
                    db,
                    saved.user_id,
                    push_title,
                    push_body,
                    {"type": "saved_item_claimed", "listing_id": str(listing.id)},
                    "saved_item_claimed",
                    saved.id,
                )
            except Exception:
                logger.exception("send_push_failed_saved_item_claimed")
        if savers:
            db.commit()


def _handle_payment_intent_canceled(db: Session, obj: dict[str, Any]) -> None:
    pi_id = obj.get("id")
    if not isinstance(pi_id, str):
        return

    claim = _find_claim_by_payment_intent(db, pi_id)
    if claim is None:
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_webhook_claim_not_found",
                    "payment_intent_id": pi_id,
                    "handler": "payment_intent.canceled",
                }
            )
        )
        return

    # D62 + D70 LOCKED — backend-initiated cancels land claim.status='cancelled'
    # or 'no_show' BEFORE the webhook fires. If the webhook arrives and the claim
    # is still 'authorized' or 'pickup_scheduled' AND pickup_scheduled_at + 24h
    # is in the past, this means the sweeper failed to capture in time and Stripe
    # auto-voided the authorization. Money is gone; this is a system-health alarm,
    # not a recovery path. Log at error level with the dedicated event name so
    # Railway log-monitor scrapes it (no Sentry dependency in MVP per D70).
    if claim.status in ("authorized", "pickup_scheduled"):
        sched = claim.pickup_scheduled_at
        if sched is not None:
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if sched + timedelta(hours=24) < now:
                logger.error(
                    json.dumps(
                        {
                            "event": "stripe_autovoid_after_window",
                            "claim_id": str(claim.id),
                            "payment_intent_id": pi_id,
                            "pickup_scheduled_at": sched.isoformat(),
                            "now": now.isoformat(),
                        }
                    )
                )
                claim.status = "cancelled"
                db.add(claim)
                db.commit()
                return

    if claim.status not in ("cancelled", "no_show"):
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_webhook_pi_canceled_unexpected_claim_status",
                    "claim_id": str(claim.id),
                    "status": claim.status,
                    "payment_intent_id": pi_id,
                }
            )
        )


def _handle_payment_intent_payment_failed(db: Session, obj: dict[str, Any]) -> None:
    pi_id = obj.get("id")
    if not isinstance(pi_id, str):
        return

    last_error = obj.get("last_payment_error") or {}
    err_code = last_error.get("code")
    err_msg = last_error.get("message")
    decline_code = last_error.get("decline_code")

    claim = _find_claim_by_payment_intent(db, pi_id)
    if claim is None:
        logger.warning(
            json.dumps(
                {
                    "event": "stripe_webhook_payment_failed_unknown_claim",
                    "payment_intent_id": pi_id,
                    "stripe_code": err_code,
                    "decline_code": decline_code,
                    "message": err_msg,
                }
            )
        )
        return

    logger.warning(
        json.dumps(
            {
                "event": "stripe_webhook_payment_failed",
                "claim_id": str(claim.id),
                "payment_intent_id": pi_id,
                "stripe_code": err_code,
                "decline_code": decline_code,
                "message": err_msg,
            }
        )
    )
    try:
        send_push(
            db,
            claim.picker_id,
            "Payment failed",
            listing.title if (listing := db.get(Listing, claim.listing_id)) else "Your claim",
            {
                "type": "payment_failed",
                "claim_id": str(claim.id),
                "listing_id": str(claim.listing_id),
            },
            "payment_failed",
            claim.id,
        )
    except Exception:
        logger.exception("send_push_failed_payment_failed")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    secret = (settings.stripe_webhook_secret or "").strip()
    if not secret:
        logger.error(
            json.dumps({"event": "stripe_webhook_missing_secret_config"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            secret,
        )
    except ValueError:
        logger.warning(
            json.dumps({"event": "stripe_webhook_invalid_payload"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        ) from None
    except SignatureVerificationError:
        logger.warning(
            json.dumps({"event": "stripe_webhook_invalid_signature"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from None

    event_type = event.get("type")
    data_object = (event.get("data") or {}).get("object")
    if not isinstance(data_object, dict):
        data_object = {}

    db = SessionLocal()
    try:
        if event_type == "payment_intent.amount_capturable_updated":
            _handle_amount_capturable_updated(db, data_object)
        elif event_type == "payment_intent.canceled":
            _handle_payment_intent_canceled(db, data_object)
        elif event_type == "payment_intent.payment_failed":
            _handle_payment_intent_payment_failed(db, data_object)
        else:
            logger.debug(
                json.dumps(
                    {
                        "event": "stripe_webhook_unhandled_type",
                        "type": event_type,
                    }
                )
            )
    except Exception:
        db.rollback()
        logger.exception("stripe_webhook_handler_error type=%s", event_type)
        raise
    finally:
        db.close()

    return JSONResponse(status_code=200, content={"received": True})

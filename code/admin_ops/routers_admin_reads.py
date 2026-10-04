"""Admin reads — one endpoint per Control Center page list, filling the seed shapes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import AdminAction, Claim, Dispute, JobRun, Listing, Message, Report, Saved, User, ViewHistory, WatcherEvent
from app.routers.admin import require_admin
from app.services.admin_notes import notes_for
from app.services.scam_detection import rule_definition
from app.services.stripe_service import retrieve_payment_intent_status
from app.utils.cloudflare_r2 import sign_photo_url, sign_photo_urls
from app.utils.iso import iso_utc

router = APIRouter(tags=["admin-reads"])

_STATUS_TO_ST = {
    "authorized": "live",
    "pickup_scheduled": "live",
    "completed": "done",
    "auto_captured": "auto",
    "no_show": "ns",
    "cancelled": "rel",
}

_D_FIELDS = (
    "completed_at",
    "captured_at",
    "refunded_at",
    "no_show_at",
    "cancelled_at",
    "auto_captured_at",
    "authorized_at",
    "claimed_at",
)


def _iso(value: Any) -> str | None:
    return iso_utc(value)


def _claim_ref(claim_id: Any) -> str:
    return "ZLB-" + str(claim_id)[:6].upper()


def _listing_ref(listing_id: Any) -> str:
    return "L-" + str(listing_id)[:6].upper()


def _how(claim: Claim) -> str:
    if claim.refunded_at is not None:
        return "refund"
    if claim.status == "cancelled":
        return "cancel"
    if claim.status == "auto_captured":
        return "window"
    if claim.status == "completed" and claim.geofence_confirmed_at is not None:
        return "geo"
    if claim.status == "completed" and claim.completion_photo_url:
        return "photo"
    if claim.status == "completed":
        return "giver"
    return ""


def _latest_at(claim: Claim) -> Any:
    values = [getattr(claim, field) for field in _D_FIELDS]
    values = [v for v in values if v is not None]
    return max(values) if values else None


def _timeline(claim: Claim, dispute_filed_at: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    if claim.claimed_at is not None:
        note = "$2.00 authorized" if claim.authorized_at is not None else "awaiting payment"
        entries.append({"cls": "live", "title": "Claim placed", "at": _iso(claim.claimed_at), "note": note})

    if claim.proposed_times:
        entries.append(
            {
                "cls": "",
                "title": "Times proposed by the giver",
                "at": None,
                "note": f"{len(claim.proposed_times)} slots",
            }
        )

    if claim.pickup_scheduled_at is not None:
        entries.append(
            {
                "cls": "",
                "title": "Time selected by the picker",
                "at": _iso(claim.pickup_scheduled_at),
                "note": None,
            }
        )

    if claim.geofence_confirmed_at is not None:
        entries.append(
            {"cls": "live", "title": "Picker arrived", "at": _iso(claim.geofence_confirmed_at), "note": "inside the ring"}
        )

    # D548: money was taken only when captured_at is set. A closed claim with credit_id
    # set and captured_at null spent its credit and the hold was released.
    if claim.captured_at is not None:
        fee_note = "$2.00 captured"
    elif claim.credit_id is not None:
        fee_note = "credit used · hold released"
    else:
        fee_note = "no fee captured"

    if claim.completed_at is not None and claim.status == "completed":
        title = "Completed · pickup photo taken" if claim.completion_photo_url else "Completed · confirmed by the giver"
        entries.append({"cls": "done", "title": title, "at": _iso(claim.completed_at), "note": fee_note})

    if claim.auto_captured_at is not None:
        title = (
            "Captured by the sweeper · geofence arrival, no confirmation"
            if claim.geofence_confirmed_at is not None
            else "Captured by the sweeper · pickup window passed"
        )
        entries.append({"cls": "auto", "title": title, "at": _iso(claim.auto_captured_at), "note": fee_note})

    if claim.no_show_at is not None:
        entries.append(
            {"cls": "ns", "title": "Marked no-show by the giver", "at": _iso(claim.no_show_at), "note": fee_note}
        )

    if claim.cancelled_at is not None:
        entries.append(
            {"cls": "", "title": "Cancelled", "at": _iso(claim.cancelled_at), "note": "authorization released"}
        )

    if dispute_filed_at is not None:
        entries.append({"cls": "auto", "title": "Dispute filed", "at": _iso(dispute_filed_at), "note": None})

    if claim.refunded_at is not None:
        entries.append(
            {
                "cls": "",
                "title": "Refunded · dispute upheld for the picker",
                "at": _iso(claim.refunded_at),
                "note": None,
            }
        )

    if (
        claim.status in ("authorized", "pickup_scheduled")
        and claim.completed_at is None
        and claim.auto_captured_at is None
        and claim.no_show_at is None
        and claim.cancelled_at is None
    ):
        at = claim.pickup_scheduled_at or claim.hold_expires_at
        entries.append({"cls": "live", "title": "Waiting for the appointment", "at": _iso(at), "note": None})

    # Stable-sort by "at"; an entry with no timestamp shares its preceding
    # entry's sort key, so it keeps its place right after the one it follows.
    last_key: str | None = None
    keyed = []
    for entry in entries:
        if entry["at"] is not None:
            last_key = entry["at"]
        keyed.append((last_key, entry))

    keyed.sort(key=lambda pair: (pair[0] is None, pair[0]))
    return [entry for _, entry in keyed]


def _claim_row(
    claim: Claim,
    listing: Listing,
    names: dict[Any, str | None],
    dispute_filed_at: Any,
) -> dict[str, Any]:
    return {
        "id": str(claim.id),
        "ref": _claim_ref(claim.id),
        "item": listing.title,
        "picker": names.get(claim.picker_id),
        "giver": names.get(listing.giver_id),
        "st": _STATUS_TO_ST.get(claim.status, ""),
        "how": _how(claim),
        "d": _iso(_latest_at(claim)),
        "dispute": _iso(dispute_filed_at),
        "timeline": _timeline(claim, dispute_filed_at),
        "status": claim.status,
        "listing_id": str(listing.id),
        "picker_id": str(claim.picker_id),
        "giver_id": str(listing.giver_id),
    }


@router.get("/admin/claims")
def list_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    rows = (
        db.query(Claim, Listing)
        .join(Listing, Listing.id == Claim.listing_id)
        .filter(Claim.status != "pending_payment")
        .filter(~((Claim.status == "cancelled") & (Claim.authorized_at.is_(None))))
        .all()
    )

    user_ids = set()
    for claim, listing in rows:
        user_ids.add(claim.picker_id)
        user_ids.add(listing.giver_id)
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    claim_ids = [claim.id for claim, _ in rows]
    disputes = {
        d.claim_id: d.filed_at
        for d in db.query(Dispute).filter(Dispute.claim_id.in_(claim_ids)).all()
    }

    out = [_claim_row(claim, listing, names, disputes.get(claim.id)) for claim, listing in rows]

    out.sort(key=lambda row: row["d"] or "", reverse=True)
    return out


@router.get("/admin/claims/{claim_id}")
def get_claim(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    row = (
        db.query(Claim, Listing)
        .join(Listing, Listing.id == Claim.listing_id)
        .filter(Claim.id == claim_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404)
    claim, listing = row

    dispute = db.query(Dispute).filter(Dispute.claim_id == claim.id).first()

    user_ids = {claim.picker_id, listing.giver_id}
    if dispute is not None:
        user_ids.add(dispute.filer_user_id)
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    dispute_filed_at = dispute.filed_at if dispute is not None else None

    dispute_out = None
    if dispute is not None:
        dispute_out = {
            "id": str(dispute.id),
            "filed_at": _iso(dispute.filed_at),
            "responded_at": _iso(dispute.responded_at),
            "resolved_at": _iso(dispute.resolved_at),
            "status": dispute.status,
            "resolution": dispute.resolution,
            "reason": dispute.reason_text,
            "party": "Picker" if dispute.filer_user_id == claim.picker_id else "Giver",
            "filer": names.get(dispute.filer_user_id),
        }

    participant_ids = {claim.picker_id, listing.giver_id}
    messages = (
        db.query(Message)
        .filter(Message.listing_id == listing.id)
        .filter(Message.sender_id.in_(participant_ids))
        .filter(Message.recipient_id.in_(participant_ids))
        .order_by(Message.created_at.asc())
        .all()
    )
    messages_out = [
        {
            "id": str(m.id),
            "sender": names.get(m.sender_id),
            "sender_id": str(m.sender_id),
            "at": _iso(m.created_at),
            "text": m.content,
            "image_url": sign_photo_url(m.image_url),
            "deflected": m.deflect_category is not None,
        }
        for m in messages
    ]

    flags = (
        db.query(func.count(Report.id))
        .filter(Report.listing_id == listing.id)
        .filter(Report.source == "auto")
        .scalar()
    )

    return {
        **_claim_row(claim, listing, names, dispute_filed_at),
        "zone": listing.neighborhood,
        "photos": sign_photo_urls(list(listing.photo_urls)) if listing.photo_urls else [],
        "pickup_photo": sign_photo_url(claim.completion_photo_url),
        "appointment": _iso(claim.pickup_scheduled_at),
        "arrived": _iso(claim.geofence_confirmed_at),
        "authorized_at": _iso(claim.authorized_at),
        "captured_at": _iso(claim.captured_at),
        "refunded_at": _iso(claim.refunded_at),
        "cancelled_at": _iso(claim.cancelled_at),
        "auto_captured_at": _iso(claim.auto_captured_at),
        "no_show_at": _iso(claim.no_show_at),
        "completed_at": _iso(claim.completed_at),
        "pickup_mode": claim.pickup_mode,
        "stripe": {
            "payment_intent": claim.stripe_payment_intent_id,
            "refund_id": claim.refund_id,
        },
        "dispute": dispute_out,
        "messages": messages_out,
        "flags": flags,
        "notes": notes_for(db, "claim", claim.id),
    }


def _listing_st(listing: Listing, now: datetime) -> str:
    if listing.status == "active":
        if listing.expires_at <= now + timedelta(hours=24):
            return "expiring"
        return "active"
    if listing.status in ("claimed", "completed", "expired"):
        return listing.status
    return "deactivated"


def _listing_ended(listing: Listing) -> str | None:
    if listing.completed_at is not None:
        return _iso(listing.completed_at)
    if listing.status == "expired":
        return _iso(listing.expires_at)
    return None


def _listing_row(
    listing: Listing,
    givers: dict[Any, str | None],
    views: dict[Any, int],
    saves: dict[Any, int],
    claims: dict[Any, int],
    now: datetime,
) -> dict[str, Any]:
    return {
        "id": str(listing.id),
        "ref": _listing_ref(listing.id),
        "title": listing.title,
        "cat": listing.category[:1].upper() + listing.category[1:],
        "giver": givers.get(listing.giver_id),
        "zone": listing.neighborhood,
        "posted": _iso(listing.created_at),
        "st": _listing_st(listing, now),
        "status": listing.status,
        "views": views.get(listing.id, 0),
        "saves": saves.get(listing.id, 0),
        "claims": claims.get(listing.id, 0),
        "deadline": listing.deadline_kind,
        "deadline_at": _iso(listing.deadline_at),
        "ended": _listing_ended(listing),
        "expires": _iso(listing.expires_at),
        "photo": sign_photo_url(listing.photo_urls[0]) if listing.photo_urls else None,
        "giver_id": str(listing.giver_id),
        "ai_generated": listing.ai_generated,
        "test": listing.is_test,
    }


@router.get("/admin/listings")
def list_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    now = datetime.utcnow()

    listings = db.query(Listing).order_by(Listing.created_at.desc()).all()
    listing_ids = [listing.id for listing in listings]

    views = dict(
        db.query(ViewHistory.listing_id, func.count(ViewHistory.id))
        .filter(ViewHistory.listing_id.in_(listing_ids))
        .group_by(ViewHistory.listing_id)
        .all()
    )
    saves = dict(
        db.query(Saved.listing_id, func.count(Saved.id))
        .filter(Saved.listing_id.in_(listing_ids))
        .group_by(Saved.listing_id)
        .all()
    )
    claims = dict(
        db.query(Claim.listing_id, func.count(Claim.id))
        .filter(Claim.listing_id.in_(listing_ids))
        .group_by(Claim.listing_id)
        .all()
    )

    giver_ids = {listing.giver_id for listing in listings}
    givers = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(giver_ids)).all()}

    return [_listing_row(listing, givers, views, saves, claims, now) for listing in listings]


_LIVE_CLAIM_STATUSES = ("authorized", "pickup_scheduled")


@router.get("/admin/listings/{listing_id}")
def get_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    now = datetime.utcnow()

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404)

    giver = db.query(User).filter(User.id == listing.giver_id).first()
    givers = {listing.giver_id: giver.display_name if giver is not None else None}

    views_count = db.query(func.count(ViewHistory.id)).filter(ViewHistory.listing_id == listing.id).scalar() or 0
    saves_count = db.query(func.count(Saved.id)).filter(Saved.listing_id == listing.id).scalar() or 0

    listing_claims = (
        db.query(Claim)
        .filter(Claim.listing_id == listing.id)
        .order_by(Claim.claimed_at.desc())
        .all()
    )
    claims_count = {listing.id: len(listing_claims)}

    picker_ids = {claim.picker_id for claim in listing_claims}
    pickers = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(picker_ids)).all()}

    claims_out = [
        {
            "id": str(claim.id),
            "ref": _claim_ref(claim.id),
            "picker": pickers.get(claim.picker_id),
            "picker_id": str(claim.picker_id),
            "status": claim.status,
            "claimed_at": _iso(claim.claimed_at),
        }
        for claim in listing_claims
    ]

    live_claim_ref = next(
        (claim["ref"] for claim in claims_out if claim["status"] in _LIVE_CLAIM_STATUSES),
        None,
    )

    reports = (
        db.query(Report)
        .filter(Report.listing_id == listing.id)
        .filter(Report.source == "auto")
        .order_by(Report.created_at.desc())
        .all()
    )
    flags_out = [
        {
            "id": "R-" + str(report.id)[:6].upper(),
            "report_id": str(report.id),
            "rule": report.triggered_rule,
            "rule_label": rule_definition(report.triggered_rule)[0],
            "rule_text": rule_definition(report.triggered_rule)[1],
            "status": report.status,
            "at": _iso(report.created_at),
            "text": report.description,
        }
        for report in reports
    ]

    today = now.date()
    views_today = (
        db.query(func.count(ViewHistory.id))
        .filter(ViewHistory.listing_id == listing.id)
        .filter(func.date(ViewHistory.viewed_at) == today)
        .scalar()
        or 0
    )
    saves_today = (
        db.query(func.count(Saved.id))
        .filter(Saved.listing_id == listing.id)
        .filter(func.date(Saved.created_at) == today)
        .scalar()
        or 0
    )

    first_view_at = (
        db.query(func.min(ViewHistory.viewed_at)).filter(ViewHistory.listing_id == listing.id).scalar()
    )
    first_save_at = (
        db.query(func.min(Saved.created_at)).filter(Saved.listing_id == listing.id).scalar()
    )
    first_claim_at = min((claim.claimed_at for claim in listing_claims), default=None)

    category_listing_ids = [
        row[0]
        for row in db.query(Listing.id).filter(Listing.category == listing.category).all()
    ]
    category_total_views = (
        db.query(func.count(ViewHistory.id))
        .filter(ViewHistory.listing_id.in_(category_listing_ids))
        .scalar()
        or 0
    )
    category_avg_views = (
        round(category_total_views / len(category_listing_ids)) if category_listing_ids else 0
    )

    messages_count = db.query(func.count(Message.id)).filter(Message.listing_id == listing.id).scalar() or 0

    return {
        **_listing_row(listing, givers, {listing.id: views_count}, {listing.id: saves_count}, claims_count, now),
        "photos": sign_photo_urls(list(listing.photo_urls)) if listing.photo_urls else [],
        "description": listing.description,
        "ai_generated": listing.ai_generated,
        "content_hash": listing.photo_content_hash is not None,
        "lat": listing.location_lat,
        "lng": listing.location_lng,
        "approx_lat": listing.location_lat_approx,
        "approx_lng": listing.location_lng_approx,
        "auto_relist": listing.auto_relist,
        "deadline_kind": listing.deadline_kind,
        "deadline_at": _iso(listing.deadline_at),
        "expires_at": _iso(listing.expires_at),
        "created_at": _iso(listing.created_at),
        "available_since": _iso(listing.available_since),
        "claimed_at": _iso(listing.claimed_at),
        "completed_at": _iso(listing.completed_at),
        "status": listing.status,
        "claims": claims_out,
        "live_claim_ref": live_claim_ref,
        "flags": flags_out,
        "views_today": views_today,
        "saves_today": saves_today,
        "first_view_at": _iso(first_view_at),
        "first_save_at": _iso(first_save_at),
        "first_claim_at": _iso(first_claim_at),
        "category_avg_views": category_avg_views,
        "messages": messages_count,
        "notes": notes_for(db, "listing", listing.id),
    }


@router.get("/admin/disputes")
def list_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    rows = (
        db.query(Dispute, Claim, Listing)
        .join(Claim, Claim.id == Dispute.claim_id)
        .join(Listing, Listing.id == Claim.listing_id)
        .order_by(Dispute.filed_at.desc())
        .all()
    )

    user_ids = {dispute.filer_user_id for dispute, _, _ in rows}
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    out = []
    for dispute, claim, listing in rows:
        out.append(
            {
                "id": str(dispute.id),
                "ref": _claim_ref(claim.id),
                "claim_id": str(claim.id),
                "at": _iso(dispute.filed_at),
                "party": "Picker" if dispute.filer_user_id == claim.picker_id else "Giver",
                "reason": claim.dispute_reason or dispute.reason_text[:60],
                "text": dispute.reason_text,
                "responded": _iso(dispute.responded_at),
                "resolved": _iso(dispute.resolved_at),
                "resolution": dispute.resolution,
                "status": dispute.status,
                "acknowledged": dispute.acknowledged,
                "origin": "app",
            }
        )

    return out


_RULE_PREFIX = "rule_"


def _flag_rule(triggered_rule: str | None) -> str | None:
    if triggered_rule is None:
        return None
    if triggered_rule.startswith(_RULE_PREFIX):
        return "r" + triggered_rule[len(_RULE_PREFIX):]
    return triggered_rule


_REPORT_STATUS_TO_ST = {
    "pending": "pending",
    "resolved": "resolved",
    "reviewed": "dismissed",
    "dismissed": "dismissed",
}

_FLAG_DECISION_ACTIONS = ("flag_warn", "flag_false_positive", "flag_escalate")


_RETIRED_RULES = frozenset({"rule_1", "rule_5"})


@router.get("/admin/rules")
def list_rules(
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    from app.services.scam_detection import RULE_DEFINITIONS

    return [
        {
            "rule": _flag_rule(key),
            "rule_label": label,
            "rule_text": text,
        }
        for key, (label, text) in RULE_DEFINITIONS.items()
        if key not in _RETIRED_RULES
    ]


@router.get("/admin/flags")
def list_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    reports = (
        db.query(Report)
        .filter(Report.source == "auto")
        .order_by(Report.created_at.desc())
        .all()
    )

    listing_ids = {r.listing_id for r in reports if r.listing_id is not None}
    listings = {l.id: l for l in db.query(Listing).filter(Listing.id.in_(listing_ids)).all()}

    user_ids = {r.reported_user_id for r in reports}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    decisions: dict[str, AdminAction] = {}
    for action in db.query(AdminAction).filter(AdminAction.action.in_(_FLAG_DECISION_ACTIONS)).all():
        report_key = (action.details or {}).get("report_id")
        if report_key:
            decisions[report_key] = action
    actor_ids = {a.actor_user_id for a in decisions.values() if a.actor_user_id is not None}
    actors = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(actor_ids)).all()} if actor_ids else {}

    out = []
    for report in reports:
        listing = listings.get(report.listing_id) if report.listing_id is not None else None
        reported_user = users.get(report.reported_user_id)
        label, rule_text = rule_definition(report.triggered_rule)
        decision = decisions.get(str(report.id))
        out.append(
            {
                "id": "R-" + str(report.id)[:6].upper(),
                "report_id": str(report.id),
                "rule": _flag_rule(report.triggered_rule),
                "rule_label": label,
                "rule_text": rule_text,
                "on": "listing" if report.listing_id is not None else "message",
                "ref": _listing_ref(listing.id) if listing is not None else None,
                "item": listing.title if listing is not None else None,
                "user": reported_user.display_name if reported_user is not None else None,
                "user_id": str(report.reported_user_id),
                "role": "Giver" if listing is not None and report.reported_user_id == listing.giver_id else "Picker",
                "at": _iso(report.created_at),
                "text": report.description,
                "after": None,
                "st": _REPORT_STATUS_TO_ST.get(report.status, report.status),
                "status": report.status,
                "reason": report.reason,
                "decided_at": _iso(report.resolved_at),
                "decided_by": actors.get(decision.actor_user_id) if decision is not None else None,
            }
        )

    return out


@router.get("/admin/money")
def list_money(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    now = datetime.utcnow()

    rows = (
        db.query(Claim, Listing)
        .join(Listing, Listing.id == Claim.listing_id)
        .filter(Claim.status == "pending_payment")
        .order_by(Claim.claimed_at.desc())
        .all()
    )

    sweep_at = (
        db.query(func.max(JobRun.started_at))
        .filter(JobRun.job == "pending_payment_sweeper")
        .scalar()
    )

    user_ids = set()
    for claim, listing in rows:
        user_ids.add(claim.picker_id)
        user_ids.add(listing.giver_id)
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    out = []
    for claim, listing in rows:
        # One read per stuck claim; None ("not read") for a synthetic id or a failed read.
        stripe_status = retrieve_payment_intent_status(claim.stripe_payment_intent_id)

        if stripe_status == "requires_capture":
            kind = "webhook"
        elif claim.claimed_at < now - timedelta(minutes=60):
            kind = "hour"
        else:
            kind = "five"

        out.append(
            {
                "ref": _claim_ref(claim.id),
                "claim_id": str(claim.id),
                "item": listing.title,
                "picker": names.get(claim.picker_id),
                "giver": names.get(listing.giver_id),
                "picker_id": str(claim.picker_id),
                "giver_id": str(listing.giver_id),
                "listing_id": str(listing.id),
                "at": _iso(claim.claimed_at),
                "stripe": stripe_status,
                "payment_intent": claim.stripe_payment_intent_id,
                "sweep": _iso(sweep_at),
                "kind": kind,
            }
        )

    return out


# Webhook receipts and deploys are NEEDS BUILDING — no table records them. Job runs
# come from job_runs (both runners write one row per job); Sentry issues from
# watcher_events. Job rows: every run in the last 24 hours plus every failure in
# the last 30 days, so the list period control has the failures to show.
@router.get("/admin/health")
def list_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    runs = (
        db.query(JobRun)
        .filter(JobRun.started_at >= now - timedelta(days=30))
        .filter(or_(JobRun.result == "failed", JobRun.started_at >= now - timedelta(hours=24)))
        .order_by(JobRun.started_at.desc())
        .all()
    )
    events = (
        db.query(WatcherEvent)
        .order_by(WatcherEvent.raised_at.desc())
        .limit(200)
        .all()
    )

    entries: list[tuple[datetime, dict[str, Any]]] = []
    for run in runs:
        entries.append((run.started_at, {
            "id": "J-" + str(run.id)[:8].upper(),
            "kind": "job",
            "job": run.job,
            "at": _iso(run.started_at),
            "dur": round((run.finished_at - run.started_at).total_seconds(), 1),
            "result": run.result,
            "counts": run.counts or "",
            "err": run.error,
        }))
    for row in events:
        entries.append((row.raised_at, {
            "id": str(row.id),
            "kind": "sentry",
            "job": "sentry",
            "at": _iso(row.raised_at),
            "dur": 0,
            "result": "open" if row.state == "pending" else "ok",
            "counts": row.kind,
            "err": row.ref,
        }))
    entries.sort(key=lambda entry: entry[0], reverse=True)
    return [row for _, row in entries]

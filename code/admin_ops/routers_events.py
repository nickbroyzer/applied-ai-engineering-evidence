"""User events — the app posts batches; admins read one person's trail."""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from sqlalchemy.orm import Session, aliased

from app.dependencies import get_current_user, get_db
from app.models import AdminAction, Source, TermsAcceptance, User, UserEvent
from app.rate_limit import rate_limit
from app.routers.admin import require_admin
from app.services.user_events import EVENT_NAMES

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])

MAX_BATCH = 100


class EventIn(BaseModel):
    client_event_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=48)
    at: datetime
    session_id: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=16)
    app_version: str | None = Field(default=None, max_length=32)
    props: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: list[EventIn]


def _row_dict(row: UserEvent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "name": row.name,
        "at": row.at.isoformat(),
        "received_at": row.received_at.isoformat(),
        "session_id": row.session_id,
        "platform": row.platform,
        "app_version": row.app_version,
        "client_event_id": row.client_event_id,
        "props": row.props,
    }


@router.post(
    "/events/batch",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("events", limit=600, window_seconds=3600))],
)
def post_events(
    body: EventBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    if not 1 <= len(body.events) <= MAX_BATCH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A batch carries 1 to {MAX_BATCH} events",
        )
    unknown = sorted({e.name for e in body.events if e.name not in EVENT_NAMES})
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Unknown event name", "names": unknown},
        )
    now = datetime.now(timezone.utc)
    if current_user.source_id is None:
        for e in body.events:
            slug = e.props.get("install_source")
            if not isinstance(slug, str):
                continue
            source = db.query(Source).filter(Source.slug == slug).first()
            if source is not None:
                current_user.source_id = source.id
                current_user.source_stamped_at = now
            break
    rows = []
    for e in body.events:
        at = e.at if e.at.tzinfo is not None else e.at.replace(tzinfo=timezone.utc)
        if at > now:
            at = now
        rows.append({
            "user_id": current_user.id,
            "name": e.name,
            "at": at,
            "session_id": e.session_id,
            "platform": e.platform,
            "app_version": e.app_version,
            "client_event_id": e.client_event_id,
            "props": e.props,
        })
    # RETURNING makes the written count exact: SQLAlchemy 2.0 reports rowcount
    # as -1 for a multi-row INSERT ... ON CONFLICT DO NOTHING without it.
    stmt = (
        insert(UserEvent)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_user_events_user_client_event")
        .returning(UserEvent.id)
    )
    written = len(db.execute(stmt).fetchall())
    db.commit()
    logger.info(json.dumps({
        "event": "user_events_written",
        "user_id": str(current_user.id),
        "received": len(rows),
        "written": written,
    }))
    return {"received": len(rows), "written": written}


@router.get("/admin/users/{user_id}/events")
def list_user_events(
    user_id: uuid.UUID,
    limit: int = Query(default=500, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    rows = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == user_id)
        .order_by(UserEvent.at.asc(), UserEvent.received_at.asc())
        .limit(min(limit, 2000))
        .all()
    )
    return [_row_dict(row) for row in rows]


def _providers_by_user(db: Session) -> dict[str, str]:
    """Sign-in method per account, from Supabase's identities table. The test
    database carries no auth schema, so a failure here means no methods, not an error."""
    try:
        rows = db.execute(text(
            "select user_id::text, string_agg(provider, ',' order by provider) "
            "from auth.identities group by user_id"
        )).fetchall()
    except Exception:
        db.rollback()
        return {}
    return {row[0]: row[1] for row in rows}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _latest_terms_by_user(db: Session) -> dict[str, str]:
    """Each user's most recently accepted terms version, newest accepted_at winning."""
    rows = (
        db.query(TermsAcceptance)
        .order_by(TermsAcceptance.user_id, TermsAcceptance.accepted_at.asc())
        .all()
    )
    out: dict[str, str] = {}
    for row in rows:
        out[str(row.user_id)] = row.version
    return out


def _latest_standing_actions_by_user(db: Session) -> dict[str, tuple[AdminAction, str | None]]:
    """Each user's newest suspend/timeout AdminAction row and the acting admin's
    name, one grouped query."""
    actor = aliased(User)
    rows = (
        db.query(AdminAction, actor.display_name)
        .outerjoin(actor, actor.id == AdminAction.actor_user_id)
        .filter(AdminAction.action.in_(("suspend", "timeout")))
        .order_by(AdminAction.subject_user_id, AdminAction.at.desc())
        .all()
    )
    out: dict[str, tuple[AdminAction, str | None]] = {}
    for action, actor_name in rows:
        key = str(action.subject_user_id)
        if key not in out:
            out[key] = (action, actor_name)
    return out


@router.get("/admin/users")
def list_users(
    limit: int = Query(default=500, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    providers = _providers_by_user(db)
    terms = _latest_terms_by_user(db)
    standing_actions = _latest_standing_actions_by_user(db)
    now = datetime.utcnow()
    users = db.query(User).order_by(User.created_at.desc()).limit(min(limit, 2000)).all()
    out = []
    for u in users:
        if u.is_suspended:
            standing = "suspended"
        elif u.picker_timeout_until is not None and u.picker_timeout_until > now:
            standing = "timeout"
        else:
            standing = "ok"
        entry = standing_actions.get(str(u.id))
        action, actor_name = entry if entry is not None else (None, None)
        if standing == "suspended":
            standing_reason = u.suspension_reason
        elif standing == "timeout":
            standing_reason = action.reason if action is not None else None
        else:
            standing_reason = None
        out.append({
            "id": str(u.id),
            "name": u.display_name,
            "email": u.email,
            "source": providers.get(str(u.id)),
            "signup": _iso(u.created_at),
            "activated": _iso(u.profile_completed_at),
            "last_seen": _iso(u.last_active_at),
            "deleted": _iso(u.deleted_at),
            "country": u.signup_country,
            "zone": u.neighborhood,
            "standing": standing,
            "standing_since": _iso(action.at) if action is not None else None,
            "standing_reason": standing_reason,
            "standing_actor": actor_name,
            "standing_notice": bool(action.notice_sent) if action is not None else False,
            "timeout_until": _iso(u.picker_timeout_until),
            "terms": terms.get(str(u.id)),
            "score": u.trust_score,
            "pickups": u.completed_pickups,
            "giveaways": u.completed_giveaways,
            "test": u.email.endswith("@zelbi.test"),
        })
    return out

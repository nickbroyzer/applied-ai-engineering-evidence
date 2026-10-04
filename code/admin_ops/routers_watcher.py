import asyncio
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.dependencies import get_current_user_detached, get_db
from app.models import User, WatcherEvent
from app.routers.admin import require_admin
from app.services.standing_notices import record_action
from app.utils.iso import iso_utc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watcher"])

SOURCE = "sentry"
FAMILY = "platform"
ACCEPTED_RESOURCES = ("issue", "event_alert")

_SEVERITY_BY_LEVEL = {"fatal": 9, "error": 7, "warning": 5, "info": 3, "debug": 2}
_DEFAULT_SEVERITY = 7
_STATE_BY_ACTION = {"resolved": "resolved", "ignored": "dismissed"}
_DEFAULT_STATE = "pending"

STREAM_POLL_SECONDS = 2
STREAM_KEEPALIVE_SECONDS = 15


def _severity_for(level: Any) -> int:
    if not isinstance(level, str):
        return _DEFAULT_SEVERITY
    return _SEVERITY_BY_LEVEL.get(level.lower(), _DEFAULT_SEVERITY)


def _state_for(action: str) -> str:
    return _STATE_BY_ACTION.get(action, _DEFAULT_STATE)


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value:
        text_value = value.strip()
        if text_value.endswith("Z"):
            text_value = text_value[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text_value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _project_slug(project: Any) -> str:
    if isinstance(project, dict):
        slug = project.get("slug") or project.get("name") or project.get("id")
        return str(slug) if slug is not None else ""
    if project is None:
        return ""
    return str(project)


def _row_dict(row: WatcherEvent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "family": row.family,
        "kind": row.kind,
        "severity": row.severity,
        "who": row.who,
        "ref": row.ref,
        "source": row.source,
        "source_id": row.source_id,
        "state": row.state,
        "raised_at": iso_utc(row.raised_at),
        "created_at": iso_utc(row.created_at),
    }


def _upsert_issue(
    db: Session,
    *,
    source_id: str,
    title: Any,
    level: Any,
    url: Any,
    who: str,
    raised_at: datetime | None,
    action: str,
    payload: dict[str, Any],
) -> tuple[WatcherEvent, bool]:
    kind = (title if isinstance(title, str) and title else "Untitled Sentry issue")[:200]
    ref = (url if isinstance(url, str) else "")[:500]
    severity = _severity_for(level)
    state = _state_for(action)
    raised = raised_at or datetime.now(timezone.utc)

    existing = (
        db.query(WatcherEvent)
        .filter(WatcherEvent.source == SOURCE, WatcherEvent.source_id == source_id)
        .first()
    )
    if existing is not None:
        existing.kind = kind
        existing.severity = severity
        existing.ref = ref
        existing.payload = payload
        existing.raised_at = raised
        existing.state = state
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing, False

    row = WatcherEvent(
        family=FAMILY,
        kind=kind,
        severity=severity,
        who=who[:200],
        ref=ref,
        source=SOURCE,
        source_id=source_id,
        payload=payload,
        state=state,
        raised_at=raised,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent delivery for the same issue won the insert; fall through
        # to the update path so both deliveries land on the one row.
        db.rollback()
        return _upsert_issue(
            db,
            source_id=source_id,
            title=title,
            level=level,
            url=url,
            who=who,
            raised_at=raised_at,
            action=action,
            payload=payload,
        )
    db.refresh(row)
    return row, True


def _invalid_payload() -> HTTPException:
    logger.warning(json.dumps({"event": "sentry_webhook_invalid_payload"}))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid payload",
    )


@router.post("/webhooks/sentry")
async def sentry_webhook(request: Request) -> JSONResponse:
    body = await request.body()
    sig_header = request.headers.get("sentry-hook-signature")
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Sentry signature",
        )

    secret = (settings.sentry_webhook_secret or "").strip()
    if not secret:
        logger.error(
            json.dumps({"event": "sentry_webhook_missing_secret_config"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook not configured",
        )

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), sig_header.strip().encode()):
        logger.warning(
            json.dumps({"event": "sentry_webhook_invalid_signature"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    resource = request.headers.get("sentry-hook-resource") or ""
    if resource not in ACCEPTED_RESOURCES:
        logger.debug(
            json.dumps({"event": "sentry_webhook_ignored_resource", "resource": resource})
        )
        return JSONResponse(status_code=200, content={"ignored": resource})

    try:
        event = json.loads(body)
    except ValueError:
        raise _invalid_payload() from None
    if not isinstance(event, dict):
        raise _invalid_payload()

    data = event.get("data")
    if not isinstance(data, dict):
        data = {}

    if resource == "issue":
        issue = data.get("issue")
        if not isinstance(issue, dict) or issue.get("id") is None:
            raise _invalid_payload()
        action = str(event.get("action") or "created")
        fields = {
            "source_id": str(issue.get("id"))[:120],
            "title": issue.get("title"),
            "level": issue.get("level"),
            "url": issue.get("web_url") or issue.get("permalink"),
            "who": _project_slug(issue.get("project")),
            "raised_at": (
                _parse_timestamp(issue.get("lastSeen") or issue.get("last_seen"))
                or _parse_timestamp(issue.get("firstSeen") or issue.get("first_seen"))
            ),
        }
    else:
        alert_event = data.get("event")
        if not isinstance(alert_event, dict) or alert_event.get("issue_id") is None:
            raise _invalid_payload()
        action = "created"
        fields = {
            "source_id": str(alert_event.get("issue_id"))[:120],
            "title": alert_event.get("title"),
            "level": alert_event.get("level"),
            "url": alert_event.get("web_url"),
            "who": _project_slug(alert_event.get("project")),
            "raised_at": _parse_timestamp(alert_event.get("timestamp")),
        }

    db = SessionLocal()
    try:
        row, inserted = _upsert_issue(db, action=action, payload=event, **fields)
        logger.info(
            json.dumps(
                {
                    "event": "sentry_webhook_upserted",
                    "resource": resource,
                    "action": action,
                    "source_id": fields["source_id"],
                    "id": str(row.id),
                    "state": row.state,
                    "inserted": inserted,
                }
            )
        )
        row_id = str(row.id)
    except Exception:
        db.rollback()
        logger.exception("sentry_webhook_handler_error resource=%s", resource)
        raise
    finally:
        db.close()

    return JSONResponse(status_code=200, content={"ok": True, "id": row_id, "action": action})


@router.get("/admin/watcher/events")
def list_watcher_events(
    family: str | None = Query(default=None),
    state: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    query = db.query(WatcherEvent)
    if family:
        query = query.filter(WatcherEvent.family == family)
    if state:
        query = query.filter(WatcherEvent.state == state)
    rows = (
        query.order_by(WatcherEvent.raised_at.desc(), WatcherEvent.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return [_row_dict(row) for row in rows]


def _stream_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
) -> User:
    """EventSource cannot set headers, so the stream also takes the bearer
    token as ?access_token=. Verification is get_current_user itself, via the
    detached wrapper so no pooler connection is held for the stream's life."""
    if not authorization and access_token:
        authorization = f"Bearer {access_token}"
    user = get_current_user_detached(request=request, authorization=authorization)
    return require_admin(current_user=user)


def _poll_new_events(since: datetime) -> tuple[list[dict[str, Any]], datetime]:
    db = SessionLocal()
    try:
        rows = (
            db.query(WatcherEvent)
            .filter(WatcherEvent.created_at > since)
            .order_by(WatcherEvent.created_at.asc())
            .all()
        )
        latest = rows[-1].created_at if rows else since
        return [_row_dict(row) for row in rows], latest
    finally:
        db.close()


async def _event_stream(request: Request):
    last_created_at = datetime.now(timezone.utc)
    last_sent = time.monotonic()
    while True:
        if await request.is_disconnected():
            return
        payloads, last_created_at = await asyncio.to_thread(
            _poll_new_events, last_created_at
        )
        if payloads:
            for payload in payloads:
                yield f"data: {json.dumps(payload)}\n\n"
            last_sent = time.monotonic()
        elif time.monotonic() - last_sent >= STREAM_KEEPALIVE_SECONDS:
            yield ": keepalive\n\n"
            last_sent = time.monotonic()
        await asyncio.sleep(STREAM_POLL_SECONDS)


@router.get("/admin/watcher/stream")
async def stream_watcher_events(
    request: Request,
    current_user: User = Depends(_stream_admin),
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


SENTRY_API_BASE = "https://sentry.io/api/0"
BACKFILL_MAX_PAGES = 10
_NEXT_CURSOR_RE = re.compile(r'rel="next";\s*results="true";\s*cursor="([^"]+)"')


def _sentry_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=SENTRY_API_BASE,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15.0,
    )


def _sentry_configured() -> bool:
    return bool((settings.sentry_auth_token or "").strip() and (settings.sentry_org or "").strip())


@router.get("/admin/watcher/sentry-config")
def sentry_config(current_user: User = Depends(require_admin)) -> dict[str, bool]:
    return {"configured": _sentry_configured()}


@router.post("/admin/watcher/backfill")
def backfill_sentry_issues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, int]:
    """One-time read of every unresolved Sentry issue into watcher_events. The webhook
    reports only changes after the integration was connected; this fills the rest."""
    if not _sentry_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SENTRY_AUTH_TOKEN is not set")
    path = f"/organizations/{settings.sentry_org.strip()}/issues/"
    params: dict[str, Any] = {"query": "is:unresolved", "limit": 100, "statsPeriod": "30d"}
    inserted = updated = pages = 0
    with _sentry_client(settings.sentry_auth_token.strip()) as client:
        while pages < BACKFILL_MAX_PAGES:
            resp = client.get(path, params=params)
            pages += 1
            if resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Sentry answered {resp.status_code}")
            for issue in resp.json():
                if not isinstance(issue, dict) or issue.get("id") is None:
                    continue
                _, was_inserted = _upsert_issue(
                    db,
                    source_id=str(issue.get("id"))[:120],
                    title=issue.get("title"),
                    level=issue.get("level"),
                    url=issue.get("permalink"),
                    who=_project_slug(issue.get("project")),
                    raised_at=_parse_timestamp(issue.get("lastSeen")) or _parse_timestamp(issue.get("firstSeen")),
                    action="created",
                    payload={"backfill": issue},
                )
                if was_inserted:
                    inserted += 1
                else:
                    updated += 1
            match = _NEXT_CURSOR_RE.search(resp.headers.get("link", ""))
            if match is None:
                break
            params = {**params, "cursor": match.group(1)}
    record_action(
        db, actor=current_user, subject=current_user, action="watcher_backfill",
        reason=f"Sentry backfill: {inserted} new, {updated} updated",
    )
    db.commit()
    logger.info(json.dumps({"event": "sentry_backfill", "inserted": inserted, "updated": updated, "pages": pages}))
    return {"inserted": inserted, "updated": updated, "pages": pages}

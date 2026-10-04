import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from app.dependencies import get_current_user, get_db
from app.models import User
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.api_abuse import record_api_signal

logger = logging.getLogger(__name__)

# Per-user sliding window, held in this process only. The web service runs as a
# single instance, so an in-process counter is exact. If the service is ever
# scaled to multiple replicas this becomes per-replica and must move to a shared
# store.
_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _allow(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Record a hit for key. Returns (allowed, seconds_until_retry)."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _hits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = int(bucket[0] + window_seconds - now) + 1
            return False, max(retry_after, 1)
        bucket.append(now)
        if not bucket:
            _hits.pop(key, None)
        return True, 0


def enforce_rate_limit(db: Session, user: User, name: str, limit: int, window_seconds: int) -> None:
    """Record one hit for `user` on the `name` bucket and raise 429 (with Retry-After and
    the D538 abuse signal) once they exceed `limit` per `window_seconds`. Called by the
    `rate_limit` dependency, and directly by a route that only meters some of its calls
    (the invite-code issue route, D550)."""
    key = f"{name}:{user.id}"
    allowed, retry_after = _allow(key, limit, window_seconds)
    if not allowed:
        logger.warning(
            "rate_limit_exceeded name=%s user=%s limit=%s window=%ss",
            name,
            user.id,
            limit,
            window_seconds,
        )
        # D538: one API-abuse alert per account per route per hour.
        hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
        record_api_signal(
            db,
            source_id=f"ratelimit:{name}:{user.id}:{hour}",
            kind=f"Rate limit hit: {name}",
            severity=4,
            who=str(user.id),
            ref=name,
            payload={"limit": limit, "window_seconds": window_seconds},
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(name: str, limit: int, window_seconds: int):
    """Build a FastAPI dependency limiting an authenticated user to `limit`
    requests per `window_seconds` across everything this dependency guards."""

    def _dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        enforce_rate_limit(db, current_user, name, limit, window_seconds)

    return _dependency


def ip_rate_limit(name: str, limit: int, window_seconds: int):
    """Like rate_limit, but keyed on the caller's network address, for routes that
    take no account (the knowledge endpoint). Behind Railway the direct client
    address is the proxy, so the first hop of X-Forwarded-For is preferred, falling
    back to the direct address. An unidentifiable caller shares one bucket rather
    than passing free."""

    def _dependency(request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        key = f"{name}:ip:{ip}"
        allowed, retry_after = _allow(key, limit, window_seconds)
        if not allowed:
            logger.warning(
                "rate_limit_exceeded name=%s ip=%s limit=%s window=%ss",
                name, ip, limit, window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


def reset_for_tests() -> None:
    """Clear all counters. Test-support only."""
    with _lock:
        _hits.clear()

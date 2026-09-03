import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from app.dependencies import get_current_user
from app.models import User

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


def rate_limit(name: str, limit: int, window_seconds: int):
    """Build a FastAPI dependency limiting an authenticated user to `limit`
    requests per `window_seconds` across everything this dependency guards."""

    def _dependency(current_user: User = Depends(get_current_user)) -> None:
        key = f"{name}:{current_user.id}"
        allowed, retry_after = _allow(key, limit, window_seconds)
        if not allowed:
            logger.warning(
                "rate_limit_exceeded name=%s user=%s limit=%s window=%ss",
                name,
                current_user.id,
                limit,
                window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

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

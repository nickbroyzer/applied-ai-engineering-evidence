"""Apple DeviceCheck client (D542 (4), slice 1): the two per-device bits Apple keeps for us.

Backend client only; no route or caller yet. The Apple host comes from
settings.apple_devicecheck_environment, never from the phone. An unconfigured key or key id
fails closed with DeviceCheckError("not configured") before any network call.

Never logs the device token, the JWT or the private key: log lines are JSON events carrying
the endpoint path and Apple's status code only.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

DEVELOPMENT_HOST = "https://api.development.devicecheck.apple.com"
PRODUCTION_HOST = "https://api.devicecheck.apple.com"
QUERY_PATH = "/v1/query_two_bits"
UPDATE_PATH = "/v1/update_two_bits"
# Apple's development host was observed answering "Failed to find bit state" on 2026-09-26.
NO_BITS_YET_TEXTS = ("Bit State Not Found", "Failed to find bit state")
TOKEN_EXPIRED_TEXT = "Authorization Token Expired"
JWT_MAX_AGE_SECONDS = 50 * 60
REQUEST_TIMEOUT_SECONDS = 10.0


class DeviceCheckError(Exception):
    """Apple refused or could not be reached. status_code and apple_text are None/"" when the
    failure happened before a request was made (for example, no key configured)."""

    def __init__(self, message: str, *, status_code: int | None = None, apple_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.apple_text = apple_text


@dataclass(frozen=True)
class Bits:
    bit0: bool
    bit1: bool
    last_update_time: str | None


def _host() -> str:
    if settings.apple_devicecheck_environment == "production":
        return PRODUCTION_HOST
    return DEVELOPMENT_HOST


def _client() -> httpx.Client:
    """Factory so tests inject an httpx.MockTransport, mirroring watcher._sentry_client."""
    return httpx.Client(base_url=_host(), timeout=REQUEST_TIMEOUT_SECONDS)


# --- bearer token -------------------------------------------------------------------------

_jwt_lock = threading.Lock()
_cached_jwt: str | None = None
_cached_jwt_minted_at: float = 0.0


def _private_key() -> str:
    # Doppler stores the .p8 as one line with literal backslash-n sequences.
    return (settings.apple_devicecheck_private_key or "").replace("\\n", "\n").strip()


def _key_id() -> str:
    return (settings.apple_devicecheck_key_id or "").strip()


def _require_configured() -> None:
    if not _private_key() or not _key_id():
        raise DeviceCheckError("not configured")


def _mint_jwt(now: float) -> str:
    _require_configured()
    return jwt.encode(
        {"iss": settings.apple_team_id, "iat": int(now)},
        _private_key(),
        algorithm="ES256",
        headers={"kid": _key_id()},
    )


def _bearer(*, force: bool = False) -> str:
    """The cached JWT, re-minted when forced or older than JWT_MAX_AGE_SECONDS."""
    global _cached_jwt, _cached_jwt_minted_at
    now = time.time()
    with _jwt_lock:
        if force or _cached_jwt is None or now - _cached_jwt_minted_at > JWT_MAX_AGE_SECONDS:
            _cached_jwt = _mint_jwt(now)
            _cached_jwt_minted_at = now
        return _cached_jwt


def _reset_jwt_cache() -> None:
    global _cached_jwt, _cached_jwt_minted_at
    with _jwt_lock:
        _cached_jwt = None
        _cached_jwt_minted_at = 0.0


# --- requests -----------------------------------------------------------------------------


def _log(event: str, path: str, status_code: int) -> None:
    logger.info(json.dumps({"event": event, "path": path, "status": status_code}))


def _log_warning(event: str, path: str, status_code: int | None, apple_text: str) -> None:
    logger.warning(
        json.dumps({"event": event, "path": path, "status": status_code, "apple_text": apple_text[:300]})
    )


def _clean_token(device_token: str) -> str:
    return "".join((device_token or "").split())


def _send(client: httpx.Client, path: str, device_token: str, extra: dict[str, Any], bearer: str) -> httpx.Response:
    body: dict[str, Any] = {
        "device_token": device_token,
        "transaction_id": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        **extra,
    }
    return client.post(path, json=body, headers={"Authorization": f"Bearer {bearer}"})


def _post(path: str, device_token: str, extra: dict[str, Any]) -> httpx.Response:
    try:
        _require_configured()
    except DeviceCheckError:
        _log_warning("devicecheck_not_configured", path, None, "")
        raise
    token = _clean_token(device_token)
    with _client() as client:
        resp = _send(client, path, token, extra, _bearer())
        if resp.status_code == 401 and TOKEN_EXPIRED_TEXT in resp.text:
            _log("devicecheck_jwt_expired", path, resp.status_code)
            resp = _send(client, path, token, extra, _bearer(force=True))
    if resp.status_code != 200:
        _log_warning("devicecheck_error", path, resp.status_code, resp.text)
        raise DeviceCheckError(
            f"Apple DeviceCheck answered {resp.status_code}",
            status_code=resp.status_code,
            apple_text=resp.text,
        )
    _log("devicecheck_ok", path, resp.status_code)
    return resp


def query_two_bits(device_token: str) -> Bits | None:
    """Apple's stored bits for this device, or None when Apple has none yet."""
    resp = _post(QUERY_PATH, device_token, {})
    if resp.text.strip().casefold() in {text.casefold() for text in NO_BITS_YET_TEXTS}:
        return None
    try:
        data = resp.json()
    except ValueError as exc:
        _log_warning("devicecheck_unreadable_body", QUERY_PATH, resp.status_code, resp.text)
        raise DeviceCheckError("Apple DeviceCheck answered 200 with an unreadable body", status_code=200) from exc
    if not isinstance(data, dict):
        _log_warning("devicecheck_unreadable_body", QUERY_PATH, resp.status_code, resp.text)
        raise DeviceCheckError("Apple DeviceCheck answered 200 with an unreadable body", status_code=200)
    return Bits(
        bit0=bool(data.get("bit0")),
        bit1=bool(data.get("bit1")),
        last_update_time=data.get("last_update_time"),
    )


def update_two_bits(device_token: str, *, bit0: bool, bit1: bool) -> None:
    """Write both of Apple's bits for this device. Both are required: Apple's docs do not say
    whether an omitted bit is kept or cleared, so every write sends both, and a caller passes
    back unchanged the bit it is not changing (D545 survey, section C)."""
    _post(UPDATE_PATH, device_token, {"bit0": bool(bit0), "bit1": bool(bit1)})

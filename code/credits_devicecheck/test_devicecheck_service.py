"""Apple DeviceCheck client (D542 (4), slice 1). Every request goes through httpx.MockTransport;
no test reaches Apple."""
import json
import time
import uuid

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import settings
from app.services import devicecheck_service as dc

KEY_ID = "TESTKEY001"
TEAM_ID = "TEAMID0000"
DEVICE_TOKEN = "  abc\ndef \r\n ghi\t"
CLEAN_TOKEN = "abcdefghi"


@pytest.fixture(scope="module")
def keypair() -> tuple[str, str]:
    private = ec.generate_private_key(ec.SECP256R1())
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def _configured(monkeypatch, keypair):
    private_pem, _ = keypair
    # Doppler stores the .p8 as one line with literal backslash-n sequences.
    monkeypatch.setattr(settings, "apple_devicecheck_private_key", private_pem.replace("\n", "\\n"))
    monkeypatch.setattr(settings, "apple_devicecheck_key_id", KEY_ID)
    monkeypatch.setattr(settings, "apple_team_id", TEAM_ID)
    monkeypatch.setattr(settings, "apple_devicecheck_environment", "development")
    dc._reset_jwt_cache()
    yield
    dc._reset_jwt_cache()


def _install(mocker, handler) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    mocker.patch.object(
        dc,
        "_client",
        lambda: httpx.Client(base_url=dc._host(), transport=httpx.MockTransport(recording)),
    )
    return seen


def _ok_bits(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"bit0": True, "bit1": False, "last_update_time": "2026-09"})


def test_jwt_is_es256_with_kid_iss_iat_and_no_exp(mocker, keypair):
    _, public_pem = keypair
    seen = _install(mocker, _ok_bits)

    dc.query_two_bits(DEVICE_TOKEN)

    auth = seen[0].headers["Authorization"]
    assert auth.startswith("Bearer ")
    token = auth.removeprefix("Bearer ")
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "ES256"
    assert header["kid"] == KEY_ID
    claims = jwt.decode(token, public_pem, algorithms=["ES256"], options={"require": ["iss", "iat"]})
    assert claims["iss"] == TEAM_ID
    assert isinstance(claims["iat"], int)
    assert abs(claims["iat"] - time.time()) < 60
    assert "exp" not in claims


def test_query_returns_bits(mocker):
    seen = _install(mocker, _ok_bits)

    bits = dc.query_two_bits(DEVICE_TOKEN)

    assert bits == dc.Bits(bit0=True, bit1=False, last_update_time="2026-09")
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/v1/query_two_bits"
    body = json.loads(seen[0].content)
    assert body["device_token"] == CLEAN_TOKEN
    assert "bit0" not in body


def test_query_bit_state_not_found_returns_none(mocker):
    _install(mocker, lambda request: httpx.Response(200, text="Bit State Not Found"))

    assert dc.query_two_bits(DEVICE_TOKEN) is None


def test_query_failed_to_find_bit_state_returns_none_and_logs_no_warning(mocker, monkeypatch, caplog):
    _install(mocker, lambda request: httpx.Response(200, text="Failed to find bit state"))
    monkeypatch.setattr(dc.logger, "disabled", False)

    with caplog.at_level("WARNING", logger="app.services.devicecheck_service"):
        assert dc.query_two_bits(DEVICE_TOKEN) is None

    assert caplog.records == []


def test_query_unreadable_body_raises_and_logs_warning(mocker, monkeypatch, caplog):
    _install(mocker, lambda request: httpx.Response(200, text="not json and not the sentinel"))
    monkeypatch.setattr(dc.logger, "disabled", False)

    with caplog.at_level("WARNING", logger="app.services.devicecheck_service"):
        with pytest.raises(dc.DeviceCheckError, match="unreadable body") as excinfo:
            dc.query_two_bits(DEVICE_TOKEN)

    assert excinfo.value.status_code == 200
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    event = json.loads(record.getMessage())
    assert event == {
        "event": "devicecheck_unreadable_body",
        "path": dc.QUERY_PATH,
        "status": 200,
        "apple_text": "not json and not the sentinel",
    }


def test_update_sends_both_bits_transaction_id_and_millisecond_timestamp(mocker):
    seen = _install(mocker, lambda request: httpx.Response(200, text=""))

    before_ms = int(time.time() * 1000)
    assert dc.update_two_bits(DEVICE_TOKEN, bit0=True, bit1=False) is None
    after_ms = int(time.time() * 1000)

    assert len(seen) == 1
    assert seen[0].url.path == "/v1/update_two_bits"
    assert seen[0].headers["Content-Type"].startswith("application/json")
    body = json.loads(seen[0].content)
    assert body["bit0"] is True
    assert body["bit1"] is False
    assert body["device_token"] == CLEAN_TOKEN
    assert uuid.UUID(body["transaction_id"]).version == 4
    assert isinstance(body["timestamp"], int)
    assert before_ms <= body["timestamp"] <= after_ms


@pytest.mark.parametrize(
    "environment, host",
    [
        ("production", "https://api.devicecheck.apple.com"),
        ("development", "https://api.development.devicecheck.apple.com"),
        ("staging", "https://api.development.devicecheck.apple.com"),
        ("", "https://api.development.devicecheck.apple.com"),
    ],
)
def test_host_follows_environment_setting(mocker, monkeypatch, environment, host):
    monkeypatch.setattr(settings, "apple_devicecheck_environment", environment)
    seen = _install(mocker, _ok_bits)

    dc.query_two_bits(DEVICE_TOKEN)

    assert str(seen[0].url) == f"{host}/v1/query_two_bits"
    assert dc._client().base_url == host


def test_expired_jwt_is_reminted_once_and_retried(mocker):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(401, text="Authorization Token Expired")
        return _ok_bits(request)

    seen = _install(mocker, handler)
    mint = mocker.spy(dc, "_mint_jwt")

    bits = dc.query_two_bits(DEVICE_TOKEN)

    assert bits is not None and bits.bit0 is True
    assert calls["n"] == 2
    assert mint.call_count == 2
    first, second = (json.loads(r.content) for r in seen)
    assert first["transaction_id"] != second["transaction_id"]


def test_second_expired_jwt_raises(mocker):
    _install(mocker, lambda request: httpx.Response(401, text="Authorization Token Expired"))
    mint = mocker.spy(dc, "_mint_jwt")

    with pytest.raises(dc.DeviceCheckError) as excinfo:
        dc.query_two_bits(DEVICE_TOKEN)

    assert excinfo.value.status_code == 401
    assert "Authorization Token Expired" in excinfo.value.apple_text
    assert mint.call_count == 2


def test_other_401_is_not_retried(mocker):
    seen = _install(mocker, lambda request: httpx.Response(401, text="Unable to verify authorization token"))

    with pytest.raises(dc.DeviceCheckError) as excinfo:
        dc.update_two_bits(DEVICE_TOKEN, bit0=True, bit1=False)

    assert excinfo.value.status_code == 401
    assert len(seen) == 1


@pytest.mark.parametrize("status, text", [(429, "Too Many Requests"), (503, "Service Unavailable")])
def test_non_200_raises_with_status_code(mocker, status, text):
    _install(mocker, lambda request: httpx.Response(status, text=text))

    with pytest.raises(dc.DeviceCheckError) as excinfo:
        dc.query_two_bits(DEVICE_TOKEN)

    assert excinfo.value.status_code == status
    assert excinfo.value.apple_text == text


def test_jwt_is_cached_within_fifty_minutes(mocker):
    seen = _install(mocker, _ok_bits)
    mint = mocker.spy(dc, "_mint_jwt")

    dc.query_two_bits(DEVICE_TOKEN)
    dc.update_two_bits(DEVICE_TOKEN, bit0=True, bit1=False)

    assert mint.call_count == 1
    assert seen[0].headers["Authorization"] == seen[1].headers["Authorization"]


def test_jwt_is_reminted_after_fifty_minutes(mocker):
    _install(mocker, _ok_bits)
    mint = mocker.spy(dc, "_mint_jwt")

    dc.query_two_bits(DEVICE_TOKEN)
    dc._cached_jwt_minted_at -= dc.JWT_MAX_AGE_SECONDS + 1
    dc.query_two_bits(DEVICE_TOKEN)

    assert mint.call_count == 2


@pytest.mark.parametrize("field", ["apple_devicecheck_private_key", "apple_devicecheck_key_id"])
def test_missing_key_or_key_id_raises_before_any_request(mocker, monkeypatch, field):
    monkeypatch.setattr(settings, field, "")
    seen = _install(mocker, _ok_bits)

    with pytest.raises(dc.DeviceCheckError, match="not configured") as excinfo:
        dc.query_two_bits(DEVICE_TOKEN)
    with pytest.raises(dc.DeviceCheckError, match="not configured"):
        dc.update_two_bits(DEVICE_TOKEN, bit0=True, bit1=False)

    assert excinfo.value.status_code is None
    assert seen == []


def test_logs_carry_status_codes_and_never_the_token_or_jwt(mocker, monkeypatch, caplog):
    seen = _install(mocker, lambda request: httpx.Response(429, text="Too Many Requests"))
    # The suite's alembic fileConfig disables loggers that existed before it ran; re-enable ours.
    monkeypatch.setattr(dc.logger, "disabled", False)

    with caplog.at_level("INFO", logger="app.services.devicecheck_service"):
        with pytest.raises(dc.DeviceCheckError):
            dc.query_two_bits(DEVICE_TOKEN)

    assert caplog.records, "expected a JSON log event"
    jwt_value = seen[0].headers["Authorization"].removeprefix("Bearer ")
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    event = json.loads(record.getMessage())
    assert event["event"] == "devicecheck_error"
    assert event["path"] == dc.QUERY_PATH
    assert event["status"] == 429
    assert event["apple_text"] == "Too Many Requests"
    for record in caplog.records:
        assert CLEAN_TOKEN not in record.getMessage()
        assert jwt_value not in record.getMessage()
        assert "PRIVATE KEY" not in record.getMessage()


def test_error_log_trims_apple_text_to_300_chars(mocker, monkeypatch, caplog):
    long_text = "x" * 500
    _install(mocker, lambda request: httpx.Response(500, text=long_text))
    monkeypatch.setattr(dc.logger, "disabled", False)

    with caplog.at_level("WARNING", logger="app.services.devicecheck_service"):
        with pytest.raises(dc.DeviceCheckError):
            dc.query_two_bits(DEVICE_TOKEN)

    event = json.loads(caplog.records[0].getMessage())
    assert event["apple_text"] == "x" * 300


def test_not_configured_logs_warning_without_token_or_key(mocker, monkeypatch, caplog):
    monkeypatch.setattr(settings, "apple_devicecheck_private_key", "")
    seen = _install(mocker, _ok_bits)
    monkeypatch.setattr(dc.logger, "disabled", False)

    with caplog.at_level("WARNING", logger="app.services.devicecheck_service"):
        with pytest.raises(dc.DeviceCheckError, match="not configured"):
            dc.query_two_bits(DEVICE_TOKEN)

    assert seen == []
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    event = json.loads(record.getMessage())
    assert event == {
        "event": "devicecheck_not_configured",
        "path": dc.QUERY_PATH,
        "status": None,
        "apple_text": "",
    }
    assert CLEAN_TOKEN not in record.getMessage()

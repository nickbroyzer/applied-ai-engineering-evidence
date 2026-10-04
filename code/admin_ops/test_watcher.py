"""Watcher — Sentry webhook writer, admin event list, and stream auth."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import text

from app import models
from app.config import settings
from app.database import engine
from app.routers import watcher

SECRET = "sentry_test_secret_0123456789"
ISSUE_ID = "4507000123"
ISSUE_URL = "https://example-org.sentry.io/issues/4507000123/"


@pytest.fixture(autouse=True)
def _clean_watcher_events():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE watcher_events"))


@pytest.fixture(autouse=True)
def _sentry_secret(monkeypatch):
    monkeypatch.setattr(settings, "sentry_webhook_secret", SECRET)


@pytest.fixture
def admin_user(db_session, picker_user) -> models.User:
    picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(picker_user)
    return picker_user


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _issue_body(action: str, level: str = "error", title: str = "ZeroDivisionError: division by zero") -> dict:
    return {
        "action": action,
        "installation": {"uuid": "inst-1"},
        "data": {
            "issue": {
                "id": ISSUE_ID,
                "title": title,
                "level": level,
                "web_url": ISSUE_URL,
                "project": {"id": "1", "slug": "zelbi-api", "name": "Zelbi API"},
                "firstSeen": "2026-09-09T09:00:00.000000Z",
                "lastSeen": "2026-09-09T09:30:00.000000Z",
            }
        },
        "actor": {"type": "application", "id": "sentry", "name": "Sentry"},
    }


def _event_alert_body() -> dict:
    return {
        "action": "triggered",
        "installation": {"uuid": "inst-1"},
        "data": {
            "event": {
                "issue_id": "4507000999",
                "title": "TimeoutError: pooler connection",
                "level": "warning",
                "web_url": "https://example-org.sentry.io/issues/4507000999/events/abc/",
                "timestamp": 1788000000.0,
                "project": 1,
            },
            "triggered_rule": "Alert on new issues",
        },
    }


def _post(client, body, *, resource: str = "issue", secret: str = SECRET, signature: str | None = None):
    raw = json.dumps(body).encode() if not isinstance(body, bytes) else body
    headers = {
        "sentry-hook-resource": resource,
        "sentry-hook-signature": signature if signature is not None else _sign(raw, secret),
    }
    return client.post("/webhooks/sentry", content=raw, headers=headers)


def _rows(db_session):
    db_session.expire_all()
    return db_session.query(models.WatcherEvent).all()


# --- Webhook: signature and configuration gates.

def test_webhook_400_when_signature_missing(client, db_session):
    resp = client.post(
        "/webhooks/sentry",
        content=b"{}",
        headers={"sentry-hook-resource": "issue"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing Sentry signature"
    assert _rows(db_session) == []


def test_webhook_400_when_signature_wrong(client, db_session):
    resp = _post(client, _issue_body("created"), secret="not-the-secret")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid signature"
    assert _rows(db_session) == []


def test_webhook_400_when_secret_unset(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "sentry_webhook_secret", "")
    resp = _post(client, _issue_body("created"), secret="anything")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Webhook not configured"
    assert _rows(db_session) == []


def test_webhook_400_when_payload_invalid(client, db_session):
    resp = _post(client, b"not-json")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid payload"
    assert _rows(db_session) == []


# --- Webhook: issue resource.

def test_issue_created_inserts_pending_platform_row(client, db_session):
    body = _issue_body("created")
    resp = _post(client, body)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["action"] == "created"

    rows = _rows(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert str(row.id) == payload["id"]
    assert row.family == "platform"
    assert row.kind == "ZeroDivisionError: division by zero"
    assert row.severity == 7
    assert row.who == "zelbi-api"
    assert row.ref == ISSUE_URL
    assert row.source == "sentry"
    assert row.source_id == ISSUE_ID
    assert row.state == "pending"
    assert row.payload == body
    assert row.raised_at == datetime(2026, 9, 9, 9, 30, tzinfo=timezone.utc)


def test_issue_resolved_updates_same_row(client, db_session):
    first = _post(client, _issue_body("created"))
    assert first.status_code == 200
    second = _post(client, _issue_body("resolved", level="fatal"))
    assert second.status_code == 200
    assert second.json()["action"] == "resolved"
    assert second.json()["id"] == first.json()["id"]

    rows = _rows(db_session)
    assert len(rows) == 1
    assert rows[0].state == "resolved"
    assert rows[0].severity == 9


def test_issue_ignored_maps_to_dismissed(client, db_session):
    resp = _post(client, _issue_body("ignored"))
    assert resp.status_code == 200
    rows = _rows(db_session)
    assert len(rows) == 1
    assert rows[0].state == "dismissed"


def test_issue_missing_id_is_invalid_payload(client, db_session):
    body = _issue_body("created")
    del body["data"]["issue"]["id"]
    resp = _post(client, body)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid payload"
    assert _rows(db_session) == []


# --- Webhook: event_alert resource.

def test_event_alert_inserts_one_row(client, db_session):
    body = _event_alert_body()
    resp = _post(client, body, resource="event_alert")
    assert resp.status_code == 200, resp.text
    assert resp.json()["action"] == "created"

    rows = _rows(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.source_id == "4507000999"
    assert row.kind == "TimeoutError: pooler connection"
    assert row.severity == 5
    assert row.who == "1"
    assert row.state == "pending"
    assert row.raised_at == datetime.fromtimestamp(1788000000.0, tz=timezone.utc)


# --- Webhook: other resources are acknowledged and dropped.

def test_other_resource_is_ignored(client, db_session):
    resp = _post(client, {"action": "created", "data": {}}, resource="comment")
    assert resp.status_code == 200
    assert resp.json() == {"ignored": "comment"}
    assert _rows(db_session) == []


# --- Admin list.

def _seed(db_session, *, source_id: str, raised_at: datetime, family: str = "platform", state: str = "pending"):
    row = models.WatcherEvent(
        family=family,
        kind=f"issue {source_id}",
        severity=7,
        who="zelbi-api",
        ref=f"https://example-org.sentry.io/issues/{source_id}/",
        source="sentry",
        source_id=source_id,
        payload={"seed": source_id},
        state=state,
        raised_at=raised_at,
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_events_401_without_user(client):
    resp = client.get("/admin/watcher/events")
    assert resp.status_code == 401


def test_events_403_for_non_admin(auth_client, picker_user):
    resp = auth_client(picker_user).get("/admin/watcher/events")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin privileges required"


def test_events_admin_gets_rows_newest_first(auth_client, admin_user, db_session):
    now = datetime.now(timezone.utc)
    _seed(db_session, source_id="old", raised_at=now - timedelta(hours=2))
    _seed(db_session, source_id="new", raised_at=now)
    _seed(db_session, source_id="mid", raised_at=now - timedelta(hours=1), state="resolved")

    resp = auth_client(admin_user).get("/admin/watcher/events")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert [r["source_id"] for r in rows] == ["new", "mid", "old"]
    assert set(rows[0]) == {
        "id", "family", "kind", "severity", "who", "ref",
        "source", "source_id", "state", "raised_at", "created_at",
    }
    assert rows[0]["family"] == "platform"
    assert rows[0]["source"] == "sentry"
    assert datetime.fromisoformat(rows[0]["raised_at"]).tzinfo is not None


def test_events_filters_and_limit(auth_client, admin_user, db_session):
    now = datetime.now(timezone.utc)
    _seed(db_session, source_id="a", raised_at=now)
    _seed(db_session, source_id="b", raised_at=now - timedelta(minutes=1), state="resolved")
    _seed(db_session, source_id="c", raised_at=now - timedelta(minutes=2), family="security")

    c = auth_client(admin_user)
    assert [r["source_id"] for r in c.get("/admin/watcher/events", params={"state": "resolved"}).json()] == ["b"]
    assert [r["source_id"] for r in c.get("/admin/watcher/events", params={"family": "security"}).json()] == ["c"]
    assert [r["source_id"] for r in c.get("/admin/watcher/events", params={"limit": 1}).json()] == ["a"]


# --- Stream auth mirrors the list route's rejection.

def test_stream_401_without_token(client):
    resp = client.get("/admin/watcher/stream")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"


def test_stream_401_with_wrong_query_token(client):
    resp = client.get("/admin/watcher/stream", params={"access_token": "not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"


def test_stream_401_with_wrong_header_token(client):
    resp = client.get("/admin/watcher/stream", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"


def test_sentry_config_reports_unset(auth_client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "sentry_auth_token", "")

    resp = auth_client(admin_user).get("/admin/watcher/sentry-config")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False}


def test_backfill_without_token_is_503(auth_client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "sentry_auth_token", "")

    resp = auth_client(admin_user).post("/admin/watcher/backfill", json={})
    assert resp.status_code == 503


def _backfill_issue(issue_id: str, title: str) -> dict:
    return {
        "id": issue_id,
        "title": title,
        "level": "error",
        "permalink": f"https://example-org.sentry.io/issues/{issue_id}/",
        "project": {"id": "1", "slug": "zelbi-api"},
        "firstSeen": "2026-09-01T09:00:00.000000Z",
        "lastSeen": "2026-09-12T09:30:00.000000Z",
    }


def test_backfill_upserts_open_issues_across_pages(auth_client, admin_user, db_session, monkeypatch, mocker):
    monkeypatch.setattr(settings, "sentry_auth_token", "tok")
    base = "https://sentry.io/api/0/organizations/example-org/issues/"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("cursor") == "c1":
            link = f'<{base}?cursor=c0>; rel="previous"; results="true"; cursor="c0", <{base}?cursor=c2>; rel="next"; results="false"; cursor="c2"'
            return httpx.Response(200, json=[_backfill_issue("9001", "KeyError: two")], headers={"link": link})
        link = f'<{base}?cursor=c0>; rel="previous"; results="false"; cursor="c0", <{base}?cursor=c1>; rel="next"; results="true"; cursor="c1"'
        return httpx.Response(200, json=[_backfill_issue("9000", "ValueError: one")], headers={"link": link})

    mocker.patch.object(
        watcher,
        "_sentry_client",
        lambda token: httpx.Client(base_url=watcher.SENTRY_API_BASE, transport=httpx.MockTransport(handler)),
    )

    resp = auth_client(admin_user).post("/admin/watcher/backfill", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["inserted"] == 2
    assert body["pages"] == 2

    db_session.expire_all()
    rows = db_session.query(models.WatcherEvent).all()
    assert len(rows) == 2
    assert {r.state for r in rows} == {"pending"}

    actions = db_session.query(models.AdminAction).filter(models.AdminAction.action == "watcher_backfill").all()
    assert len(actions) == 1


def test_backfill_non_admin_forbidden(auth_client, other_picker_user):
    resp = auth_client(other_picker_user).post("/admin/watcher/backfill", json={})
    assert resp.status_code == 403

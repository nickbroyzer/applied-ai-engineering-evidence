"""Rate-limit mounts on claim creation and knowledge (both per signed-in account, D538).

Covers: reading your own claims is never metered — the ceiling was attached at
router mount until 2026-08-13 and locked users out of their own receipts; claim
CREATION trips at its configured limit and answers 429 with a Retry-After header;
the knowledge mount is keyed on X-Forwarded-For, so a different caller address gets
its own bucket rather than sharing the tripped one.
"""
import uuid

from app import models

DISCLOSURE_VERSION = "fee-disclosure-2026-08-08"


def test_claims_reads_are_never_rate_limited(auth_client, picker_user):
    client = auth_client(picker_user)
    listing_id = uuid.uuid4()
    for _ in range(60):
        resp = client.get("/claims/my-active", params={"listing_id": str(listing_id)})
        assert resp.status_code != 429, resp.text

    for _ in range(60):
        resp = client.get("/claims/my-closed")
        assert resp.status_code != 429, resp.text


def test_claim_creation_rate_limit_trips_after_limit(auth_client, picker_user):
    client = auth_client(picker_user)
    body = {
        "listing_id": str(uuid.uuid4()),
        "disclosure_version": DISCLOSURE_VERSION,
    }
    for _ in range(30):
        resp = client.post("/claims", json=body)
        assert resp.status_code != 429, resp.text

    resp = client.post("/claims", json=body)
    assert resp.status_code == 429, resp.text
    assert "Retry-After" in resp.headers


def test_knowledge_requires_sign_in(client):
    resp = client.post("/knowledge/ask", json={"question": "What is the $2 claim fee?"})
    assert resp.status_code == 401, resp.text


def test_knowledge_rate_limit_is_per_account_and_alerts_once(auth_client, picker_user, db_session):
    client = auth_client(picker_user)
    body = {"question": "What is the $2 claim fee?"}
    for _ in range(30):
        resp = client.post("/knowledge/ask", json=body)
        assert resp.status_code != 429, resp.text
    for _ in range(3):
        resp = client.post("/knowledge/ask", json=body)
        assert resp.status_code == 429, resp.text
        assert "Retry-After" in resp.headers
    alerts = (
        db_session.query(models.WatcherEvent)
        .filter(models.WatcherEvent.family == "api")
        .all()
    )
    assert len(alerts) == 1
    assert alerts[0].kind == "Rate limit hit: knowledge"
    other = models.User(
        email=f"other+{uuid.uuid4().hex[:8]}@example.com", display_name="Other"
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    resp = auth_client(other).post("/knowledge/ask", json=body)
    assert resp.status_code != 429, resp.text

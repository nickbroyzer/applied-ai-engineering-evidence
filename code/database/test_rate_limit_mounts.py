"""Rate-limit mounts on claim creation (authenticated) and knowledge (IP-keyed).

Covers: reading your own claims is never metered — the ceiling was attached at
router mount until 2026-08-13 and locked users out of their own receipts; claim
CREATION trips at its configured limit and answers 429 with a Retry-After header;
the knowledge mount is keyed on X-Forwarded-For, so a different caller address gets
its own bucket rather than sharing the tripped one.
"""
import uuid

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


def test_knowledge_ip_rate_limit_trips_then_different_ip_passes(client):
    for _ in range(30):
        resp = client.post(
            "/knowledge/ask",
            json={"question": "What is the $2 claim fee?"},
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert resp.status_code != 429, resp.text

    resp = client.post(
        "/knowledge/ask",
        json={"question": "What is the $2 claim fee?"},
        headers={"X-Forwarded-For": "203.0.113.1"},
    )
    assert resp.status_code == 429, resp.text
    assert "Retry-After" in resp.headers

    resp = client.post(
        "/knowledge/ask",
        json={"question": "What is the $2 claim fee?"},
        headers={"X-Forwarded-For": "203.0.113.2"},
    )
    assert resp.status_code != 429, resp.text

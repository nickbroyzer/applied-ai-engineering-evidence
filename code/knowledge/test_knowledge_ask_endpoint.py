"""
RAG Phase 6A endpoint tests: POST /knowledge/ask (public) and
POST /knowledge/cx/ask (admin-auth CX, per §10 of
14-rag-ingestion-architecture.md).

Covers: answering the claim-fee question with Sources citing the claim-fee
doc, the public-only index rule (default public, 403 on index=cx, 422 on
arbitrary tiers), the support route in contact-support answers and in
refusals, safe refusal of the D212 card-hold-expiry probe, the hard leaks
over every seeded question (no D212, no internal doc paths, no CX docs in
public responses), request validation (missing/empty question), the
unknown-question fallback, query logging, CX route auth, the no-external-API
guard, and the full 22/22 answer eval after router wiring. No embeddings,
no LLM, no external APIs.
"""
import hashlib
import json
import re
import socket
import uuid
from pathlib import Path

import pytest

from app import models
from app.services.knowledge.answer import REFUSAL_TEXT
from app.services.knowledge.answer_eval import run_answer_eval
from app.services.knowledge.eval_cases import seed_eval_cases
from app.services.knowledge.ingestion import run_ingestion

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = REPO_ROOT / "backend" / "app" / "data" / "knowledge_eval_cases.json"

CLAIM_FEE_QUESTION = "What is the $2 claim fee?"
D212_PROBE_QUESTION = "What happens if my card hold expires before pickup?"


def _seed_questions() -> list[str]:
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [c["question"] for c in payload["cases"]]


@pytest.fixture
def corpus(db_session) -> models.KnowledgeIngestionRun:
    run = run_ingestion(db_session, REPO_ROOT)
    assert run.status == "succeeded"
    return run


@pytest.fixture
def golden_cases(db_session, corpus):
    seed_eval_cases(db_session)


@pytest.fixture
def admin_user(db_session) -> models.User:
    u = models.User(
        email=f"admin+{uuid.uuid4().hex[:8]}@example.com",
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _ask(client, question: str, **extra):
    return client.post("/knowledge/ask", json={"question": question, **extra})


# --- 1: claim-fee question answers.


def test_claim_fee_question_answers(client, golden_cases):
    resp = _ask(client, CLAIM_FEE_QUESTION)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "answered"
    assert "hold" in body["answer"]
    assert body["matched_case_slug"] == "claim-fee-basic"
    assert body["retrieval_count"] > 0


# --- 2: default index is public.


def test_default_index_is_public(client, db_session, golden_cases):
    resp = _ask(client, CLAIM_FEE_QUESTION)  # no index field
    assert resp.status_code == 200
    log = db_session.query(models.KnowledgeQueryLog).one()
    assert log.index_used == "public"
    assert log.caller_role == "public"


# --- 3: public endpoint rejects index = cx; arbitrary tiers rejected too.


def test_public_endpoint_rejects_cx_index(client, golden_cases):
    resp = _ask(client, CLAIM_FEE_QUESTION, index="cx")
    assert resp.status_code == 403
    assert "docs/policy/cx/" not in resp.text


def test_public_endpoint_rejects_arbitrary_index(client, golden_cases):
    for index in ("internal", "all", "admin"):
        resp = _ask(client, CLAIM_FEE_QUESTION, index=index)
        assert resp.status_code == 422, (index, resp.text)


# --- 4–5: answerable questions carry Sources; claim-fee cites its doc.


def test_answer_includes_sources(client, golden_cases):
    body = _ask(client, CLAIM_FEE_QUESTION).json()
    assert body["sources"], body
    for source in body["sources"]:
        assert source["doc_path"].startswith("docs/policy/public/")
        assert source["title"]
        assert isinstance(source["source_decisions"], list)
    assert "Sources:" in body["answer"]


def test_claim_fee_answer_cites_claim_fee_doc(client, golden_cases):
    body = _ask(client, CLAIM_FEE_QUESTION).json()
    paths = [s["doc_path"] for s in body["sources"]]
    assert "docs/policy/public/claim-fee.md" in paths
    decisions = {d for s in body["sources"] for d in s["source_decisions"]}
    assert "D214" in decisions


# --- 6: contact-support answer includes support@zelbi.ai.


def test_contact_support_answer_includes_support_email(client, golden_cases):
    body = _ask(client, "How do I contact Zelbi support?").json()
    assert body["outcome"] == "answered"
    assert "support@zelbi.ai" in body["answer"]


# --- 7: card-hold-expiry D212 probe refuses safely.


def test_card_hold_expiry_probe_refuses_safely(client, golden_cases):
    resp = _ask(client, D212_PROBE_QUESTION)
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "refused"
    assert body["answer"] == REFUSAL_TEXT
    assert "support@zelbi.ai" in body["answer"]
    assert body["sources"] == []
    assert body["retrieval_count"] == 0
    # The matched probe slug names the deny-listed decision; it must not
    # surface, so refusals never return a matched_case_slug.
    assert body["matched_case_slug"] is None
    assert not re.search(r"d212", resp.text, re.IGNORECASE)


# --- 8–10: hard leaks over every seeded question, raw response body.


def test_d212_never_appears_in_response_body(client, golden_cases):
    for question in _seed_questions():
        resp = _ask(client, question)
        assert resp.status_code == 200, (question, resp.text)
        assert not re.search(r"d212", resp.text, re.IGNORECASE), question


def test_internal_doc_paths_never_appear_in_response_body(client, golden_cases):
    for question in _seed_questions():
        resp = _ask(client, question)
        assert "docs/policy/internal" not in resp.text, question


def test_public_response_never_cites_cx_docs(client, golden_cases):
    for question in _seed_questions():
        resp = _ask(client, question)
        assert "docs/policy/cx/" not in resp.text, question
        paths = [s["doc_path"] for s in resp.json()["sources"]]
        assert all(p.startswith("docs/policy/public/") for p in paths), (
            question,
            paths,
        )


# --- 11–12: request validation.


def test_missing_question_returns_validation_error(client, golden_cases):
    resp = client.post("/knowledge/ask", json={})
    assert resp.status_code == 422


def test_empty_question_returns_validation_error(client, golden_cases):
    for question in ("", "   ", "\n\t"):
        resp = _ask(client, question)
        assert resp.status_code == 422, repr(question)


# --- 13: unknown question falls back to the safe refusal.


def test_unknown_question_returns_safe_refusal(client, golden_cases):
    body = _ask(client, "What is the capital of France?").json()
    assert body["outcome"] == "refused"
    assert body["answer"] == REFUSAL_TEXT
    assert "support@zelbi.ai" in body["answer"]
    assert body["sources"] == []
    assert body["matched_case_slug"] is None


# --- CX route: admin-auth per §10; public callers cannot reach the CX index.


def test_cx_route_requires_auth(client, golden_cases):
    resp = client.post("/knowledge/cx/ask", json={"question": CLAIM_FEE_QUESTION})
    assert resp.status_code == 401


def test_cx_route_rejects_non_admin(auth_client, picker_user, golden_cases):
    resp = auth_client(picker_user).post(
        "/knowledge/cx/ask", json={"question": CLAIM_FEE_QUESTION}
    )
    assert resp.status_code == 403


def test_cx_route_answers_cx_question_for_admin(
    auth_client, admin_user, db_session, golden_cases
):
    resp = auth_client(admin_user).post(
        "/knowledge/cx/ask",
        json={"question": "How do I process a refund for an upheld dispute?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "answered"
    paths = [s["doc_path"] for s in body["sources"]]
    assert "docs/policy/cx/cx-dispute-resolution.md" in paths
    log = db_session.query(models.KnowledgeQueryLog).one()
    assert log.index_used == "cx"
    assert log.caller_role == "cx"
    assert log.caller_id_hash == hashlib.sha256(
        str(admin_user.id).encode()
    ).hexdigest()


# --- Query logging on the public route.


def test_public_ask_writes_query_log(client, db_session, golden_cases):
    _ask(client, D212_PROBE_QUESTION)
    log = db_session.query(models.KnowledgeQueryLog).one()
    assert log.index_used == "public"
    assert log.caller_id_hash is None
    assert log.outcome == "refused_no_answer"
    assert log.retrieved_chunk_ids == []
    assert log.query_text == D212_PROBE_QUESTION


# --- 14: the endpoint makes no external network calls.


def test_endpoint_makes_no_external_api_calls(client, golden_cases, monkeypatch):
    real_getaddrinfo = socket.getaddrinfo
    local_hosts = {"localhost", "127.0.0.1", "::1", None}

    def guarded(host, *args, **kwargs):
        if host not in local_hosts:
            raise AssertionError(f"external network lookup attempted: {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
    assert _ask(client, CLAIM_FEE_QUESTION).json()["outcome"] == "answered"
    assert _ask(client, D212_PROBE_QUESTION).json()["outcome"] == "refused"


# --- 15: the answer eval still passes 22/22 with the router wired in.


def test_answer_eval_still_passes_after_endpoint_wiring(db_session, golden_cases):
    run = run_answer_eval(db_session, git_commit="phase6a-endpoint")
    assert run.cases_total == 22
    assert run.cases_passed == 22
    assert run.cases_failed == 0
    assert run.leak_failures == 0

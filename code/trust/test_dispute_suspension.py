"""Phase 9-1 D67 — picker auto-suspension by 90-day rolling dispute count."""
import uuid
from datetime import datetime, timedelta

import httpx
import pytest

from app import models
from app.routers.claims import KNOWN_DISCLOSURE_VERSIONS
from app.services import notification_service, strike_service
from app.services.strike_service import (
    _D67_SUSPENSION_PUSH_BODY,
    check_and_apply_dispute_suspension,
)

_DISCLOSURE_VERSION = next(iter(KNOWN_DISCLOSURE_VERSIONS))


@pytest.fixture(autouse=True)
def sent_emails(monkeypatch) -> list[dict]:
    recorded: list[dict] = []

    def _fake_send_email(*, to, subject, html, text=None):
        recorded.append({"to": to, "subject": subject, "html": html, "text": text})

    # strike_service imports send_email directly (not via standing_notices),
    # so the stub target is the name bound in strike_service's own namespace.
    monkeypatch.setattr(strike_service, "send_email", _fake_send_email)
    return recorded


def _patch_httpx(mocker):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_client = mocker.MagicMock()
    mock_client.post.return_value = mock_response
    cls = mocker.patch.object(notification_service.httpx, "Client")
    cls.return_value.__enter__.return_value = mock_client
    return mock_client.post


def _give_user_token(db_session, user):
    user.expo_push_token = f"ExponentPushToken[{uuid.uuid4().hex[:10]}]"
    db_session.commit()
    db_session.refresh(user)


def _add_dispute_event(db_session, user_id, *, days_ago: int = 1):
    event = models.TrustEvent(
        user_id=user_id,
        event_type="dispute_lost_picker",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db_session.add(event)
    db_session.commit()


def test_one_dispute_no_suspension_no_warning(
    mocker, db_session, picker_user,
):
    _give_user_token(db_session, picker_user)
    mock_post = _patch_httpx(mocker)
    _add_dispute_event(db_session, picker_user.id)

    check_and_apply_dispute_suspension(db_session, picker_user.id)

    db_session.expire_all()
    fresh = db_session.get(models.User, picker_user.id)
    assert fresh.is_suspended is False
    assert mock_post.call_count == 0


def test_two_disputes_fires_warning_push_no_suspension(
    mocker, db_session, picker_user,
):
    _give_user_token(db_session, picker_user)
    mock_post = _patch_httpx(mocker)
    for _ in range(2):
        _add_dispute_event(db_session, picker_user.id)

    check_and_apply_dispute_suspension(db_session, picker_user.id)

    db_session.expire_all()
    fresh = db_session.get(models.User, picker_user.id)
    assert fresh.is_suspended is False
    assert mock_post.call_count == 1
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args.args[1]
    assert payload["title"] == "Account warning"
    assert (
        payload["body"]
        == "One more lost dispute will suspend your account."
    )


def test_three_disputes_suspends_user_and_fires_suspension_push(
    mocker, db_session, picker_user, sent_emails,
):
    _give_user_token(db_session, picker_user)
    mock_post = _patch_httpx(mocker)
    for _ in range(3):
        _add_dispute_event(db_session, picker_user.id)

    check_and_apply_dispute_suspension(db_session, picker_user.id)
    db_session.commit()

    db_session.expire_all()
    fresh = db_session.get(models.User, picker_user.id)
    assert fresh.is_suspended is True
    assert fresh.suspension_reason == _D67_SUSPENSION_PUSH_BODY

    assert mock_post.call_count == 1
    payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args.args[1]
    assert payload["title"] == "Account suspended"
    assert (
        payload["body"]
        == "Your account has been suspended after losing 3 disputes in 90 days. "
        "Contact support if you believe this is in error."
    )

    action = (
        db_session.query(models.AdminAction)
        .filter(
            models.AdminAction.subject_user_id == picker_user.id,
            models.AdminAction.action == "suspend",
        )
        .one()
    )
    assert action.actor_user_id is None
    assert action.reason == _D67_SUSPENSION_PUSH_BODY
    assert action.notice_sent is True

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "Account disabled"


def test_two_disputes_warning_records_action_and_sends_email(
    mocker, db_session, picker_user, sent_emails,
):
    _give_user_token(db_session, picker_user)
    _patch_httpx(mocker)
    for _ in range(2):
        _add_dispute_event(db_session, picker_user.id)

    check_and_apply_dispute_suspension(db_session, picker_user.id)
    db_session.commit()

    action = (
        db_session.query(models.AdminAction)
        .filter(
            models.AdminAction.subject_user_id == picker_user.id,
            models.AdminAction.action == "warn",
        )
        .one()
    )
    assert action.actor_user_id is None
    assert action.notice_sent is True

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "Account warning"


def test_old_disputes_outside_90d_window_excluded(
    mocker, db_session, picker_user,
):
    _give_user_token(db_session, picker_user)
    mock_post = _patch_httpx(mocker)
    for _ in range(3):
        _add_dispute_event(db_session, picker_user.id, days_ago=91)

    check_and_apply_dispute_suspension(db_session, picker_user.id)

    db_session.expire_all()
    fresh = db_session.get(models.User, picker_user.id)
    assert fresh.is_suspended is False
    assert mock_post.call_count == 0


def test_already_suspended_user_is_idempotent_no_extra_push(
    mocker, db_session, picker_user,
):
    _give_user_token(db_session, picker_user)
    mock_post = _patch_httpx(mocker)
    picker_user.is_suspended = True
    db_session.commit()
    for _ in range(3):
        _add_dispute_event(db_session, picker_user.id)

    check_and_apply_dispute_suspension(db_session, picker_user.id)

    assert mock_post.call_count == 0


def test_resolve_upheld_giver_at_third_dispute_suspends_picker(
    mocker, auth_client, db_session, picker_user, giver_user, authorized_claim,
):
    """End-to-end: admin resolves upheld_giver at the 3rd dispute → suspension fires."""
    _give_user_token(db_session, picker_user)
    _patch_httpx(mocker)
    # Pre-seed 2 dispute_lost_picker events; resolving will write the 3rd.
    for _ in range(2):
        _add_dispute_event(db_session, picker_user.id, days_ago=10)

    dispute = models.Dispute(
        claim_id=authorized_claim.id,
        filer_user_id=picker_user.id,
        reason_text="x" * 100,
        acknowledged=True,
        status="pending",
    )
    db_session.add(dispute)
    db_session.commit()
    db_session.refresh(dispute)

    giver_user.is_admin = True
    db_session.commit()
    resp = auth_client(giver_user).post(
        f"/admin/disputes/{dispute.id}/resolve",
        json={"resolution": "upheld_giver"},
    )
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    fresh = db_session.get(models.User, picker_user.id)
    assert fresh.is_suspended is True


def test_suspended_picker_blocked_from_claims_endpoint(
    auth_client, db_session, picker_user, active_listing,
):
    """D67 + dependencies.py get_current_user gate — suspended picker cannot
    create new claims; /claims returns 403."""
    picker_user.is_suspended = True
    picker_user.suspension_reason = "auto_suspended_dispute_threshold"
    db_session.commit()
    db_session.refresh(picker_user)

    resp = auth_client(picker_user).post(
        "/claims",
        json={
            "listing_id": str(active_listing.id),
            "disclosure_version": _DISCLOSURE_VERSION,
        },
    )
    assert resp.status_code == 403, resp.text

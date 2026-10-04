"""Admin actions — suspend, lift and time out a user's standing."""
import pytest

from app import models
from app.services import standing_notices


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


@pytest.fixture(autouse=True)
def sent_emails(monkeypatch) -> list[dict]:
    recorded: list[dict] = []

    def _fake_send_email(*, to, subject, html, text=None):
        recorded.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr(standing_notices, "send_email", _fake_send_email)
    return recorded


def test_suspend_sets_flag_writes_action_and_shows_in_users_list(
    auth_client, admin_user, picker_user, db_session,
):
    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["standing"] == "suspended"
    assert body["suspension_reason"] == "Repeated no-shows"

    action = (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .one()
    )
    assert action.action == "suspend"
    assert action.reason == "Repeated no-shows"
    assert action.actor_user_id == admin_user.id

    users_resp = auth_client(admin_user).get("/admin/users")
    assert users_resp.status_code == 200
    row = next(u for u in users_resp.json() if u["id"] == str(picker_user.id))
    assert row["standing"] == "suspended"
    assert row["standing_since"] is not None
    assert row["standing_reason"] == "Repeated no-shows"
    assert row["standing_notice"] is True


def test_suspended_user_is_told_the_recorded_reason(
    auth_client, admin_user, picker_user, db_session,
):
    suspend_resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert suspend_resp.status_code == 200
    db_session.refresh(picker_user)

    resp = auth_client(picker_user).get("/auth/me")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Repeated no-shows"


def test_suspending_twice_is_conflict(auth_client, admin_user, picker_user):
    first = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert first.status_code == 200

    second = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Again"},
    )
    assert second.status_code == 409


def test_blank_reason_is_unprocessable(auth_client, admin_user, picker_user):
    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "   "},
    )
    assert resp.status_code == 422


def test_lift_clears_suspension_and_writes_its_own_action(
    auth_client, admin_user, picker_user, db_session,
):
    suspend_resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert suspend_resp.status_code == 200

    lift_resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/lift",
        json={"reason": "Appeal accepted"},
    )
    assert lift_resp.status_code == 200
    body = lift_resp.json()
    assert body["standing"] == "ok"
    assert body["suspension_reason"] is None

    actions = (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .order_by(models.AdminAction.at)
        .all()
    )
    assert [a.action for a in actions] == ["suspend", "lift"]
    assert actions[-1].reason == "Appeal accepted"


def test_timeout_sets_a_date_days_ahead(auth_client, admin_user, picker_user):
    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/timeout",
        json={"reason": "Missed pickup window", "days": 14},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["standing"] == "timeout"
    assert body["timeout_until"] is not None


def test_timeout_over_an_expired_one_reads_timeout_in_the_future(
    auth_client, admin_user, picker_user, db_session,
):
    from datetime import datetime, timedelta, timezone

    picker_user.picker_timeout_until = datetime.utcnow() - timedelta(hours=1)
    db_session.add(picker_user)
    db_session.commit()

    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/timeout",
        json={"reason": "Missed pickup window", "days": 7},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["standing"] == "timeout"
    assert body["timeout_until"] is not None
    assert datetime.fromisoformat(body["timeout_until"]) > datetime.now(timezone.utc)


def test_timeout_is_refused_while_suspended(auth_client, admin_user, picker_user):
    suspend_resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert suspend_resp.status_code == 200

    timeout_resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/timeout",
        json={"reason": "Missed pickup window"},
    )
    assert timeout_resp.status_code == 409


def test_non_admin_is_forbidden_on_all_three(auth_client, other_picker_user, picker_user):
    body = {"reason": "Repeated no-shows"}
    suspend_resp = auth_client(other_picker_user).post(
        f"/admin/users/{picker_user.id}/suspend", json=body,
    )
    lift_resp = auth_client(other_picker_user).post(
        f"/admin/users/{picker_user.id}/lift", json=body,
    )
    timeout_resp = auth_client(other_picker_user).post(
        f"/admin/users/{picker_user.id}/timeout", json=body,
    )
    assert suspend_resp.status_code == 403
    assert lift_resp.status_code == 403
    assert timeout_resp.status_code == 403


def test_suspend_sends_notice_email(
    auth_client, admin_user, picker_user, db_session, sent_emails,
):
    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert resp.status_code == 200
    assert resp.json()["notice_sent"] is True

    assert len(sent_emails) == 1
    sent = sent_emails[0]
    assert sent["to"] == picker_user.email
    assert sent["subject"] == "Account disabled"
    assert sent["text"].startswith("Account disabled\n\nHi User,\n\nRepeated no-shows\n\n")
    assert "Repeated no-shows" in sent["html"]
    assert "zelbi.ai" in sent["text"]

    action = (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .one()
    )
    assert action.notice_sent is True


def test_lift_sends_notice_email(auth_client, admin_user, picker_user, sent_emails):
    auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    sent_emails.clear()

    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/lift",
        json={"reason": "Appeal accepted"},
    )
    assert resp.status_code == 200
    assert resp.json()["notice_sent"] is True
    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == "Account restored"


def test_timeout_sends_notice_email_with_resume_date(
    auth_client, admin_user, picker_user, sent_emails,
):
    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/timeout",
        json={"reason": "Missed pickup window", "days": 14},
    )
    assert resp.status_code == 200
    assert resp.json()["notice_sent"] is True
    assert len(sent_emails) == 1
    assert "You can claim again from" in sent_emails[0]["text"]


def test_send_failure_leaves_notice_sent_false_but_action_still_applies(
    auth_client, admin_user, picker_user, db_session, monkeypatch,
):
    def _boom(**kwargs):
        raise RuntimeError("resend is down")

    monkeypatch.setattr(standing_notices, "send_email", _boom)

    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert resp.status_code == 200
    assert resp.json()["standing"] == "suspended"
    assert resp.json()["notice_sent"] is False

    action = (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .one()
    )
    assert action.notice_sent is False


def test_suspending_an_admin_is_conflict_with_no_action_and_no_email(
    auth_client, admin_user, picker_user, db_session, sent_emails,
):
    picker_user.is_admin = True
    db_session.commit()

    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/suspend",
        json={"reason": "Repeated no-shows"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "An admin account cannot be suspended or timed out"

    db_session.expire_all()
    assert db_session.get(models.User, picker_user.id).is_suspended is False
    assert (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .count()
        == 0
    )
    assert sent_emails == []


def test_timing_out_an_admin_is_conflict_with_no_action_and_no_email(
    auth_client, admin_user, picker_user, db_session, sent_emails,
):
    picker_user.is_admin = True
    db_session.commit()

    resp = auth_client(admin_user).post(
        f"/admin/users/{picker_user.id}/timeout",
        json={"reason": "Missed pickup window", "days": 7},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "An admin account cannot be suspended or timed out"

    db_session.expire_all()
    assert db_session.get(models.User, picker_user.id).picker_timeout_until is None
    assert (
        db_session.query(models.AdminAction)
        .filter(models.AdminAction.subject_user_id == picker_user.id)
        .count()
        == 0
    )
    assert sent_emails == []

"""Admin flags list — GET /admin/flags in the seed shape."""
import pytest

from app import models
from app.services import standing_notices
from app.services.scam_detection import RULE_DEFINITIONS


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


def _auto_report(db_session, *, reported_user_id, listing_id=None, triggered_rule="rule_2", status="pending"):
    report = models.Report(
        reported_user_id=reported_user_id,
        listing_id=listing_id,
        reason="scam",
        description="Automated scan flagged this content.",
        status=status,
        source="auto",
        triggered_rule=triggered_rule,
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


def test_auto_report_on_listing_lists_with_rule_and_giver_role(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(
        db_session, reported_user_id=giver_user.id, listing_id=active_listing.id,
    )

    resp = auth_client(admin_user).get("/admin/flags")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    row = next(r for r in rows if r["report_id"] == str(report.id))

    assert row["rule"] == "r2"
    assert row["on"] == "listing"
    assert row["ref"] == "L-" + str(active_listing.id)[:6].upper()
    assert row["user"] == giver_user.display_name
    assert row["role"] == "Giver"
    assert row["st"] == "pending"


def test_user_sourced_report_is_absent(
    auth_client, admin_user, db_session, picker_user, active_listing,
):
    report = models.Report(
        reported_user_id=picker_user.id,
        listing_id=active_listing.id,
        reason="scam",
        description="A user reported this.",
        status="pending",
        source="user",
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    resp = auth_client(admin_user).get("/admin/flags")
    assert resp.status_code == 200
    ids = [r["report_id"] for r in resp.json()]
    assert str(report.id) not in ids


def test_non_admin_is_forbidden(auth_client, picker_user):
    resp = auth_client(picker_user).get("/admin/flags")
    assert resp.status_code == 403


def _flag_row(auth_client, admin_user, report):
    resp = auth_client(admin_user).get("/admin/flags")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json() if r["report_id"] == str(report.id))


def _actions(db_session, action):
    db_session.expire_all()
    return db_session.query(models.AdminAction).filter(models.AdminAction.action == action).all()


def test_flag_row_carries_backend_rule_label(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    row = _flag_row(auth_client, admin_user, report)

    assert (row["rule_label"], row["rule_text"]) == RULE_DEFINITIONS["rule_2"]


def test_unknown_rule_value_falls_back_to_raw_value(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(
        db_session, reported_user_id=giver_user.id, listing_id=active_listing.id, triggered_rule="rule_x",
    )

    row = _flag_row(auth_client, admin_user, report)

    assert row["rule_label"] == "rule_x"


def test_every_stored_rule_value_has_a_definition():
    assert {"rule_2", "rule_3", "rule_5", "rule_6", "block_ended_claim"} <= RULE_DEFINITIONS.keys()


def test_confirm_resolves_emails_and_records(
    auth_client, admin_user, db_session, giver_user, active_listing, sent_emails,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    resp = auth_client(admin_user).post(
        f"/admin/flags/{report.id}/confirm", json={"note": "Second listing in ten seconds."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["notice_sent"] is True

    db_session.expire_all()
    fresh = db_session.get(models.Report, report.id)
    assert fresh.status == "resolved"
    assert fresh.resolved_at is not None

    assert len(sent_emails) == 1
    assert sent_emails[0]["subject"] == f"Warning · {active_listing.title}"
    assert "Reference R-" in sent_emails[0]["text"]

    actions = _actions(db_session, "flag_warn")
    assert len(actions) == 1
    assert actions[0].details["report_id"] == str(report.id)


def test_confirm_on_decided_flag_is_409(
    auth_client, admin_user, db_session, giver_user, active_listing, sent_emails,
):
    report = _auto_report(
        db_session, reported_user_id=giver_user.id, listing_id=active_listing.id, status="resolved",
    )

    resp = auth_client(admin_user).post(f"/admin/flags/{report.id}/confirm", json={})

    assert resp.status_code == 409
    assert sent_emails == []


def test_false_positive_dismisses_without_email(
    auth_client, admin_user, db_session, giver_user, active_listing, sent_emails,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    resp = auth_client(admin_user).post(f"/admin/flags/{report.id}/false-positive", json={"note": "Rule misfired"})
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    assert db_session.get(models.Report, report.id).status == "dismissed"
    assert sent_emails == []
    assert len(_actions(db_session, "flag_false_positive")) == 1
    assert _flag_row(auth_client, admin_user, report)["st"] == "dismissed"


def test_escalate_before_suspend_is_409(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    resp = auth_client(admin_user).post(f"/admin/flags/{report.id}/escalate", json={"reason": "Repeat offender"})

    assert resp.status_code == 409


def test_escalate_after_suspend_resolves_and_records(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    suspend = auth_client(admin_user).post(
        f"/admin/users/{giver_user.id}/suspend", json={"reason": "Automated scan flagged this content."},
    )
    assert suspend.status_code == 200, suspend.text
    resp = auth_client(admin_user).post(
        f"/admin/flags/{report.id}/escalate", json={"reason": "Automated scan flagged this content."},
    )
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    assert db_session.get(models.Report, report.id).status == "resolved"
    assert len(_actions(db_session, "flag_escalate")) == 1


def test_decided_flag_lists_decider(
    auth_client, admin_user, db_session, giver_user, active_listing,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)

    resp = auth_client(admin_user).post(f"/admin/flags/{report.id}/confirm", json={})
    assert resp.status_code == 200, resp.text

    row = _flag_row(auth_client, admin_user, report)
    assert row["decided_by"] == admin_user.display_name
    assert row["decided_at"] is not None


def test_flag_decision_routes_non_admin_forbidden(
    auth_client, picker_user, db_session, giver_user, active_listing,
):
    report = _auto_report(db_session, reported_user_id=giver_user.id, listing_id=active_listing.id)
    client = auth_client(picker_user)

    assert client.post(f"/admin/flags/{report.id}/confirm", json={}).status_code == 403
    assert client.post(f"/admin/flags/{report.id}/false-positive", json={}).status_code == 403
    assert client.post(f"/admin/flags/{report.id}/escalate", json={"reason": "x"}).status_code == 403

"""D542 (4), D543: the iPhone check on a giveaway credit. POST /users/me/device-check runs
Apple's query and update on its own endpoint, serialized by one advisory lock, never inside
claim creation. Apple is mocked at devicecheck_service's functions; no test reaches Apple.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.config import settings
from app.routers import users as users_router
from app.services import devicecheck_service as dc
from app.services.credit_service import pending_device_check_credit

TOKEN = "device-token-never-logged"


def _credit(db_session, user, *, kind="giveaway", used=False, checked=False, refused=False,
            referred_user_id=None) -> models.Credit:
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id,
        kind=kind,
        referred_user_id=referred_user_id,
        earned_at=now,
        expires_at=now + timedelta(days=90),
        used_at=now if used else None,
        device_checked_at=now if checked else None,
        device_check_refused_at=now if refused else None,
    )
    db_session.add(credit)
    db_session.commit()
    db_session.refresh(credit)
    return credit


def _reload(db_session, credit) -> models.Credit:
    db_session.expire_all()
    return db_session.get(models.Credit, credit.id)


def _watcher_rows(db_session) -> list[models.WatcherEvent]:
    db_session.expire_all()
    return db_session.query(models.WatcherEvent).all()


@pytest.fixture(autouse=True)
def _apple_never_reached(mocker, monkeypatch):
    """Every test mocks query/update; the HTTP client must never be built."""
    def _no_client():
        raise AssertionError("Apple DeviceCheck must not be reached from tests")
    mocker.patch.object(dc, "_client", _no_client)
    monkeypatch.setattr(settings, "apple_devicecheck_environment", "development")
    # The suite's alembic fileConfig disables loggers that existed before it ran; re-enable
    # the router's logger so caplog can read its JSON events.
    monkeypatch.setattr(users_router.logger, "disabled", False)


@pytest.fixture
def apple(mocker):
    query = mocker.patch("app.services.devicecheck_service.query_two_bits", return_value=None)
    update = mocker.patch("app.services.devicecheck_service.update_two_bits", return_value=None)
    return query, update


def _post(auth_client, user, token=TOKEN):
    return auth_client(user).post("/users/me/device-check", json={"device_token": token})


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

def test_pass_stamps_device_checked_at_and_sets_bit0(auth_client, db_session, picker_user, apple):
    query, update = apple
    query.return_value = None  # Apple has no bits for this iPhone yet
    credit = _credit(db_session, picker_user)

    resp = _post(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "passed"}

    query.assert_called_once_with(TOKEN)
    update.assert_called_once_with(TOKEN, bit0=True, bit1=False)
    row = _reload(db_session, credit)
    assert row.device_checked_at is not None
    assert row.device_check_refused_at is None
    assert _watcher_rows(db_session) == []
    assert pending_device_check_credit(db_session, picker_user.id) is None


def test_pass_with_bits_present_and_bit0_false(auth_client, db_session, picker_user, apple):
    query, update = apple
    query.return_value = dc.Bits(bit0=False, bit1=False, last_update_time="2026-08")
    credit = _credit(db_session, picker_user)

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    update.assert_called_once_with(TOKEN, bit0=True, bit1=False)
    assert _reload(db_session, credit).device_checked_at is not None


def test_pass_keeps_apples_bit1_when_already_set(auth_client, db_session, picker_user, apple):
    # D545 survey, C: the write sends both bits and passes bit1 back unchanged.
    query, update = apple
    query.return_value = dc.Bits(bit0=False, bit1=True, last_update_time="2026-09")
    credit = _credit(db_session, picker_user)

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    update.assert_called_once_with(TOKEN, bit0=True, bit1=True)
    assert _reload(db_session, credit).device_checked_at is not None


def test_bit0_already_set_refuses_writes_no_update_and_one_alert(
    auth_client, db_session, picker_user, apple, caplog,
):
    query, update = apple
    query.return_value = dc.Bits(bit0=True, bit1=False, last_update_time="2026-09")
    credit = _credit(db_session, picker_user)

    with caplog.at_level(logging.INFO, logger="app.routers.users"):
        resp = _post(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "refused"}

    update.assert_not_called()
    row = _reload(db_session, credit)
    assert row.device_check_refused_at is not None
    assert row.device_checked_at is None
    assert row.used_at is None  # the record stays, unusable (D543 (1))
    assert pending_device_check_credit(db_session, picker_user.id) is None

    rows = _watcher_rows(db_session)
    assert len(rows) == 1
    alert = rows[0]
    assert alert.family == "account"
    assert alert.kind == "giveaway_credit_device_refused"
    assert alert.who == str(picker_user.id)
    assert alert.ref == str(credit.id)
    assert alert.source == "zelbi"
    assert alert.source_id == f"devicecheck-refused:{credit.id}"
    assert alert.state == "pending"
    assert alert.severity == 4

    events = [json.loads(r.getMessage()) for r in caplog.records if r.name == "app.routers.users"]
    refused = [e for e in events if e["event"] == "giveaway_credit_device_refused"]
    assert len(refused) == 1
    assert refused[0]["credit_id"] == str(credit.id)
    for record in caplog.records:
        assert TOKEN not in record.getMessage()


def test_no_pending_credit_is_not_needed_and_never_calls_apple(
    auth_client, db_session, picker_user, other_picker_user, apple,
):
    query, update = apple
    # No credit at all.
    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "not_needed"}
    # A checked one, a refused one, a used one, and a referral credit: none needs a check.
    _credit(db_session, picker_user, used=True)
    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "not_needed"}
    _credit(db_session, other_picker_user, kind="referral", referred_user_id=picker_user.id)
    resp = _post(auth_client, other_picker_user)
    assert resp.json() == {"result": "not_needed"}
    query.assert_not_called()
    update.assert_not_called()
    assert _watcher_rows(db_session) == []


@pytest.mark.parametrize("state", ["checked", "refused"])
def test_already_decided_credit_is_not_needed(auth_client, db_session, picker_user, apple, state):
    query, update = apple
    _credit(db_session, picker_user, checked=state == "checked", refused=state == "refused")
    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "not_needed"}
    query.assert_not_called()
    update.assert_not_called()


def test_query_error_writes_nothing_and_is_unavailable(auth_client, db_session, picker_user, apple, caplog):
    query, update = apple
    query.side_effect = dc.DeviceCheckError("Apple DeviceCheck answered 503", status_code=503)
    credit = _credit(db_session, picker_user)

    with caplog.at_level(logging.ERROR, logger="app.routers.users"):
        resp = _post(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "unavailable"}

    update.assert_not_called()
    row = _reload(db_session, credit)
    assert row.device_checked_at is None
    assert row.device_check_refused_at is None
    assert _watcher_rows(db_session) == []
    # Still pending: the next app open retries.
    assert pending_device_check_credit(db_session, picker_user.id) is not None
    errors = [r for r in caplog.records if r.levelno == logging.ERROR and r.name == "app.routers.users"]
    assert errors and json.loads(errors[0].getMessage())["event"] == "giveaway_credit_device_check_unavailable"
    for record in caplog.records:
        assert TOKEN not in record.getMessage()


def test_update_error_then_success_on_the_retry_passes(auth_client, db_session, picker_user, apple):
    query, update = apple
    query.return_value = None
    update.side_effect = [dc.DeviceCheckError("Apple DeviceCheck answered 500", status_code=500), None]
    credit = _credit(db_session, picker_user)

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    assert update.call_count == 2
    for call in update.call_args_list:
        assert call.args == (TOKEN,) and call.kwargs == {"bit0": True, "bit1": False}
    assert _reload(db_session, credit).device_checked_at is not None


def test_two_update_errors_write_nothing_and_are_unavailable(
    auth_client, db_session, picker_user, apple, caplog,
):
    query, update = apple
    query.return_value = None
    update.side_effect = dc.DeviceCheckError("Apple DeviceCheck answered 429", status_code=429)
    credit = _credit(db_session, picker_user)

    with caplog.at_level(logging.ERROR, logger="app.routers.users"):
        resp = _post(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "unavailable"}
    assert update.call_count == 2
    row = _reload(db_session, credit)
    assert row.device_checked_at is None
    assert row.device_check_refused_at is None
    assert _watcher_rows(db_session) == []
    assert pending_device_check_credit(db_session, picker_user.id) is not None
    errors = [r for r in caplog.records if r.levelno == logging.ERROR and r.name == "app.routers.users"]
    assert len(errors) == 1


def test_another_users_credit_is_untouched(auth_client, db_session, picker_user, other_picker_user, apple):
    query, update = apple
    query.return_value = None
    mine = _credit(db_session, picker_user)
    theirs = _credit(db_session, other_picker_user)

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    assert _reload(db_session, mine).device_checked_at is not None
    other = _reload(db_session, theirs)
    assert other.device_checked_at is None
    assert other.device_check_refused_at is None
    assert pending_device_check_credit(db_session, other_picker_user.id) is not None


def test_device_token_is_required(auth_client, picker_user, apple):
    resp = auth_client(picker_user).post("/users/me/device-check", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# The me flag
# ---------------------------------------------------------------------------

def _me_flag(auth_client, user) -> bool:
    resp = auth_client(user).get("/auth/me")
    assert resp.status_code == 200, resp.text
    return resp.json()["giveaway_credit_needs_device_check"]


def _me_flag_from_users_builder(auth_client, user) -> bool:
    resp = auth_client(user).post("/users/me/accept-terms", json={"version": "terms-2026-09-01"})
    assert resp.status_code == 200, resp.text
    return resp.json()["giveaway_credit_needs_device_check"]


def test_me_flag_true_with_pending_credit_and_false_after_pass(
    auth_client, db_session, picker_user, apple,
):
    query, _ = apple
    query.return_value = None
    assert _me_flag(auth_client, picker_user) is False
    assert _me_flag_from_users_builder(auth_client, picker_user) is False
    _credit(db_session, picker_user)
    assert _me_flag(auth_client, picker_user) is True
    assert _me_flag_from_users_builder(auth_client, picker_user) is True
    assert _post(auth_client, picker_user).json() == {"result": "passed"}
    assert _me_flag(auth_client, picker_user) is False
    assert _me_flag_from_users_builder(auth_client, picker_user) is False


def test_me_flag_false_after_refusal(auth_client, db_session, picker_user, apple):
    query, _ = apple
    query.return_value = dc.Bits(bit0=True, bit1=False, last_update_time="2026-09")
    _credit(db_session, picker_user)
    assert _me_flag(auth_client, picker_user) is True
    assert _post(auth_client, picker_user).json() == {"result": "refused"}
    assert _me_flag(auth_client, picker_user) is False
    assert _me_flag_from_users_builder(auth_client, picker_user) is False


def test_me_flag_false_with_no_credit_or_only_a_referral_credit(
    auth_client, db_session, picker_user, other_picker_user,
):
    assert _me_flag(auth_client, picker_user) is False
    _credit(db_session, picker_user, kind="referral", referred_user_id=other_picker_user.id)
    assert _me_flag(auth_client, picker_user) is False
    _credit(db_session, other_picker_user, used=True)
    assert _me_flag(auth_client, other_picker_user) is False


# ---------------------------------------------------------------------------
# The development-only reset (D543 (6))
# ---------------------------------------------------------------------------

def _reset(auth_client, user, token=TOKEN):
    return auth_client(user).post("/users/me/device-check/reset", json={"device_token": token})


def test_reset_is_404_against_production(auth_client, db_session, picker_user, apple, monkeypatch):
    query, update = apple
    monkeypatch.setattr(settings, "apple_devicecheck_environment", "production")
    credit = _credit(db_session, picker_user, checked=True)
    resp = _reset(auth_client, picker_user)
    assert resp.status_code == 404
    update.assert_not_called()
    query.assert_not_called()
    assert _reload(db_session, credit).device_checked_at is not None


@pytest.mark.parametrize("state", ["checked", "refused"])
def test_reset_clears_both_stamps_and_sends_both_bits_false(
    auth_client, db_session, picker_user, apple, state,
):
    query, update = apple
    credit = _credit(db_session, picker_user, checked=state == "checked", refused=state == "refused")
    assert pending_device_check_credit(db_session, picker_user.id) is None

    resp = _reset(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "reset"}
    update.assert_called_once_with(TOKEN, bit0=False, bit1=False)
    query.assert_not_called()
    row = _reload(db_session, credit)
    assert row.device_checked_at is None
    assert row.device_check_refused_at is None
    assert pending_device_check_credit(db_session, picker_user.id) is not None


def test_reset_with_no_credit_still_clears_apples_bit(auth_client, db_session, picker_user, apple):
    _, update = apple
    resp = _reset(auth_client, picker_user)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"result": "reset"}
    update.assert_called_once_with(TOKEN, bit0=False, bit1=False)


def test_reset_apple_error_is_unavailable_and_keeps_stamps(auth_client, db_session, picker_user, apple):
    _, update = apple
    update.side_effect = dc.DeviceCheckError("Apple DeviceCheck answered 503", status_code=503)
    credit = _credit(db_session, picker_user, checked=True)
    resp = _reset(auth_client, picker_user)
    assert resp.json() == {"result": "unavailable"}
    assert _reload(db_session, credit).device_checked_at is not None


# ---------------------------------------------------------------------------
# D549 (survey C5): the invite credit and bit1
# ---------------------------------------------------------------------------

from app.services.credit_service import INVITE_DEVICE_REFUSAL_KIND  # noqa: E402


def test_invite_credit_with_bit1_set_refuses_and_alerts_but_keeps_the_claim_covered(
    auth_client, db_session, picker_user, active_listing, apple, caplog,
):
    query, update = apple
    query.return_value = dc.Bits(bit0=False, bit1=True, last_update_time="2026-09")
    credit = _credit(db_session, picker_user, kind="invite")
    claim = models.Claim(
        listing_id=active_listing.id, picker_id=picker_user.id, status="authorized",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}", credit_id=credit.id,
    )
    db_session.add(claim)
    db_session.commit()

    with caplog.at_level(logging.INFO, logger="app.routers.users"):
        resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "refused"}

    update.assert_not_called()
    row = _reload(db_session, credit)
    assert row.device_check_refused_at is not None
    assert row.device_checked_at is None
    # The claim approved at apply stays covered; only reuse of the credit is stopped.
    assert db_session.get(models.Claim, claim.id).credit_id == credit.id
    rows = _watcher_rows(db_session)
    assert len(rows) == 1
    assert rows[0].kind == INVITE_DEVICE_REFUSAL_KIND
    assert rows[0].ref == str(credit.id)
    events = [json.loads(r.getMessage()) for r in caplog.records if r.name == "app.routers.users"]
    assert [e["event"] for e in events] == ["invite_credit_device_refused"]
    for record in caplog.records:
        assert TOKEN not in record.getMessage()


@pytest.mark.parametrize(
    "bits,expected_bit0",
    [(None, False), (dc.Bits(bit0=False, bit1=False, last_update_time="2026-09"), False),
     (dc.Bits(bit0=True, bit1=False, last_update_time="2026-09"), True)],
    ids=["no_bits", "both_clear", "bit0_kept"],
)
def test_invite_credit_with_bit1_clear_writes_bit1_and_keeps_bit0(
    auth_client, db_session, picker_user, apple, bits, expected_bit0,
):
    query, update = apple
    query.return_value = bits
    credit = _credit(db_session, picker_user, kind="invite")

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    update.assert_called_once_with(TOKEN, bit0=expected_bit0, bit1=True)
    row = _reload(db_session, credit)
    assert row.device_checked_at is not None
    assert row.device_check_refused_at is None
    assert _watcher_rows(db_session) == []


def test_giveaway_credit_ignores_bit1_and_passes_it_back(auth_client, db_session, picker_user, apple):
    query, update = apple
    query.return_value = dc.Bits(bit0=False, bit1=True, last_update_time="2026-09")
    credit = _credit(db_session, picker_user, kind="giveaway")

    resp = _post(auth_client, picker_user)
    assert resp.json() == {"result": "passed"}
    update.assert_called_once_with(TOKEN, bit0=True, bit1=True)
    assert _reload(db_session, credit).device_checked_at is not None


def test_me_flag_true_for_a_pending_invite_credit(auth_client, db_session, picker_user, apple):
    credit = _credit(db_session, picker_user, kind="invite")
    assert _me_flag(auth_client, picker_user) is True
    assert _me_flag_from_users_builder(auth_client, picker_user) is True
    assert pending_device_check_credit(db_session, picker_user.id).id == credit.id

    assert _post(auth_client, picker_user).json() == {"result": "passed"}
    assert _me_flag(auth_client, picker_user) is False


def test_reset_clears_the_stamps_on_both_kinds(auth_client, db_session, picker_user, apple):
    query, update = apple
    giveaway = _credit(db_session, picker_user, kind="giveaway", checked=True)
    invite = _credit(db_session, picker_user, kind="invite", refused=True)

    resp = _reset(auth_client, picker_user)
    assert resp.json() == {"result": "reset"}
    update.assert_called_once_with(TOKEN, bit0=False, bit1=False)
    for credit in (giveaway, invite):
        row = _reload(db_session, credit)
        assert row.device_checked_at is None
        assert row.device_check_refused_at is None

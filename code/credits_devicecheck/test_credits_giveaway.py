"""D539 step 4, slice 1 (D542): the first-giveaway credit is written on a completed handoff.

Every completing ending earns it for the giver — the picker's photo (confirm_pickup), the
giver's yes (confirm_collected), and each of the sweeper's silence branches — once per
person, only while the giveaway_credit switch is on. Endings that do not complete a
handoff (no_show, a late cancel, a cancel) earn nothing. Stripe is mocked exactly as the
existing completion tests mock it.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app import models
from app.models import DeletedEmailFingerprint
from app.services.credit_service import GIVEAWAY_CREDIT_PUSH_BODY
from app.utils.email_fingerprint import email_fingerprint
from tests.test_account_deletion import _delete_me
from app.jobs.post_window_sweeper import run_post_window_sweeper
from app.routers.claims import find_available_credit
from tests.test_claims import _build_authorized_claim_for, _set_pickup_scheduled_at
from tests.test_curbside_sweeper import _capturing, _make_curbside_booked
from tests.test_post_window_sweeper import _make_claim

NINETY_DAYS = timedelta(days=90)


def _giver_push_body(send_push_mock, *, call_index: int = -1) -> str:
    """The body (4th positional arg) of the "Giveaway complete" call(s) the mock recorded."""
    giver_calls = [c for c in send_push_mock.call_args_list if c.args[2] == "Giveaway complete"]
    return giver_calls[call_index].args[3]


def _giveaway_credits(db_session, user_id) -> list[models.Credit]:
    db_session.expire_all()
    return (
        db_session.query(models.Credit)
        .filter(models.Credit.user_id == user_id, models.Credit.kind == "giveaway")
        .order_by(models.Credit.earned_at.asc())
        .all()
    )


def _set_switch(db_session, enabled: bool) -> None:
    db_session.execute(
        text("UPDATE program_switches SET enabled=:e WHERE name='giveaway_credit'"),
        {"e": enabled},
    )
    db_session.commit()
    db_session.expire_all()


def _restore_switch(db_session) -> None:
    """conftest does not truncate program_switches: put the seeded row back as it was."""
    db_session.rollback()
    db_session.execute(
        text(
            "INSERT INTO program_switches (name, enabled) VALUES ('giveaway_credit', true) "
            "ON CONFLICT (name) DO UPDATE SET enabled = true"
        )
    )
    db_session.commit()
    db_session.expire_all()


# ---------------------------------------------------------------------------
# The three completion writers each earn one row
# ---------------------------------------------------------------------------

def test_confirm_pickup_earns_one_giveaway_credit_for_the_giver(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    mocker.patch("app.routers.claims.send_push")
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "completed"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    credit = credits[0]
    assert credit.kind == "giveaway"
    assert credit.source_claim_id == authorized_claim.id
    assert credit.expires_at - credit.earned_at == NINETY_DAYS
    assert credit.used_at is None
    assert credit.used_claim_id is None
    # The picker earns nothing for picking up.
    assert _giveaway_credits(db_session, picker_user.id) == []


def test_confirm_collected_earns_one_giveaway_credit(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    mocker.patch("app.routers.claims.send_push")
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/confirm-collected")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "completed"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].source_claim_id == authorized_claim.id
    assert credits[0].expires_at - credits[0].earned_at == NINETY_DAYS
    assert credits[0].used_at is None
    assert _giveaway_credits(db_session, picker_user.id) == []


def test_sweeper_pinged_branch_earns_one_giveaway_credit(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert result.errored == 0
    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "auto_captured"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].source_claim_id == claim.id
    assert credits[0].expires_at - credits[0].earned_at == NINETY_DAYS
    assert _giveaway_credits(db_session, picker_user.id) == []


def test_sweeper_24h_branch_earns_one_giveaway_credit(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="pickup_scheduled", pickup_offset_hours=-25, geofence_offset_hours=None,
    )
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "auto_captured"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].source_claim_id == claim.id


def test_sweeper_curbside_window_end_earns_one_giveaway_credit(
    db_session, picker_user, giver_user, authorized_claim, claim_in_db, mocker,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    mocker.patch(
        "app.jobs.post_window_sweeper.capture_payment_intent",
        side_effect=_capturing(db_session),
    )
    _make_curbside_booked(db_session, authorized_claim, setout_hours_ago=30, window_hours_ago=25)
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert claim_in_db(authorized_claim.id).status == "auto_captured"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].source_claim_id == authorized_claim.id
    assert _giveaway_credits(db_session, picker_user.id) == []


# ---------------------------------------------------------------------------
# D542 (7): the giver's push wording depends on whether this completion earned a credit
# ---------------------------------------------------------------------------

def test_confirm_pickup_first_completion_sends_credit_earned_push(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    send_push = mocker.patch("app.routers.claims.send_push")
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text

    assert len(_giveaway_credits(db_session, giver_user.id)) == 1
    assert _giver_push_body(send_push) == GIVEAWAY_CREDIT_PUSH_BODY


def test_confirm_collected_first_completion_sends_credit_earned_push(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    send_push = mocker.patch("app.routers.claims.send_push")
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/confirm-collected")
    assert resp.status_code == 200, resp.text

    assert len(_giveaway_credits(db_session, giver_user.id)) == 1
    assert _giver_push_body(send_push) == GIVEAWAY_CREDIT_PUSH_BODY


def test_sweeper_first_completion_sends_credit_earned_push(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    send_push = mocker.patch("app.jobs.post_window_sweeper.send_push")
    _make_claim(
        db_session, active_listing, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1

    assert len(_giveaway_credits(db_session, giver_user.id)) == 1
    assert _giver_push_body(send_push) == GIVEAWAY_CREDIT_PUSH_BODY


def test_confirm_pickup_second_completion_for_same_giver_sends_listing_title(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    send_push = mocker.patch("app.routers.claims.send_push")
    first = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert first.status_code == 200, first.text
    assert _giver_push_body(send_push) == GIVEAWAY_CREDIT_PUSH_BODY

    second_claim = _build_authorized_claim_for(db_session, giver_user, picker_user)
    second = auth_client(picker_user).post(f"/claims/{second_claim.id}/confirm-pickup")
    assert second.status_code == 200, second.text

    assert len(_giveaway_credits(db_session, giver_user.id)) == 1
    assert _giver_push_body(send_push) == second_claim.listing.title


def test_confirm_pickup_switch_off_sends_listing_title(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    send_push = mocker.patch("app.routers.claims.send_push")
    try:
        _set_switch(db_session, False)
        resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
        assert resp.status_code == 200, resp.text
        assert _giveaway_credits(db_session, giver_user.id) == []
        assert _giver_push_body(send_push) == authorized_claim.listing.title
    finally:
        _restore_switch(db_session)


# ---------------------------------------------------------------------------
# Once per person
# ---------------------------------------------------------------------------

def test_second_completion_for_same_giver_completes_but_writes_no_second_row(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db, trust_events_for,
):
    mocker.patch("app.routers.claims.send_push")
    first = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert first.status_code == 200, first.text
    first_credit = _giveaway_credits(db_session, giver_user.id)
    assert len(first_credit) == 1

    second_claim = _build_authorized_claim_for(db_session, giver_user, picker_user)
    second = auth_client(picker_user).post(f"/claims/{second_claim.id}/confirm-pickup")
    assert second.status_code == 200, second.text
    assert claim_in_db(second_claim.id).status == "completed"

    # The completion itself is untouched by the lost index race: counters and events land.
    db_session.expire_all()
    assert db_session.get(models.User, giver_user.id).completed_giveaways == 2
    assert db_session.get(models.User, picker_user.id).completed_pickups == 2
    assert len(trust_events_for(giver_user.id, "giveaway_completed")) == 2

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].id == first_credit[0].id
    assert credits[0].source_claim_id == authorized_claim.id


def test_giver_with_a_spent_giveaway_credit_earns_no_new_row(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    """The once-per-person index counts a spent credit too: earned means earned."""
    now = datetime.now(timezone.utc)
    spent = models.Credit(
        user_id=giver_user.id, kind="giveaway",
        earned_at=now - timedelta(days=30), expires_at=now + timedelta(days=60), used_at=now,
    )
    db_session.add(spent)
    db_session.commit()
    db_session.refresh(spent)

    mocker.patch("app.routers.claims.send_push")
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "completed"
    db_session.expire_all()
    assert db_session.get(models.User, giver_user.id).completed_giveaways == 1

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].id == spent.id
    assert credits[0].used_at is not None


# ---------------------------------------------------------------------------
# The program switch gates earning
# ---------------------------------------------------------------------------

def test_switch_off_earns_nothing(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    mocker.patch("app.routers.claims.send_push")
    try:
        _set_switch(db_session, False)
        resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
        assert resp.status_code == 200, resp.text
        assert claim_in_db(authorized_claim.id).status == "completed"
        db_session.expire_all()
        assert db_session.get(models.User, giver_user.id).completed_giveaways == 1
        assert _giveaway_credits(db_session, giver_user.id) == []
    finally:
        _restore_switch(db_session)


def test_switch_row_missing_reads_as_off_and_earns_nothing(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    mocker.patch("app.routers.claims.send_push")
    try:
        db_session.execute(text("DELETE FROM program_switches WHERE name='giveaway_credit'"))
        db_session.commit()
        db_session.expire_all()
        resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
        assert resp.status_code == 200, resp.text
        assert claim_in_db(authorized_claim.id).status == "completed"
        assert _giveaway_credits(db_session, giver_user.id) == []
    finally:
        _restore_switch(db_session)
    db_session.expire_all()
    restored = db_session.get(models.ProgramSwitch, "giveaway_credit")
    assert restored is not None and restored.enabled is True


# ---------------------------------------------------------------------------
# A deleted giver
# ---------------------------------------------------------------------------

def test_deleted_giver_earns_nothing_on_a_sweeper_completion(
    mocker, db_session, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    mocker.patch("app.jobs.post_window_sweeper.send_push")
    db_session.execute(
        text("UPDATE users SET deleted_at=timezone('utc', now()) WHERE id=:g"),
        {"g": giver_user.id},
    )
    db_session.commit()
    db_session.expire_all()
    claim = _make_claim(
        db_session, active_listing, picker_user,
        status="authorized", pickup_offset_hours=-3, geofence_offset_hours=-2.5,
    )
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert result.errored == 0
    db_session.expire_all()
    assert db_session.get(models.Claim, claim.id).status == "auto_captured"
    assert db_session.get(models.User, giver_user.id).completed_giveaways == 1
    assert _giveaway_credits(db_session, giver_user.id) == []


# ---------------------------------------------------------------------------
# Endings that do not complete a handoff earn nothing
# ---------------------------------------------------------------------------

def test_no_show_earns_nothing(
    auth_client, db_session, giver_user, picker_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "no_show"
    assert _giveaway_credits(db_session, giver_user.id) == []
    assert _giveaway_credits(db_session, picker_user.id) == []


def test_late_cancel_earns_nothing(
    auth_client, db_session, giver_user, picker_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, mock_stripe_pi_cancel, claim_in_db,
):
    pickup_at = datetime.utcnow() + timedelta(hours=1, minutes=30)
    _set_pickup_scheduled_at(
        db_session, authorized_claim.id, status="pickup_scheduled", pickup_at=pickup_at,
    )
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/cancel")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "no_show"
    mock_stripe_pi_capture.assert_called_once()
    assert _giveaway_credits(db_session, giver_user.id) == []
    assert _giveaway_credits(db_session, picker_user.id) == []


def test_cancelled_claim_earns_nothing(
    auth_client, db_session, giver_user, picker_user, authorized_claim,
    mock_stripe_pi_cancel, claim_in_db,
):
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/cancel")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "cancelled"
    assert _giveaway_credits(db_session, giver_user.id) == []
    assert _giveaway_credits(db_session, picker_user.id) == []


# ---------------------------------------------------------------------------
# The earned credit is spendable once its iPhone is checked (D542 (4))
# ---------------------------------------------------------------------------

def test_earned_credit_is_what_find_available_credit_returns_for_the_giver(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    mocker.patch("app.routers.claims.send_push")
    now = datetime.now(timezone.utc)
    assert find_available_credit(db_session, giver_user.id, now) is None

    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    # Earned but unchecked: not yet spendable (D542 (4)).
    assert credits[0].device_checked_at is None
    assert find_available_credit(db_session, giver_user.id, datetime.now(timezone.utc)) is None
    credits[0].device_checked_at = datetime.now(timezone.utc)
    db_session.add(credits[0])
    db_session.commit()
    available = find_available_credit(db_session, giver_user.id, datetime.now(timezone.utc))
    assert available is not None
    assert available.id == credits[0].id
    assert isinstance(available.id, uuid.UUID)
    # Not the picker's to spend.
    assert find_available_credit(db_session, picker_user.id, now) is None


# ---------------------------------------------------------------------------
# D542 (5), slice 2: the re-signup rule. Deleting an account records whether it held a
# giveaway credit; a new account with the same email then earns none.
# ---------------------------------------------------------------------------

def _fingerprint_row(db_session, email) -> DeletedEmailFingerprint:
    db_session.expire_all()
    return (
        db_session.query(DeletedEmailFingerprint)
        .filter(DeletedEmailFingerprint.email_hash == email_fingerprint(email))
        .one()
    )


@pytest.mark.parametrize("used", [False, True], ids=["unused", "used"])
def test_delete_me_records_had_giveaway_credit_for_a_holder(
    auth_client, db_session, giver_user, used,
):
    now = datetime.now(timezone.utc)
    db_session.add(models.Credit(
        user_id=giver_user.id, kind="giveaway", earned_at=now, expires_at=now + NINETY_DAYS,
        used_at=now if used else None,
    ))
    db_session.commit()
    email = giver_user.email

    resp, _ = _delete_me(auth_client, giver_user)
    assert resp.status_code == 204, resp.text

    row = _fingerprint_row(db_session, email)
    assert row.had_giveaway_credit is True
    assert row.was_referred is False  # D544 (5): holding a credit is not being referred


def test_delete_me_records_no_giveaway_credit_for_a_referral_only_holder(
    auth_client, db_session, giver_user, picker_user,
):
    """A referral credit is not a giveaway credit; a user with none at all reads the same."""
    now = datetime.now(timezone.utc)
    db_session.add(models.Credit(
        user_id=giver_user.id, kind="referral", referred_user_id=picker_user.id,
        earned_at=now, expires_at=now + NINETY_DAYS,
    ))
    db_session.commit()
    giver_email = giver_user.email
    picker_email = picker_user.email

    resp, _ = _delete_me(auth_client, giver_user)
    assert resp.status_code == 204, resp.text
    giver_row = _fingerprint_row(db_session, giver_email)
    assert giver_row.had_giveaway_credit is False
    assert giver_row.was_referred is False

    resp, _ = _delete_me(auth_client, picker_user)
    assert resp.status_code == 204, resp.text
    assert _fingerprint_row(db_session, picker_email).had_giveaway_credit is False


def _credit_logger():
    return __import__("app.services.credit_service", fromlist=["logger"]).logger


def test_giver_whose_email_earned_before_deletion_earns_nothing(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    db_session.add(DeletedEmailFingerprint(
        email_hash=email_fingerprint(giver_user.email), had_giveaway_credit=True,
    ))
    db_session.commit()
    mocker.patch("app.routers.claims.send_push")
    info_spy = mocker.spy(_credit_logger(), "info")

    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "completed"
    db_session.expire_all()
    assert db_session.get(models.User, giver_user.id).completed_giveaways == 1

    assert _giveaway_credits(db_session, giver_user.id) == []
    payloads = [c.args[0] for c in info_spy.call_args_list if c.args]
    assert any(
        "giveaway_credit_skipped" in p and "earned_before_deletion" in p for p in payloads
    )


def test_giver_matching_a_deleted_email_without_a_credit_still_earns(
    auth_client, db_session, picker_user, giver_user, authorized_claim, mocker,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture, claim_in_db,
):
    db_session.add(DeletedEmailFingerprint(
        email_hash=email_fingerprint(giver_user.email), had_giveaway_credit=False,
    ))
    db_session.commit()
    mocker.patch("app.routers.claims.send_push")

    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert claim_in_db(authorized_claim.id).status == "completed"

    credits = _giveaway_credits(db_session, giver_user.id)
    assert len(credits) == 1
    assert credits[0].source_claim_id == authorized_claim.id

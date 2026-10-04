"""GET /claims/{claim_id}/score-delta — what one ending did to one user's scores.

Every ending is driven through the real path that writes it (confirm-pickup, the
post-window sweeper, no-show, cancel) rather than assembled in the database, because
the thing most likely to break is the seam these tests exist to hold: a trust event's
created_at defaults to CURRENT_TIMESTAMP — transaction start — while the claim's ending
anchor is stamped later in the same request from Python. Hand-built rows would put both
timestamps at the same instant and prove nothing about the gap.

The two cases at the bottom are the reason no constant can express this: a first
infraction is free, so a first no-show moves the score by 0 and not -40; and a
completion that heals an older infraction is worth more than the flat 10, because the
deduction it retires comes back.
"""
import uuid

from sqlalchemy import text

from app import models
from app.jobs.post_window_sweeper import run_post_window_sweeper


# Trust events written for the tests' PRE-EXISTING history go in through the database
# clock, never through Python's. trust_events.created_at is a naive column filled by
# CURRENT_TIMESTAMP, which Postgres renders in the session's timezone — a naive
# datetime.utcnow() from the test would land in a different frame on any machine whose
# Postgres session is not UTC, and would sort against the real rows wrongly.
def _seed_event(db_session, user_id, event_type, *, days_ago: int, listing_id=None):
    db_session.execute(
        text(
            "INSERT INTO trust_events (user_id, event_type, related_listing_id, created_at) "
            "VALUES (:uid, :et, :lid, CURRENT_TIMESTAMP - make_interval(days => :d))"
        ),
        {"uid": user_id, "et": event_type, "lid": listing_id, "d": days_ago},
    )
    db_session.commit()


def _delta(auth_client, user, claim_id):
    resp = auth_client(user).get(f"/claims/{claim_id}/score-delta")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_sweepable_claim(db_session, listing, picker):
    """An authorized claim whose pickup and geofence are behind it — what the
    post-window sweeper auto-captures. Mirrors test_post_window_sweeper's factory."""
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="pending_payment",
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex[:16]}",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.execute(
        text(
            "UPDATE claims SET status='authorized', "
            "pickup_scheduled_at = CURRENT_TIMESTAMP - interval '3 hours', "
            "geofence_confirmed_at = CURRENT_TIMESTAMP - interval '2 hours', "
            "authorized_at = CURRENT_TIMESTAMP - interval '3 hours' WHERE id=:cid"
        ),
        {"cid": claim.id},
    )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(models.Claim, claim.id)


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------

def test_404_when_claim_missing(auth_client, picker_user):
    resp = auth_client(picker_user).get(f"/claims/{uuid.uuid4()}/score-delta")
    assert resp.status_code == 404


def test_403_when_caller_is_not_a_party(auth_client, other_picker_user, authorized_claim):
    resp = auth_client(other_picker_user).get(
        f"/claims/{authorized_claim.id}/score-delta"
    )
    assert resp.status_code == 403


def test_claim_with_no_ending_reads_zeros_rather_than_erroring(
    auth_client, picker_user, authorized_claim,
):
    """A live claim has no anchor, so it has no identifiable ending. Zeros, not a 409."""
    assert _delta(auth_client, picker_user, authorized_claim.id) == {
        "trust_delta": 0,
        "eco_delta": 0,
    }


# ---------------------------------------------------------------------------
# completed — POST /claims/{id}/confirm-pickup
# ---------------------------------------------------------------------------

def test_completed_picker(
    auth_client, picker_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, picker_user, authorized_claim.id) == {
        "trust_delta": 10,
        "eco_delta": 10,
    }


def test_completed_giver(
    auth_client, picker_user, giver_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """The giver nets 5 eco: the completion earns him 10 and moves his listing out of
    the active-or-claimed set, costing the 5 it was contributing."""
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, giver_user, authorized_claim.id) == {
        "trust_delta": 10,
        "eco_delta": 5,
    }


# ---------------------------------------------------------------------------
# auto_captured — the post-window sweeper
# ---------------------------------------------------------------------------

def test_auto_captured_picker(
    db_session, auth_client, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    claim = _make_sweepable_claim(db_session, active_listing, picker_user)
    result = run_post_window_sweeper(db_session)
    assert result.captured == 1
    assert _delta(auth_client, picker_user, claim.id) == {
        "trust_delta": 10,
        "eco_delta": 10,
    }


def test_auto_captured_giver(
    db_session, auth_client, picker_user, giver_user, active_listing,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """Auto-capture awards identically to a confirmed pickup on both sides."""
    claim = _make_sweepable_claim(db_session, active_listing, picker_user)
    assert run_post_window_sweeper(db_session).captured == 1
    assert _delta(auth_client, giver_user, claim.id) == {
        "trust_delta": 10,
        "eco_delta": 5,
    }


# ---------------------------------------------------------------------------
# no_show — POST /claims/{id}/no-show
# ---------------------------------------------------------------------------

def test_no_show_picker_with_the_free_slot_already_spent(
    db_session, auth_client, picker_user, giver_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """-40 is only reachable once an OLDER infraction holds the free slot. That older
    event sits 60 days back, far outside this ending's window, so it is not counted as
    part of this ending — it only changes what this ending costs."""
    _seed_event(db_session, picker_user.id, "late_cancel", days_ago=60)

    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, picker_user, authorized_claim.id) == {
        "trust_delta": -40,
        "eco_delta": 0,
    }


def test_no_show_giver(
    db_session, auth_client, picker_user, giver_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """A no-show writes nothing against the giver, and the listing goes back to
    'active' — inside the same eco set it already occupied as 'claimed'."""
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, giver_user, authorized_claim.id) == {
        "trust_delta": 0,
        "eco_delta": 0,
    }


# ---------------------------------------------------------------------------
# cancelled — POST /claims/{id}/cancel
# ---------------------------------------------------------------------------

def test_cancelled_giver(
    auth_client, giver_user, authorized_claim, mock_stripe_pi_cancel, trust_events_for,
):
    """A giver's cancel DOES write a trust event — and it is inert.
    `giver_cancelled_listing` is in neither the deduction table nor the clean set, so it
    scores nothing and never consumes the free slot. The 0 here is measured through a
    real event row, not an absence of one."""
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/cancel")
    assert resp.status_code == 200, resp.text
    assert len(trust_events_for(giver_user.id, "giver_cancelled_listing")) == 1
    assert _delta(auth_client, giver_user, authorized_claim.id) == {
        "trust_delta": 0,
        "eco_delta": 0,
    }


def test_cancelled_picker(
    auth_client, picker_user, giver_user, authorized_claim, mock_stripe_pi_cancel,
):
    """The picker is charged nothing by the giver's cancellation."""
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/cancel")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, picker_user, authorized_claim.id) == {
        "trust_delta": 0,
        "eco_delta": 0,
    }


# ---------------------------------------------------------------------------
# The two cases no constant can express
# ---------------------------------------------------------------------------

def test_first_no_show_costs_nothing_because_the_first_infraction_is_free(
    auth_client, picker_user, giver_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """A weights table would print -40 here. The picker's score does not move at all:
    with no prior infraction, this one takes the free slot."""
    resp = auth_client(giver_user).post(f"/claims/{authorized_claim.id}/no-show")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, picker_user, authorized_claim.id)["trust_delta"] == 0


def test_healing_completion_is_worth_more_than_ten(
    db_session, auth_client, picker_user, authorized_claim,
    mock_stripe_pi_retrieve, mock_stripe_pi_capture,
):
    """This completion is the fifth clean event after an old no-show, so that no-show
    heals. Healing frees the slot the no-show was occupying, which promotes the later
    late_cancel into it and retires its -20 as well. The picker's score moves +30 for a
    completion nominally worth +10.

    Before: 4 completions (+40), no_show free, late_cancel deducts 20  ->  20
    After:  5 completions (+50), no_show healed, late_cancel now free  ->  50
    """
    _seed_event(db_session, picker_user.id, "no_show", days_ago=30)
    for day in (25, 24, 23, 22):
        _seed_event(db_session, picker_user.id, "pickup_completed", days_ago=day)
    _seed_event(db_session, picker_user.id, "late_cancel", days_ago=20)

    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text

    body = _delta(auth_client, picker_user, authorized_claim.id)
    assert body["trust_delta"] > 10
    assert body["trust_delta"] == 30


# ---------------------------------------------------------------------------
# D539 step 3, slice 2 — a completion covered by a Zelbi credit releases the hold. The
# ending is still 'completed' anchored on completed_at, written in the same request as
# the trust events, so it reads exactly like a charged completion on both sides.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone  # noqa: E402


def _cover_with_credit(db_session, claim, user, mocker, stripe_pi_factory):
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id, kind="giveaway", earned_at=now, expires_at=now + timedelta(days=90),
    )
    db_session.add(credit)
    db_session.commit()
    db_session.execute(
        text("UPDATE claims SET credit_id=:c WHERE id=:cid"), {"c": credit.id, "cid": claim.id},
    )
    db_session.commit()
    db_session.expire_all()
    pid = claim.stripe_payment_intent_id
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id=pid, amount_capturable=200, status="requires_capture"),
    )
    mocker.patch("app.services.stripe_service.stripe.PaymentIntent.modify")
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.cancel",
        return_value=stripe_pi_factory(pi_id=pid, status="canceled", amount_capturable=0),
    )
    return mocker.patch("app.services.stripe_service.stripe.PaymentIntent.capture")


def test_covered_completion_reads_the_same_as_a_charged_one_for_the_picker(
    db_session, auth_client, picker_user, authorized_claim, mocker, stripe_pi_factory,
):
    capture = _cover_with_credit(db_session, authorized_claim, picker_user, mocker, stripe_pi_factory)
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    capture.assert_not_called()
    db_session.expire_all()
    assert db_session.get(models.Claim, authorized_claim.id).captured_at is None
    assert _delta(auth_client, picker_user, authorized_claim.id) == {
        "trust_delta": 10,
        "eco_delta": 10,
    }


def test_covered_completion_reads_the_same_as_a_charged_one_for_the_giver(
    db_session, auth_client, picker_user, giver_user, authorized_claim, mocker, stripe_pi_factory,
):
    _cover_with_credit(db_session, authorized_claim, picker_user, mocker, stripe_pi_factory)
    resp = auth_client(picker_user).post(f"/claims/{authorized_claim.id}/confirm-pickup")
    assert resp.status_code == 200, resp.text
    assert _delta(auth_client, giver_user, authorized_claim.id) == {
        "trust_delta": 10,
        "eco_delta": 5,
    }

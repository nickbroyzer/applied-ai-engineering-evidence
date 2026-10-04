"""D549 (survey A2): the $2 hold moves from checkout open to the pay tap.

A deferred create makes the claim and reserves a credit but creates no PaymentIntent.
POST /claims/{id}/payment-intent, called by the PaymentSheet's confirmHandler with the
chosen PaymentMethod, stamps consent and the card fingerprint, creates the intent for
that card and returns its client secret. A dead intent from an earlier tap is cancelled
and replaced under a new idempotency key; an identical retried request keeps its key.
The non-deferred path is untouched: the existing create_claim tests cover it.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import models
from app.jobs.pending_payment_sweeper import run_pending_payment_sweeper
from app.routers.claims import KNOWN_DISCLOSURE_VERSIONS

_DISCLOSURE_VERSION = next(
    v for v in KNOWN_DISCLOSURE_VERSIONS if not v.startswith("fee-disclosure-credit-")
)
_CREDIT_DISCLOSURE_VERSION = "fee-disclosure-credit-2026-09-27"
_FINGERPRINT = "fp_test_4242"


def _create_body(listing_id) -> dict:
    return {
        "listing_id": str(listing_id),
        "disclosure_version": _DISCLOSURE_VERSION,
        "deferred": True,
    }


def _pm_body(pm_id: str, version: str = _DISCLOSURE_VERSION) -> dict:
    return {"payment_method_id": pm_id, "disclosure_version": version}


def _give_credit(db_session, user) -> models.Credit:
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id,
        kind="giveaway",
        earned_at=now,
        expires_at=now + timedelta(days=90),
        device_checked_at=now,
    )
    db_session.add(credit)
    db_session.commit()
    db_session.refresh(credit)
    return credit


def _payment_method(mocker, *, pm_id: str | None = None, customer=None, fingerprint=_FINGERPRINT):
    pm = mocker.MagicMock()
    pm.id = pm_id or f"pm_test_{uuid.uuid4().hex[:16]}"
    pm.customer = customer
    pm.card = mocker.MagicMock()
    pm.card.fingerprint = fingerprint
    return pm


def _mock_pm_retrieve(mocker, pm):
    return mocker.patch(
        "app.services.stripe_service.stripe.PaymentMethod.retrieve",
        return_value=pm,
    )


def _deferred_claim(auth_client, picker_user, active_listing, claim_in_db) -> models.Claim:
    resp = auth_client(picker_user).post("/claims", json=_create_body(active_listing.id))
    assert resp.status_code == 201, resp.text
    return claim_in_db(uuid.UUID(resp.json()["claim"]["id"]))


# ---------------------------------------------------------------------------
# Deferred create
# ---------------------------------------------------------------------------

def test_deferred_create_makes_no_intent_and_keeps_the_credit_reservation(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, claim_in_db, db_session,
):
    credit = _give_credit(db_session, picker_user)
    resp = auth_client(picker_user).post("/claims", json=_create_body(active_listing.id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["client_secret"] is None
    assert body["claim"]["covered_by_credit"] is True
    assert body["claim"]["status"] == "pending_payment"
    mock_stripe_pi_create.assert_not_called()

    claim = claim_in_db(uuid.UUID(body["claim"]["id"]))
    assert claim.stripe_payment_intent_id is None
    assert claim.credit_id == credit.id
    assert claim.disclosure_version == _DISCLOSURE_VERSION
    assert claim.disclosure_accepted_at is None


def test_deferred_reopen_returns_the_same_pending_claim(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, mock_stripe_pi_cancel,
    claim_in_db, db_session,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)

    again = auth_client(picker_user).post("/claims", json=_create_body(active_listing.id))
    assert again.status_code == 200, again.text
    assert again.json()["claim"]["id"] == str(claim.id)
    assert again.json()["client_secret"] is None
    mock_stripe_pi_cancel.assert_not_called()
    assert db_session.query(models.Claim).count() == 1

    # An intent left by an earlier tap is cancelled and cleared on reopen.
    claim.stripe_payment_intent_id = "pi_test_left_by_earlier_tap"
    db_session.add(claim)
    db_session.commit()
    third = auth_client(picker_user).post("/claims", json=_create_body(active_listing.id))
    assert third.status_code == 200, third.text
    mock_stripe_pi_cancel.assert_called_once_with("pi_test_left_by_earlier_tap")
    assert claim_in_db(claim.id).stripe_payment_intent_id is None


# ---------------------------------------------------------------------------
# POST /claims/{id}/payment-intent
# ---------------------------------------------------------------------------

def test_payment_intent_creates_for_the_method_and_stamps_consent_and_fingerprint(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, stripe_pi_factory,
    mocker, claim_in_db, db_session,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)
    created = stripe_pi_factory(status="requires_confirmation")
    mock_stripe_pi_create.side_effect = None
    mock_stripe_pi_create.return_value = created

    resp = auth_client(picker_user).post(
        f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id, _CREDIT_DISCLOSURE_VERSION)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"client_secret": created.client_secret}

    mock_stripe_pi_create.assert_called_once()
    kwargs = mock_stripe_pi_create.call_args.kwargs
    assert kwargs["payment_method"] == pm.id
    assert kwargs["capture_method"] == "manual"
    assert kwargs["setup_future_usage"] == "off_session"
    assert kwargs["automatic_payment_methods"] == {"enabled": True, "allow_redirects": "never"}
    assert kwargs["idempotency_key"] == f"pi_claim_{claim.id}_{pm.id}_first"

    db_session.expire_all()
    fresh = claim_in_db(claim.id)
    assert fresh.stripe_payment_intent_id == created.id
    assert fresh.card_fingerprint == _FINGERPRINT
    assert fresh.disclosure_version == _CREDIT_DISCLOSURE_VERSION
    assert fresh.disclosure_accepted_at is not None
    assert fresh.status == "pending_payment"


def test_payment_intent_refuses_a_foreign_payment_method(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, mocker, claim_in_db,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    pm = _payment_method(mocker, customer="cus_someone_else")
    _mock_pm_retrieve(mocker, pm)

    resp = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id))
    assert resp.status_code == 403, resp.text
    mock_stripe_pi_create.assert_not_called()
    fresh = claim_in_db(claim.id)
    assert fresh.stripe_payment_intent_id is None
    assert fresh.card_fingerprint is None
    assert fresh.disclosure_accepted_at is None


def test_payment_intent_refuses_unknown_version_and_other_pickers(
    auth_client, picker_user, other_picker_user, active_listing, mock_stripe_pi_create,
    mocker, claim_in_db,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)

    bad_version = auth_client(picker_user).post(
        f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id, "fee-disclosure-nope")
    )
    assert bad_version.status_code == 400, bad_version.text

    stranger = auth_client(other_picker_user).post(
        f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id)
    )
    assert stranger.status_code == 403, stranger.text
    mock_stripe_pi_create.assert_not_called()


def test_second_tap_after_a_decline_cancels_the_dead_intent_and_creates_a_new_one(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, mock_stripe_pi_cancel,
    stripe_pi_factory, mocker, claim_in_db, db_session,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    first_pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, first_pm)
    first_pi = stripe_pi_factory(status="requires_confirmation")
    mock_stripe_pi_create.side_effect = None
    mock_stripe_pi_create.return_value = first_pi
    first = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(first_pm.id))
    assert first.status_code == 200, first.text

    # The SDK confirmed and the card was declined: Stripe now reports the intent as
    # requires_payment_method. The picker picks another card and taps again.
    declined = stripe_pi_factory(pi_id=first_pi.id, status="requires_payment_method")
    mock_retrieve = mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve", return_value=declined
    )
    second_pm = _payment_method(mocker, fingerprint="fp_test_other")
    _mock_pm_retrieve(mocker, second_pm)
    second_pi = stripe_pi_factory(status="requires_confirmation")
    mock_stripe_pi_create.return_value = second_pi

    second = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(second_pm.id))
    assert second.status_code == 200, second.text
    assert second.json() == {"client_secret": second_pi.client_secret}

    mock_retrieve.assert_called_once_with(first_pi.id)
    mock_stripe_pi_cancel.assert_called_once_with(first_pi.id)
    assert mock_stripe_pi_create.call_count == 2
    kwargs = mock_stripe_pi_create.call_args.kwargs
    assert kwargs["payment_method"] == second_pm.id
    assert kwargs["idempotency_key"] == f"pi_claim_{claim.id}_{second_pm.id}_{first_pi.id}"

    db_session.expire_all()
    fresh = claim_in_db(claim.id)
    assert fresh.stripe_payment_intent_id == second_pi.id
    assert fresh.card_fingerprint == "fp_test_other"


def test_live_hold_on_the_claim_still_refuses_a_second_intent(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, mock_stripe_pi_cancel,
    stripe_pi_factory, mocker, claim_in_db, db_session,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    claim.stripe_payment_intent_id = "pi_test_live_hold"
    db_session.add(claim)
    db_session.commit()
    mocker.patch(
        "app.services.stripe_service.stripe.PaymentIntent.retrieve",
        return_value=stripe_pi_factory(pi_id="pi_test_live_hold", status="requires_capture"),
    )
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)

    resp = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id))
    assert resp.status_code == 502, resp.text
    mock_stripe_pi_cancel.assert_not_called()
    mock_stripe_pi_create.assert_not_called()
    assert claim_in_db(claim.id).stripe_payment_intent_id == "pi_test_live_hold"


def test_identical_retried_request_keeps_its_key_and_returns_the_same_intent(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, stripe_pi_factory,
    mocker, claim_in_db, db_session,
):
    """Stripe replays the original response for a repeated idempotency key. The first
    attempt here reached Stripe but its write was lost (the claim still carries no
    intent id), so the retry must present the same key and land the same intent."""
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)

    by_key: dict[str, object] = {}

    def _stripe_like_create(*args, **kwargs):
        key = kwargs["idempotency_key"]
        if key not in by_key:
            by_key[key] = stripe_pi_factory(status="requires_confirmation")
        return by_key[key]

    mock_stripe_pi_create.side_effect = _stripe_like_create

    first = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id))
    assert first.status_code == 200, first.text
    first_pid = claim_in_db(claim.id).stripe_payment_intent_id
    assert first_pid is not None

    # The response never reached the app, and the row lost its write: retry.
    db_session.execute(
        text("UPDATE claims SET stripe_payment_intent_id = NULL WHERE id = :cid"),
        {"cid": claim.id},
    )
    db_session.commit()
    db_session.expire_all()

    second = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id))
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert mock_stripe_pi_create.call_count == 2
    keys = [c.kwargs["idempotency_key"] for c in mock_stripe_pi_create.call_args_list]
    assert keys[0] == keys[1] == f"pi_claim_{claim.id}_{pm.id}_first"
    assert len(by_key) == 1
    db_session.expire_all()
    assert claim_in_db(claim.id).stripe_payment_intent_id == first_pid


# ---------------------------------------------------------------------------
# D548 addendum (c): the giveaway credit's card rule at the pay tap
# ---------------------------------------------------------------------------

def _spent_giveaway_credit_on(db_session, user, fingerprint) -> models.Credit:
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id, kind="giveaway", earned_at=now, expires_at=now + timedelta(days=90),
        used_at=now, used_card_fingerprint=fingerprint,
    )
    db_session.add(credit)
    db_session.commit()
    return credit


def test_pay_tap_conflict_refuses_the_giveaway_credit_and_creates_no_intent(
    auth_client, picker_user, other_picker_user, active_listing, mock_stripe_pi_create,
    stripe_pi_factory, mocker, claim_in_db, db_session,
):
    """Another person's giveaway credit already spent this card: 409 credit_card_refused,
    the credit comes off the claim and stays available and unstamped, no PaymentIntent."""
    _spent_giveaway_credit_on(db_session, other_picker_user, _FINGERPRINT)
    credit = _give_credit(db_session, picker_user)
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    assert claim.credit_id == credit.id
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)

    resp = auth_client(picker_user).post(
        f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id, _CREDIT_DISCLOSURE_VERSION)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == {
        "code": "credit_card_refused",
        "kind": "giveaway",
        "message": "Zelbi credit not applied. It can't be used with this card.",
    }
    mock_stripe_pi_create.assert_not_called()

    db_session.expire_all()
    fresh = claim_in_db(claim.id)
    assert fresh.credit_id is None
    assert fresh.stripe_payment_intent_id is None
    assert fresh.status == "pending_payment"
    fresh_credit = db_session.get(models.Credit, credit.id)
    assert fresh_credit.used_at is None
    assert fresh_credit.used_claim_id is None
    assert fresh_credit.used_card_fingerprint is None

    # The claim is now a plain $2 claim: the next tap creates the intent.
    created = stripe_pi_factory(status="requires_confirmation")
    mock_stripe_pi_create.side_effect = None
    mock_stripe_pi_create.return_value = created
    second = auth_client(picker_user).post(f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id))
    assert second.status_code == 200, second.text
    assert second.json() == {"client_secret": created.client_secret}
    assert claim_in_db(claim.id).credit_id is None


def test_pay_tap_with_an_unused_card_keeps_the_giveaway_credit(
    auth_client, picker_user, other_picker_user, active_listing, mock_stripe_pi_create,
    stripe_pi_factory, mocker, claim_in_db, db_session,
):
    _spent_giveaway_credit_on(db_session, other_picker_user, "fp_test_someone_elses")
    credit = _give_credit(db_session, picker_user)
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    pm = _payment_method(mocker)
    _mock_pm_retrieve(mocker, pm)
    mock_stripe_pi_create.side_effect = None
    mock_stripe_pi_create.return_value = stripe_pi_factory(status="requires_confirmation")

    resp = auth_client(picker_user).post(
        f"/claims/{claim.id}/payment-intent", json=_pm_body(pm.id, _CREDIT_DISCLOSURE_VERSION)
    )
    assert resp.status_code == 200, resp.text
    mock_stripe_pi_create.assert_called_once()
    fresh = claim_in_db(claim.id)
    assert fresh.credit_id == credit.id
    assert fresh.card_fingerprint == _FINGERPRINT


# ---------------------------------------------------------------------------
# Sweeper
# ---------------------------------------------------------------------------

def test_sweeper_cancels_an_abandoned_deferred_claim_with_no_intent(
    auth_client, picker_user, active_listing, mock_stripe_pi_create, mock_stripe_pi_cancel,
    mocker, claim_in_db, db_session,
):
    claim = _deferred_claim(auth_client, picker_user, active_listing, claim_in_db)
    assert claim.stripe_payment_intent_id is None
    mock_retrieve = mocker.patch("app.services.stripe_service.stripe.PaymentIntent.retrieve")
    db_session.execute(
        text("UPDATE claims SET claimed_at = :t WHERE id = :cid"),
        {"cid": claim.id, "t": datetime.utcnow() - timedelta(minutes=6)},
    )
    db_session.commit()
    db_session.expire_all()

    result = run_pending_payment_sweeper(db_session)

    assert result.cancelled == 1
    assert result.errored == 0
    assert result.promoted == 0
    mock_retrieve.assert_not_called()
    mock_stripe_pi_cancel.assert_not_called()
    db_session.expire_all()
    fresh = claim_in_db(claim.id)
    assert fresh.status == "cancelled"
    assert fresh.cancelled_at is not None
    assert db_session.get(models.Listing, active_listing.id).status == "active"

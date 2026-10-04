"""GET /claims/my-fees — the Payment history rows (D535) and their outcome (D539 step 3,
slice 3). The route had no tests before this file; every outcome is covered here."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import models


def _close(db_session, claim, status: str, **stamps) -> models.Claim:
    """Move `claim` (already authorized) into a closed status with the given timestamp
    columns set, the way the terminal routes and cron do."""
    sets = ["status=:status"] + [f"{col}=:{col}" for col in stamps]
    db_session.execute(
        text(f"UPDATE claims SET {', '.join(sets)} WHERE id=:cid"),
        {"status": status, "cid": claim.id, **stamps},
    )
    db_session.commit()
    db_session.expire_all()
    return db_session.get(models.Claim, claim.id)


def _credit_for(db_session, user, *, used_claim_id=None) -> models.Credit:
    now = datetime.now(timezone.utc)
    credit = models.Credit(
        user_id=user.id, kind="giveaway", earned_at=now, expires_at=now + timedelta(days=90),
        used_at=now if used_claim_id is not None else None,
        used_claim_id=used_claim_id,
    )
    db_session.add(credit)
    db_session.commit()
    db_session.refresh(credit)
    return credit


def _reserve(db_session, claim, credit) -> None:
    db_session.execute(
        text("UPDATE claims SET credit_id=:c WHERE id=:cid"),
        {"c": credit.id, "cid": claim.id},
    )
    db_session.commit()
    db_session.expire_all()


def _only_row(auth_client, picker_user, claim) -> dict:
    resp = auth_client(picker_user).get("/claims/my-fees")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["claim_id"] == str(claim.id)
    return rows[0]


def test_my_fees_charged_on_captured_at(auth_client, picker_user, authorized_claim, db_session):
    now = datetime.utcnow()
    claim = _close(db_session, authorized_claim, "completed", completed_at=now, captured_at=now)
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "charged"


def test_my_fees_charged_on_auto_captured_at(auth_client, picker_user, authorized_claim, db_session):
    now = datetime.utcnow()
    claim = _close(db_session, authorized_claim, "auto_captured", auto_captured_at=now)
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "charged"


def test_my_fees_refunded_wins_over_charged(auth_client, picker_user, authorized_claim, db_session):
    now = datetime.utcnow()
    claim = _close(
        db_session, authorized_claim, "completed",
        completed_at=now, captured_at=now, refunded_at=now + timedelta(hours=1),
    )
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "refunded"


def test_my_fees_not_charged_on_cancelled(auth_client, picker_user, authorized_claim, db_session):
    claim = _close(db_session, authorized_claim, "cancelled", cancelled_at=datetime.utcnow())
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "not_charged"


def test_my_fees_not_charged_on_no_show_with_lapsed_hold(
    auth_client, picker_user, authorized_claim, db_session,
):
    """A no-show recorded after the hold lapsed: no_show_at set, nothing captured. Nothing
    was taken, so the row must not read as charged (backlog row from the step 3 survey)."""
    claim = _close(db_session, authorized_claim, "no_show", no_show_at=datetime.utcnow())
    assert claim.captured_at is None and claim.auto_captured_at is None
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "not_charged"


def test_my_fees_no_show_with_capture_still_charged(
    auth_client, picker_user, authorized_claim, db_session,
):
    """The ordinary no-show — capture succeeded — is unchanged by the lapsed-hold fix."""
    now = datetime.utcnow()
    claim = _close(db_session, authorized_claim, "no_show", no_show_at=now, captured_at=now)
    assert _only_row(auth_client, picker_user, claim)["outcome"] == "charged"


def test_my_fees_credit_on_covered_completion(auth_client, picker_user, authorized_claim, db_session):
    """A completed pickup whose reserved credit was spent on it: credit_id set and that
    credit's used_claim_id is this claim. The hold was released, so the outcome is credit."""
    credit = _credit_for(db_session, picker_user, used_claim_id=authorized_claim.id)
    _reserve(db_session, authorized_claim, credit)
    completed_at = datetime.utcnow() - timedelta(minutes=5)
    claim = _close(db_session, authorized_claim, "completed", completed_at=completed_at)
    assert claim.captured_at is None
    row = _only_row(auth_client, picker_user, claim)
    assert row["outcome"] == "credit"
    # fee_date lands on completed_at for a covered completion.
    fee_date = datetime.fromisoformat(row["fee_date"].replace("Z", "+00:00"))
    assert fee_date.astimezone(timezone.utc).replace(tzinfo=None) == completed_at


def test_my_fees_covered_completion_whose_credit_was_spent_elsewhere_is_not_credit(
    auth_client, picker_user, authorized_claim, db_session,
):
    """credit_id set, but the credit's used_claim_id points at a different claim: the
    credit did not cover THIS completion, so the row does not read as credit. The other
    claim (same credit reserved, and spent on it) does."""
    other_claim_id = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO claims (id, listing_id, picker_id, status, claimed_at, authorized_at, "
            "completed_at) VALUES (:id, :lid, :pid, 'completed', :t, :t, :t)"
        ),
        {
            "id": other_claim_id, "lid": authorized_claim.listing_id,
            "pid": picker_user.id, "t": datetime.utcnow() - timedelta(days=10),
        },
    )
    db_session.commit()
    credit = _credit_for(db_session, picker_user, used_claim_id=other_claim_id)
    db_session.execute(
        text("UPDATE claims SET credit_id=:c WHERE id=:cid"),
        {"c": credit.id, "cid": other_claim_id},
    )
    db_session.commit()
    _reserve(db_session, authorized_claim, credit)
    claim = _close(db_session, authorized_claim, "completed", completed_at=datetime.utcnow())

    resp = auth_client(picker_user).get("/claims/my-fees")
    assert resp.status_code == 200, resp.text
    by_id = {r["claim_id"]: r for r in resp.json()}
    assert by_id[str(claim.id)]["outcome"] != "credit"
    assert by_id[str(other_claim_id)]["outcome"] == "credit"


def test_my_fees_credit_on_released_no_show(auth_client, picker_user, authorized_claim, db_session):
    """D548: a missed pickup on a covered claim released the hold and used the credit up:
    credit_id set, the credit spent on this claim, captured_at null. Reads credit, not
    not_charged."""
    credit = _credit_for(db_session, picker_user, used_claim_id=authorized_claim.id)
    _reserve(db_session, authorized_claim, credit)
    claim = _close(db_session, authorized_claim, "no_show", no_show_at=datetime.utcnow())
    assert claim.captured_at is None
    row = _only_row(auth_client, picker_user, claim)
    assert row["outcome"] == "credit"


def test_my_fees_credit_on_released_auto_captured(auth_client, picker_user, authorized_claim, db_session):
    """D548: a silence completion on a covered claim released the hold and used the credit
    up. auto_captured_at is set but captured_at is null; the credit check wins over the
    auto_captured_at charged rule."""
    credit = _credit_for(db_session, picker_user, used_claim_id=authorized_claim.id)
    _reserve(db_session, authorized_claim, credit)
    claim = _close(
        db_session, authorized_claim, "auto_captured", auto_captured_at=datetime.utcnow(),
    )
    assert claim.captured_at is None
    row = _only_row(auth_client, picker_user, claim)
    assert row["outcome"] == "credit"

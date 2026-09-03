"""Phase 9-1 — Migration B (disputes table) schema validation."""
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _seed_claim_and_filer(db_session):
    """Returns (claim_id, picker_user_id) committed in the test DB."""
    from app import models
    from datetime import datetime, timedelta

    user = models.User(
        email=f"u_{uuid.uuid4().hex[:8]}@example.com",
        display_name="U",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    listing = models.Listing(
        giver_id=user.id,
        title="L",
        description="d for migration test seeding",
        category="Other",
        photo_urls=["https://example.com/x.jpg"],
        location_lat=37.7749,
        location_lng=-122.4194,
        location_lat_approx=37.7760,
        location_lng_approx=-122.4182,
        status="active",
        ai_generated=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)

    claim = models.Claim(
        listing_id=listing.id,
        picker_id=user.id,
        status="authorized",
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim.id, user.id


def test_disputes_table_exists_after_migration(db_session):
    """Smoke: the table created by Migration B is queryable."""
    rows = db_session.execute(
        text("SELECT count(*) FROM disputes")
    ).scalar()
    assert rows == 0


def test_ck_disputes_reason_min_len_rejects_79_char_reason(db_session):
    """D64 LOCKED — reason_text < 80 chars must be rejected at the schema layer."""
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    short_reason = "x" * 79
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
                "acknowledged) VALUES (:c, :f, :r, true)"
            ),
            {"c": claim_id, "f": filer_id, "r": short_reason},
        )
        db_session.commit()
    db_session.rollback()


def test_ck_disputes_reason_min_len_accepts_80_char_reason(db_session):
    """Boundary — exactly 80 chars passes."""
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    reason = "y" * 80
    db_session.execute(
        text(
            "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
            "acknowledged) VALUES (:c, :f, :r, true)"
        ),
        {"c": claim_id, "f": filer_id, "r": reason},
    )
    db_session.commit()


def test_ck_disputes_acknowledged_rejects_false(db_session):
    """D64 LOCKED — schema-level CHECK on acknowledged=true."""
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    reason = "z" * 100
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
                "acknowledged) VALUES (:c, :f, :r, false)"
            ),
            {"c": claim_id, "f": filer_id, "r": reason},
        )
        db_session.commit()
    db_session.rollback()


def test_ck_disputes_status_rejects_invalid_value(db_session):
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    reason = "a" * 100
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
                "acknowledged, status) VALUES (:c, :f, :r, true, 'invalid')"
            ),
            {"c": claim_id, "f": filer_id, "r": reason},
        )
        db_session.commit()
    db_session.rollback()


def test_ck_disputes_resolution_rejects_invalid_value(db_session):
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    reason = "b" * 100
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
                "acknowledged, resolution) VALUES (:c, :f, :r, true, 'bogus')"
            ),
            {"c": claim_id, "f": filer_id, "r": reason},
        )
        db_session.commit()
    db_session.rollback()


def test_disputes_claim_id_fk_cascades_on_claim_delete(db_session):
    """FK with ON DELETE CASCADE: deleting the claim removes the dispute."""
    claim_id, filer_id = _seed_claim_and_filer(db_session)
    reason = "c" * 100
    db_session.execute(
        text(
            "INSERT INTO disputes (claim_id, filer_user_id, reason_text, "
            "acknowledged) VALUES (:c, :f, :r, true)"
        ),
        {"c": claim_id, "f": filer_id, "r": reason},
    )
    db_session.commit()

    db_session.execute(text("DELETE FROM claims WHERE id=:c"), {"c": claim_id})
    db_session.commit()

    remaining = db_session.execute(
        text("SELECT count(*) FROM disputes WHERE claim_id=:c"),
        {"c": claim_id},
    ).scalar()
    assert remaining == 0

"""Admin notes — POST/GET /admin/notes and notes in the claim and listing records."""
import uuid

import pytest

from app import models


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


def _post_note(client, kind, subject_id, text="Called the picker; the pickup is rescheduled."):
    return client.post(
        "/admin/notes",
        json={"subject_kind": kind, "subject_id": str(subject_id), "text": text},
    )


def test_note_on_claim_is_saved_and_listed(auth_client, admin_user, pending_payment_claim):
    client = auth_client(admin_user)

    resp = _post_note(client, "claim", pending_payment_claim.id)
    assert resp.status_code == 201, resp.text
    assert resp.json()["author"] == admin_user.display_name

    listed = client.get(f"/admin/notes?subject_kind=claim&subject_id={pending_payment_claim.id}")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["text"] == "Called the picker; the pickup is rescheduled."


def test_claim_record_includes_notes(auth_client, admin_user, pending_payment_claim):
    client = auth_client(admin_user)
    assert _post_note(client, "claim", pending_payment_claim.id).status_code == 201

    resp = client.get(f"/admin/claims/{pending_payment_claim.id}")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["notes"]) == 1


def test_listing_record_includes_notes(auth_client, admin_user, active_listing):
    client = auth_client(admin_user)
    assert _post_note(client, "listing", active_listing.id).status_code == 201

    resp = client.get(f"/admin/listings/{active_listing.id}")
    assert resp.status_code == 200, resp.text
    notes = resp.json()["notes"]
    assert len(notes) == 1
    assert notes[0]["author"] == admin_user.display_name


def test_note_on_user_lists_by_subject(auth_client, admin_user, picker_user, pending_payment_claim):
    client = auth_client(admin_user)
    assert _post_note(client, "user", picker_user.id, text="Asked about the no-show.").status_code == 201

    user_rows = client.get(f"/admin/notes?subject_kind=user&subject_id={picker_user.id}").json()
    claim_rows = client.get(f"/admin/notes?subject_kind=claim&subject_id={pending_payment_claim.id}").json()

    assert [r["text"] for r in user_rows] == ["Asked about the no-show."]
    assert claim_rows == []


def test_note_on_unknown_subject_404s(auth_client, admin_user):
    resp = _post_note(auth_client(admin_user), "listing", uuid.uuid4())
    assert resp.status_code == 404


def test_blank_note_is_rejected(auth_client, admin_user, active_listing):
    resp = _post_note(auth_client(admin_user), "listing", active_listing.id, text="   ")
    assert resp.status_code == 422


def test_unknown_subject_kind_is_rejected(auth_client, admin_user, active_listing):
    resp = _post_note(auth_client(admin_user), "dispute", active_listing.id)
    assert resp.status_code == 422


def test_notes_non_admin_forbidden(auth_client, picker_user, active_listing):
    client = auth_client(picker_user)
    assert _post_note(client, "listing", active_listing.id).status_code == 403
    assert client.get(f"/admin/notes?subject_kind=listing&subject_id={active_listing.id}").status_code == 403

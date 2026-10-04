import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.utils import cloudflare_r2


def _url(key: str) -> str:
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


@pytest.fixture(autouse=True)
def _reset_signed_url_cache():
    cloudflare_r2._photo_url_cache.clear()
    cloudflare_r2._photo_url_cache_window = None
    yield
    cloudflare_r2._photo_url_cache.clear()
    cloudflare_r2._photo_url_cache_window = None


def test_setting_off_returns_url_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", False)
    url = _url("abc/def.jpg")
    assert cloudflare_r2.sign_photo_url(url) == url


def test_setting_on_signs_a_stored_url(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_ttl_seconds", 86400)
    client = MagicMock()
    client.generate_presigned_url.return_value = (
        f"{_url('abc/def.jpg')}?X-Amz-Signature=deadbeef&X-Amz-Expires=86400"
    )
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        signed = cloudflare_r2.sign_photo_url(_url("abc/def.jpg"))
    client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": "abc/def.jpg"},
        ExpiresIn=86400,
    )
    assert "X-Amz-Signature" in signed
    assert "X-Amz-Expires" in signed


def test_unknown_host_returned_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    url = "https://other.example/abc/def.jpg"
    assert cloudflare_r2.sign_photo_url(url) == url


def test_none_returned_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    assert cloudflare_r2.sign_photo_url(None) is None


def test_empty_string_returned_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    assert cloudflare_r2.sign_photo_url("") == ""


def test_signing_failure_returns_url_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    client = MagicMock()
    client.generate_presigned_url.side_effect = Exception("boom")
    url = _url("abc/def.jpg")
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        assert cloudflare_r2.sign_photo_url(url) == url


def test_array_helper_preserves_order(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", False)
    urls = [_url("a.jpg"), None, _url("b.jpg"), ""]
    assert cloudflare_r2.sign_photo_urls(urls) == urls


def _counting_client() -> MagicMock:
    client = MagicMock()
    counter = {"n": 0}

    def _side_effect(_action, Params, ExpiresIn):
        counter["n"] += 1
        return f"https://signed.example/{Params['Key']}?n={counter['n']}"

    client.generate_presigned_url.side_effect = _side_effect
    return client


def test_same_address_reused_within_one_window(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_window_seconds", 100)
    monkeypatch.setattr(time, "time", lambda: 1_000_000)
    client = _counting_client()
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        first = cloudflare_r2.sign_photo_url(_url("abc/def.jpg"))
        second = cloudflare_r2.sign_photo_url(_url("abc/def.jpg"))
    assert first == second
    assert client.generate_presigned_url.call_count == 1


def test_different_addresses_get_different_signed_urls(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_window_seconds", 100)
    monkeypatch.setattr(time, "time", lambda: 1_000_000)
    client = _counting_client()
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        a = cloudflare_r2.sign_photo_url(_url("a.jpg"))
        b = cloudflare_r2.sign_photo_url(_url("b.jpg"))
    assert a != b
    assert client.generate_presigned_url.call_count == 2


def test_window_advance_mints_a_new_signed_url(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_window_seconds", 100)
    current_time = {"t": 1_000_000}
    monkeypatch.setattr(time, "time", lambda: current_time["t"])
    client = _counting_client()
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        first = cloudflare_r2.sign_photo_url(_url("abc/def.jpg"))
        current_time["t"] += 100
        second = cloudflare_r2.sign_photo_url(_url("abc/def.jpg"))
    assert first != second
    assert client.generate_presigned_url.call_count == 2


def test_cache_does_not_leak_across_windows(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_window_seconds", 100)
    current_time = {"t": 1_000_000}
    monkeypatch.setattr(time, "time", lambda: current_time["t"])
    client = _counting_client()
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        cloudflare_r2.sign_photo_url(_url("a.jpg"))
        current_time["t"] += 100
        cloudflare_r2.sign_photo_url(_url("b.jpg"))
    assert list(cloudflare_r2._photo_url_cache.keys()) == ["b.jpg"]


def test_setting_off_caches_nothing(monkeypatch):
    monkeypatch.setattr(settings, "signed_photo_reads", False)
    url = _url("abc/def.jpg")
    assert cloudflare_r2.sign_photo_url(url) == url
    assert cloudflare_r2._photo_url_cache == {}


# --- Endpoint coverage: every emitter that hands a stored photo address to a client.
#
# The unit tests above prove sign_photo_url signs. These prove each response actually
# routes its address through it — the failure they catch is an emitter that was never
# wired up, which looks fine until public bucket access is closed and the photo is a
# blank square. The assertion is deliberately "a signature is present", because that
# is the only property the client needs and the only one the bucket enforces.

SIG = "X-Amz-Signature"


@pytest.fixture
def signing_on(monkeypatch):
    """Signing switched on, with a stub R2 client standing in for the network."""
    monkeypatch.setattr(settings, "signed_photo_reads", True)
    monkeypatch.setattr(settings, "photo_read_ttl_seconds", 43200)
    client = MagicMock()

    def _side_effect(_action, Params, ExpiresIn):
        return f"{_url(Params['Key'])}?{SIG}=deadbeef&X-Amz-Expires={ExpiresIn}"

    client.generate_presigned_url.side_effect = _side_effect
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        yield client


@pytest.fixture
def admin_user(db_session, other_picker_user):
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


@pytest.fixture
def stored_listing(db_session, active_listing):
    """active_listing's fixture photo sits on an unrelated host, which sign_photo_url
    leaves alone by design. Move it onto the bucket so signing has something to do."""
    active_listing.photo_urls = [_url("listing/1.jpg"), _url("listing/2.jpg")]
    db_session.commit()
    db_session.refresh(active_listing)
    return active_listing


def _completed_claim(db_session, listing, picker):
    from app import models
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="completed",
        completion_photo_url=_url("pickup/done.jpg"),
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


def test_notifications_listing_photo_is_signed(
    signing_on, auth_client, picker_user, stored_listing, db_session,
):
    from app import models
    db_session.add(
        models.Notification(
            recipient_id=picker_user.id,
            notification_type="listing_claimed",
            listing_id=stored_listing.id,
            title="Claimed",
            body="Your item was claimed.",
        )
    )
    db_session.commit()

    resp = auth_client(picker_user).get("/notifications")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["listing_id"] == str(stored_listing.id))
    assert SIG in row["listing_photo_url"]


def test_blocks_avatar_is_signed(
    signing_on, auth_client, picker_user, giver_user, db_session,
):
    from app import models
    giver_user.avatar_url = _url("avatars/giver.jpg")
    db_session.add(
        models.BlockedUser(blocker_id=picker_user.id, blocked_id=giver_user.id)
    )
    db_session.commit()

    resp = auth_client(picker_user).get("/users/me/blocks")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["user_id"] == str(giver_user.id))
    assert SIG in row["avatar_url"]


def test_admin_claim_message_image_is_signed(
    signing_on, auth_client, admin_user, picker_user, giver_user, stored_listing, db_session,
):
    from app import models
    claim = _completed_claim(db_session, stored_listing, picker_user)
    db_session.add(
        models.Message(
            listing_id=stored_listing.id,
            sender_id=picker_user.id,
            recipient_id=giver_user.id,
            content="Here it is",
            image_url=_url("messages/1.jpg"),
        )
    )
    db_session.commit()

    resp = auth_client(admin_user).get(f"/admin/claims/{claim.id}")
    assert resp.status_code == 200, resp.text
    message = resp.json()["messages"][0]
    assert SIG in message["image_url"]


def test_admin_claim_listing_photos_are_signed(
    signing_on, auth_client, admin_user, picker_user, stored_listing, db_session,
):
    claim = _completed_claim(db_session, stored_listing, picker_user)

    resp = auth_client(admin_user).get(f"/admin/claims/{claim.id}")
    assert resp.status_code == 200, resp.text
    photos = resp.json()["photos"]
    assert len(photos) == 2
    assert all(SIG in photo for photo in photos)


def test_admin_claim_pickup_photo_is_signed(
    signing_on, auth_client, admin_user, picker_user, stored_listing, db_session,
):
    claim = _completed_claim(db_session, stored_listing, picker_user)

    resp = auth_client(admin_user).get(f"/admin/claims/{claim.id}")
    assert resp.status_code == 200, resp.text
    assert SIG in resp.json()["pickup_photo"]


def test_admin_listings_row_photo_is_signed(
    signing_on, auth_client, admin_user, stored_listing,
):
    resp = auth_client(admin_user).get("/admin/listings")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == str(stored_listing.id))
    assert SIG in row["photo"]


def test_admin_listing_detail_photos_are_signed(
    signing_on, auth_client, admin_user, stored_listing,
):
    resp = auth_client(admin_user).get(f"/admin/listings/{stored_listing.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["photos"]) == 2
    assert all(SIG in photo for photo in body["photos"])


# --- The upload responses: public_url is what the client STORES and must stay raw;
# read_url is the signed twin it DISPLAYS while the upload is still in hand.

def test_upload_presign_returns_both_a_storable_and_a_renderable_url(
    signing_on, auth_client, picker_user,
):
    resp = auth_client(picker_user).post("/uploads/presign", json={"file_extension": "jpg"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert SIG not in body["public_url"]
    assert SIG in body["read_url"]
    assert body["read_url"].startswith(body["public_url"])


def test_completion_photo_presign_returns_both_urls(
    signing_on, auth_client, picker_user, stored_listing, db_session,
):
    from app import models
    claim = models.Claim(
        listing_id=stored_listing.id,
        picker_id=picker_user.id,
        status="authorized",
        authorized_at=datetime.utcnow(),
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    resp = auth_client(picker_user).post(f"/claims/{claim.id}/presign-completion-photo")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert SIG not in body["public_url"]
    assert SIG in body["read_url"]

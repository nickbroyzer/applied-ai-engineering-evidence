from unittest.mock import MagicMock, patch

from app.config import settings
from app.utils import cloudflare_r2


def _url(key: str) -> str:
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


def test_key_recovered_from_public_url():
    assert cloudflare_r2.object_key_from_public_url(_url("abc/def.jpg")) == "abc/def.jpg"


def test_foreign_host_url_is_not_guessed_at():
    assert cloudflare_r2.object_key_from_public_url("https://other.example/abc/def.jpg") is None


def test_delete_calls_r2_with_bucket_and_key():
    client = MagicMock()
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        assert cloudflare_r2.delete_object("abc/def.jpg") is True
    client.delete_object.assert_called_once_with(
        Bucket=settings.r2_bucket_name, Key="abc/def.jpg"
    )


def test_failed_delete_reports_false_and_does_not_raise():
    client = MagicMock()
    client.delete_object.side_effect = Exception("boom")
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        assert cloudflare_r2.delete_object("abc/def.jpg") is False


def test_batch_separates_deleted_unresolved_and_failed():
    client = MagicMock()
    client.delete_object.side_effect = [None, Exception("boom")]
    with patch.object(cloudflare_r2, "_r2_client", return_value=client):
        result = cloudflare_r2.delete_objects_by_public_url(
            [_url("a/1.jpg"), _url("a/2.jpg"), "https://other.example/a/3.jpg"]
        )
    assert result["deleted"] == ["a/1.jpg"]
    assert result["failed"] == ["a/2.jpg"]
    assert result["unresolved"] == ["https://other.example/a/3.jpg"]

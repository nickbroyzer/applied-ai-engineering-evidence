import logging
import time

import boto3
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)

# Per-window signed-URL cache: same object key gets the same minted address for
# a whole window, keyed by window index so a phone's image cache actually hits
# instead of re-downloading on every fetch. Cleared wholesale on window advance
# so it never grows across windows.
_photo_url_cache: dict[str, str] = {}
_photo_url_cache_window: int | None = None


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def object_key_from_public_url(public_url: str) -> str | None:
    """Recover the stored object key from a public URL this module composed.

    Returns None when the URL does not carry the configured public prefix, so a
    row written under an older host is skipped rather than guessed at.
    """
    prefix = settings.r2_public_url.rstrip("/") + "/"
    if not public_url or not public_url.startswith(prefix):
        return None
    key = public_url[len(prefix):]
    return key or None


def delete_object(object_key: str) -> bool:
    """Delete one object. True when the delete call succeeded, False on failure.

    R2 answers a delete for a key that does not exist without raising, so this
    is safe to call twice.
    """
    if not object_key:
        return False
    try:
        _r2_client().delete_object(Bucket=settings.r2_bucket_name, Key=object_key)
        return True
    except Exception:
        logger.exception("r2_delete_failed key=%s", object_key)
        return False


def delete_objects_by_public_url(public_urls: list[str]) -> dict:
    """Delete every object addressed by these public URLs.

    Returns counts plus the URLs that could not be resolved to a key and the
    keys whose delete call failed, so a caller can report honestly rather than
    assume success.
    """
    deleted: list[str] = []
    unresolved: list[str] = []
    failed: list[str] = []
    for url in public_urls or []:
        key = object_key_from_public_url(url)
        if key is None:
            unresolved.append(url)
            continue
        if delete_object(key):
            deleted.append(key)
        else:
            failed.append(key)
    return {"deleted": deleted, "unresolved": unresolved, "failed": failed}


def generate_presigned_upload_url(user_id: str, file_extension: str) -> dict:
    client = _r2_client()

    object_key = f"{user_id}/{uuid4()}.{file_extension}"

    upload_url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": object_key},
        ExpiresIn=3600,
    )

    public_url = f"{settings.r2_public_url.rstrip('/')}/{object_key}"

    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "public_url": public_url,
    }


def generate_presigned_read_url(object_key: str, expires_in: int) -> str:
    client = _r2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": object_key},
        ExpiresIn=expires_in,
    )


def sign_photo_url(url: str | None) -> str | None:
    """Turn a stored public photo URL into a time-limited signed URL.

    Never raises: any failure here must not blank a photo, so on error this
    logs at warning and returns the original url unchanged.

    The signed address is reused for a whole window rather than minted fresh
    per call, or the phone's image cache never hits (a new signature makes a
    "new" address on every request). The window is half the TTL: an address
    minted at the start of a window is handed out until the window ends, so
    even the last recipient still has at least TTL minus window of validity
    left on it.
    """
    global _photo_url_cache_window
    if not url:
        return url
    if not settings.signed_photo_reads:
        return url
    try:
        key = object_key_from_public_url(url)
        if key is None:
            return url
        window = int(time.time()) // settings.photo_read_window_seconds
        if window != _photo_url_cache_window:
            _photo_url_cache.clear()
            _photo_url_cache_window = window
        cached = _photo_url_cache.get(key)
        if cached is not None:
            return cached
        signed = generate_presigned_read_url(key, settings.photo_read_ttl_seconds)
        _photo_url_cache[key] = signed
        return signed
    except Exception:
        logger.warning("r2_sign_photo_url_failed url=%s", url, exc_info=True)
        return url


def sign_photo_urls(urls: list[str | None]) -> list[str | None]:
    return [sign_photo_url(url) for url in urls or []]

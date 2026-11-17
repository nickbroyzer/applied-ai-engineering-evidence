# `code/photo_access/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## A photo address must be the caller's own upload (D588)

`backend/app/utils/photo_ownership.py`, lines 1–40, at `4772472b`. Cited by: LIMITATIONS.md (Private photos); 06-case-studies/09.

```python
"""Refuse a photo address that is not the caller's own upload (security audit 2026-10-13, H1/H2).

Four client fields are stored as photo addresses: listing photo_urls, the avatar, a message
picture and a claim's completion photo. Each must be an object the presign issued to that
user, under their own prefix, or the row could point at another user's object (deleted with
this user's listing or account) or at any host (fetched by the support agent).
"""
import re

from fastapi import HTTPException, status

from app.utils.cloudflare_r2 import is_own_photo_url

# The avatar pack marker the app stores instead of an upload: "pack:" + a 3-digit index.
_AVATAR_PACK = re.compile(r"^pack:\d{3}$")


def _refuse(field: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"{field} must be an address from your own photo upload",
    )


def require_own_photo_url(url: str | None, user_id, *, field: str) -> None:
    """Raise 422 unless `url` is empty or one of `user_id`'s own uploads."""
    if not url:
        return
    if not is_own_photo_url(url, user_id):
        raise _refuse(field)


def require_own_photo_urls(urls: list[str] | None, user_id, *, field: str) -> None:
    for url in urls or []:
        if not is_own_photo_url(url, user_id):
            raise _refuse(field)


def require_own_avatar_url(url: str | None, user_id) -> None:
    """An avatar is an own upload, a pack marker, or nothing."""
```

## Signing fails open to the stored address

`backend/app/utils/cloudflare_r2.py`, lines 165–199, at `4772472b`. Cited by: 01-product-logic/private-photo-access.md; LIMITATIONS.md (Private photos).

```python
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
```

## Deletes touch only the owner's folder

`backend/app/utils/cloudflare_r2.py`, lines 97–127, at `4772472b`. Cited by: 06-case-studies/09; 01-product-logic/private-photo-access.md.

```python
def delete_objects_by_public_url(public_urls: list[str], *, owner_id) -> dict:
    """Delete every object addressed by these public URLs that belongs to `owner_id`.

    Only keys under the owner's own prefix are deleted: a listing's photos go with the
    listing's giver, an account's with the account. A key under anyone else's prefix is
    skipped and logged, never deleted, whatever row it was found on (security audit
    2026-10-13, H1).

    Returns counts plus the URLs that could not be resolved to a key, the keys that
    were skipped for belonging to someone else, and the keys whose delete call failed,
    so a caller can report honestly rather than assume success.
    """
    deleted: list[str] = []
    unresolved: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    owner = str(owner_id)
    for url in public_urls or []:
        key = object_key_from_public_url(url)
        if key is None:
            unresolved.append(url)
            continue
        if owner_id_from_object_key(key) != owner:
            logger.warning("r2_delete_skipped_foreign_key owner=%s key=%s", owner, key)
            skipped.append(key)
            continue
        if delete_object(key):
            deleted.append(key)
        else:
            failed.append(key)
    return {"deleted": deleted, "unresolved": unresolved, "skipped": skipped, "failed": failed}
```

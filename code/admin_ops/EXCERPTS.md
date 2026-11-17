# `code/admin_ops/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## The admin gate

`backend/app/routers/admin.py`, lines 29–35, at `4772472b`. Cited by: 02-architecture/admin-and-ops.md.

```python
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
```

## Sentry webhook: HMAC signature check

`backend/app/routers/watcher.py`, lines 175–214 (first 40 lines of the function), at `4772472b`. Cited by: 02-architecture/admin-and-ops.md; LIMITATIONS.md (Admin and ops).

```python
async def sentry_webhook(request: Request) -> JSONResponse:
    body = await request.body()
    sig_header = request.headers.get("sentry-hook-signature")
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Sentry signature",
        )

    secret = (settings.sentry_webhook_secret or "").strip()
    if not secret:
        logger.error(
            json.dumps({"event": "sentry_webhook_missing_secret_config"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook not configured",
        )

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), sig_header.strip().encode()):
        logger.warning(
            json.dumps({"event": "sentry_webhook_invalid_signature"})
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    resource = request.headers.get("sentry-hook-resource") or ""
    if resource not in ACCEPTED_RESOURCES:
        logger.debug(
            json.dumps({"event": "sentry_webhook_ignored_resource", "resource": resource})
        )
        return JSONResponse(status_code=200, content={"ignored": resource})

    try:
        event = json.loads(body)
    except ValueError:
        raise _invalid_payload() from None
```

## The watcher stream: a 2-second database poll

`backend/app/routers/watcher.py`, lines 329–345, at `4772472b`. Cited by: 02-architecture/admin-and-ops.md; LIMITATIONS.md (Admin and ops).

```python
async def _event_stream(request: Request):
    last_created_at = datetime.now(timezone.utc)
    last_sent = time.monotonic()
    while True:
        if await request.is_disconnected():
            return
        payloads, last_created_at = await asyncio.to_thread(
            _poll_new_events, last_created_at
        )
        if payloads:
            for payload in payloads:
                yield f"data: {json.dumps(payload)}\n\n"
            last_sent = time.monotonic()
        elif time.monotonic() - last_sent >= STREAM_KEEPALIVE_SECONDS:
            yield ": keepalive\n\n"
            last_sent = time.monotonic()
        await asyncio.sleep(STREAM_POLL_SECONDS)
```

# Private photo access

Code and tests: [`../code/photo_access/`](../code/photo_access/). Line numbers
are at Zelbi `8875721`.

## The problem, as it actually was

Until 2026-09-15 every photo in object storage was publicly addressable — not
just listing photos, which are meant to be public, but images sent inside
private conversations and the completion photo a picker takes at the door. The
bucket was reachable through a public development URL; anyone holding or
guessing an address could load it. The internal backlog recorded it as named in
an August audit and not yet actioned.

## The fix

Two changes, in order (backlog, closed 2026-09-15 and confirmed on a device):

1. **Every public route to the bucket was switched off** — the development URL
   disabled and the custom domain removed. A stored photo address on its own now
   loads nothing.
2. **The backend signs every photo address it hands out.** `sign_photo_url`
   (`cloudflare_r2.py:109-143`) turns a stored address into a time-limited
   pre-signed URL. Thirty-three call sites across the routers pass every photo
   field through it before it leaves the API.

So **who can see a photo is decided by which endpoint will give you a signed
URL for it** — the object store itself trusts nobody.

| Photo | Who receives a signed URL |
|---|---|
| Completion photo (taken at handoff) | The picker and the giver on that claim (`routers/claims.py:1003-1006`, excerpt: anyone else gets 403), and admins |
| Message images | The two parties to the conversation (message routes check `assert_can_message` before returning anything), and admins |
| Listing photos, avatars | Anyone who can see the listing or profile — public by design |

## Signed URLs that a phone can still cache

A fresh signature on every request makes a "new" address every time, so the
phone's image cache never hits and every scroll re-downloads every photo. The
signer therefore reuses one signed address per object for a **window of 12
hours**, inside a **24-hour lifetime**: an address minted at the start of a
window is still valid for at least 12 hours after the window ends
(`cloudflare_r2.py:11-16, 115-140`; `config.py:22-24`, not published). The
cache is cleared wholesale when the window advances, so it never grows.

Uploads go the other way: a pre-signed PUT, valid for an hour, to a key that
starts with the uploader's user id (`cloudflare_r2.py:80-97`).

## Tests

26 `def test_` functions: `test_signed_photo_reads.py` (21) and
`test_r2_delete.py` (5).

## Honest limits

- **A signed URL is a bearer URL.** Anyone it is forwarded to can load the
  photo until it expires (up to 24 hours).
- **Signing fails open — to a dead address.** On any error `sign_photo_url`
  logs and returns the stored, unsigned address unchanged (:141-143), by design
  so an error never blanks a photo. Because the public routes are off, that
  address no longer loads anything, so nothing leaks; but the code does not
  fail *closed*.
- **One switch controls it.** Signing only happens when `signed_photo_reads` is
  on (:125-126); the default in code is off and production sets it on. A
  development backend once ran with it off against production data, handing out
  dead addresses (backlog, 2026-09-15). It is kept as a deliberate safety switch.
- **Photo keys supplied by the client are not ownership-checked** on the
  completion-photo and message-image paths. The listing-analysis endpoint does
  check that the caller owns the object key it names
  ([`../code/ai_service/routers_ai.py`](../code/ai_service/routers_ai.py)).
- **Completion photos outlive account deletion**, kept as evidence of the
  handoff.

## What is never claimed

That photos are end-to-end private, that a signed URL cannot be shared, or that
access control lives in the storage layer.

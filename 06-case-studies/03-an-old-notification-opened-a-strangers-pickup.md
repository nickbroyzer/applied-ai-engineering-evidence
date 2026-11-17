# 3. An old notification opened a stranger's pickup

**In short:** after a cancel, a relist and a re-claim, tapping an old notification could open someone else's handoff, with their pickup details. One screen loaded "the newest claim on this item" when it should have loaded "the claim this notification is about".

## What broke
A notification carries both the listing and the claim it refers to. The handoff screen ignored the claim and asked the server for the newest claim on the listing.

Cancelling a claim returns the same listing to active, so one item can have several claims over time. After a cancel, a relist and a new claim by someone else, an old notification resolved to the new person's claim. Either it showed a stranger's pickup, or it answered 403 when the viewer had no claim at all.

## Why it's a privacy bug, not a display bug
The screen was showing one person's handoff details to someone else, and only because they held a stale notification.

## The fix
The screen loads the claim id the notification itself carries. It falls back to the listing lookup only for entry points that have no claim id:

```ts
// LOAD THE CLAIM WE WERE GIVEN, not the newest one on this listing.
getClaimByListing(listingId)
// became
claimId
  ? getClaimById(claimId).catch(() => getClaimByListing(listingId))
  : getClaimByListing(listingId)
```

The same fix went into the choose-a-time screen. Commit `138cce7`, 2026-08-28 (D402).

The server enforces it too. `GET /claims/{id}` answers 403 with `{"detail": "Not a party to this claim"}` to anyone who is neither the picker nor the giver. A test now proves it: `test_stranger_requesting_a_claim_by_id_is_refused_with_no_pickup_details` (commit `0cd7e3ce`). The same test confirms the picker and giver do see the details. A second test, `test_unknown_claim_id_is_404_not_403`, confirms an unknown id answers 404. The app has no screen tests, so the screen-side fix is proven by the code and a device walk.

## What this shows
"Latest record for this parent" is a convenient lookup and a common source of leaks. Identity should travel with the event.

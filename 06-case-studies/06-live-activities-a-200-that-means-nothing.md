# 6. Live Activities: a 200 that means nothing

**In short:** Apple answers 200 to an update for a lock-screen card the phone no longer shows. The server trusted its own records and its 200s, so it held back an arrival banner for a card that wasn't there. The fix was to make the phone report what it really has, then to send the card or a banner for each moment, never both and never neither.

## What broke
Zelbi shows a live pickup card on the lock screen and Dynamic Island. That's native Swift work: a widget target, the island views and an App Intent for the buttons. When a card is up, the card is the alert, so the server skips the banner.

That decision rested on three wrong assumptions:
- The phone reported a card gone only while the app was running.
- Apple returns 200 for a card that no longer exists.
- The server's "does a card carry this moment?" check trusted its own row.

So a person who had swiped the card away got no banner and no card.

## The fix, in two steps
1. **Reconcile (D625).** The phone lists the cards it really has and posts that list at every launch, every return to the foreground, every background push wake, at sign-in, and right before every arrival call (waiting at most 4 seconds). Cards the server thinks are open but the phone doesn't list are marked dismissed.
2. **Card or banner, never both (D627).** A test on build 18 showed a swipe reaches the server within about a second even with the app force-quit. So the server can know when a card is gone. A moment now goes to the card only if a card that can still show it exists, and otherwise to a banner. The server keeps the latest swipe, not the first (D628).

There are 135 backend test functions across the Live Activity and push-sender test files.

## What this shows
A success code from a third party says the request was accepted, not that the user saw anything. The fix was to get ground truth from the device.

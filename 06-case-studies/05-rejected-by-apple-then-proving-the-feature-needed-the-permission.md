# 5. Rejected by Apple, then proving the feature needed the permission

**In short:** Apple rejected the app under Guideline 2.5.4 for asking for background location. The first fix kept the feature without the permission, and real walk data showed it couldn't fire at the door. The final answer was a narrowly scoped use of the permission plus a recording that proved it. Apple approved build 20 by 2026-11-03, and it was released on 2026-11-04.

## What broke
Build 14 was rejected on 2026-10-26. Apple's reviewer found `location` in the background modes and no feature that needed it. Apple offered two options: reply with a screen recording on a physical device, or remove the mode.

## First answer: remove the mode, keep the feature
Removing the setting alone would have silently broken arrival detection. The location library refuses to register geofences without the background mode, throwing an error. So the guard was patched out of the library and the mode was removed (`a6e663bc`, 2026-10-26).

## What the walk data showed
Build 19 was walked on a real iPhone, with every check logged:
- At the 150 m ring, iOS woke the app and it logged 18 checks in 4 seconds, at 118 to 119 m with 8 to 9 m accuracy.
- At the 100 m ring it logged 3 checks at 67 m, then no more wakes. **Nothing fired at the door.**
- iOS delivered each wake about 32 m inside its ring.
- At the door, the screen's data load failed on the network, so no check ran until a manual retry stamped at 11 m.

Rings alone could not reliably detect arrival at the door.

## Final answer
A silent third ring at 50 m was added, and failed loads now retry (D635). Then the background mode came back for **one feature only**, arrival detection (D636, amended by D637):
- A continuous location stream starts only near the item: when the pickup screen's own check measures the phone within 600 m, or, with the screen closed, at the first significant-change report within 1 km.
- It stops after 15 minutes, beyond 1.5 km, or at the pickup window's end.
- The blue location indicator stays on.
- The rings stay as a fallback.
- The stamp rule is unchanged: one reading within 25 m whose own accuracy is 20 m or better. No coordinates reach the server.

The proving walk doubled as the App Review recording. The reply and the recording went to Apple on 2026-10-28 with build 20. A fallback was decided in advance: if Apple rejected it again, build 21 would ship without the mode.

**Result:** the device walk and the recording drive passed. Apple approved build 20 by 2026-11-03, and it was released on 2026-11-04. The arrival rule is pure code with its own Node test file: 110 tests, as `node --test` reports them.

## What this shows
A policy fight is won with evidence, not argument. The library patch was the right first move. The walk data showed its limit. The final answer used the permission only where the data said it was needed, and proved it.

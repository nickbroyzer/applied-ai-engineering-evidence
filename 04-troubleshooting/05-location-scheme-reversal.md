# I reversed my own location privacy scheme, offline, to nanometre precision

**Commit:** `26eaa9bb7fc6e48cb637a7db9d16fb321a5fd0d5` · 2026-08-11
**Message, verbatim:** `coordinate privacy: the fuzzed point is keyed by a server secret and every stored point is recomputed under it`
**Decision:** [`D323`](../03-decisions/privacy/D323.md) · related [`D320`](../03-decisions/privacy/D320.md), [`D321`](../03-decisions/privacy/D321.md), [`D322`](../03-decisions/privacy/D322.md)
**Code:** [`../code/coordinate_privacy/coordinate_privacy.py`](../code/coordinate_privacy/coordinate_privacy.py)
**Tests:** [`../code/coordinate_privacy/test_coordinate_privacy.py`](../code/coordinate_privacy/test_coordinate_privacy.py)

## Symptom

None. Nothing was broken, no error was raised, and no user reported anything.
This was found by auditing a design I had written myself and asking the only
question that matters about an obfuscation scheme: *what does an attacker who
knows the algorithm actually need?*

## Diagnosis

Listings are shown on a public map at an approximate point rather than the
giver's real address. The original derivation seeded a pseudo-random generator
from the **listing id** and drew an angle and a distance from it.

The listing id is printed in every feed row.

So the offset was a pure function of a value the attacker already has. Anyone
who reconstructed the recipe could replay both draws for every listing and
recover the true point — **offline, retroactively, sending no request**, with no
rate limit to hit and nothing to detect. Worse than a leak, because there is no
trace of it happening.

The audit performed that reversal on **eight listings** and recovered the true
coordinates to within nanometres. Not "in principle" — actually done, against
real stored rows, before writing a line of the fix.

That step matters more than the fix. A design flaw argued in the abstract gets
weighed against effort and deferred. A design flaw *demonstrated*, with the real
addresses printed next to the fuzzed ones, is not deferred.

## What the original design got right

Two properties were correct and had to survive:

1. **The offset is stable per listing.** A point that moves between requests is
   a triangulation oracle — sample the same listing repeatedly and the true
   position is the centre of the cloud.
2. **Distance is computed from the fuzzed point, not the true one.** A distance
   computed from the truth and displayed alongside a fuzzed point leaks the
   truth through the distance.

A fix that broke either of those would have been a regression dressed as a
security improvement.

## Fix

Key the derivation with a server secret. Angle and distance now come from an
HMAC-SHA256 of the listing id under a secret held in the secrets manager, rather
than from a PRNG seeded by the id alone:

```python
digest = hmac.new(secret.encode(), listing_id.bytes, hashlib.sha256).digest()
angle      = (int.from_bytes(digest[0:8], "big") / 2**64) * 2 * math.pi
distance_m = 120 + (int.from_bytes(digest[8:16], "big") / 2**64) * 130
```

Two independent 8-byte words from one digest drive the two draws. Replay is now
impossible without the secret, and both properties above are preserved exactly:
same listing, same offset; distance still measured from the fuzzed point.

An unset secret **warns loudly** rather than failing, so test runs work without
the secrets manager while a misconfigured production cannot go silently unkeyed.
That is a deliberate trade and it is a weakness — see the limitation below.

## The part people forget: the migration

Changing the derivation changes the output. Stored approximate columns computed
under the old recipe do not update themselves — points would have silently
changed **for new listings only**, leaving the entire existing corpus reversible
while the code looked fixed.

So the fix is not the HMAC. The fix is the HMAC **plus a recompute of every
stored row**. All 127 listings' approximate columns were recomputed under the
new secret in a single transaction, and every resulting offset was verified to
fall inside the expected metre band **before the transaction committed**.

The same applies to rotation, and the docstring says so: rotating the secret
requires re-running the recompute, or the same silent split reappears.

## Test

Fifteen collected cases (ten `def test_` functions; the difference is
parametrisation — see [`../verification/repo-metrics-2026-09-03.md`](../verification/repo-metrics-2026-09-03.md)).
Two carry the properties:

- **distance in range** — the derived offset lands inside the metre band, which
  is what makes the recompute verifiable
- **seeded stability** — the same listing yields the same point every time,
  which is the anti-triangulation property

## Limitations, stated

- An unset secret **warns and continues unkeyed** rather than refusing to start.
  A misconfigured deployment degrades to the reversible scheme with only a log
  line to show for it.
- Rotation is a **recorded manual procedure**, not automation. It has been
  performed and verified once; nothing enforces that it is done correctly next
  time.
- Exact coordinates are released to the giver and, after payment authorization,
  to the picker — latched at authorization so cancelled and no-show receipts
  keep them. The correct description is the two-tier one; "only during an active
  claim" is wrong and is not claimed here.

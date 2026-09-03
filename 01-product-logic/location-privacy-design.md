# Location privacy — two tiers, and the defect that was reversible

Full incident write-up:
[`../04-troubleshooting/05-location-scheme-reversal.md`](../04-troubleshooting/05-location-scheme-reversal.md).
Code and tests: [`../code/coordinate_privacy/`](../code/coordinate_privacy/).

## The problem

Every listing is at someone's home. The map has to be useful — a picker must
know whether an item is worth crossing town for — while never publishing where
anyone lives.

## Two tiers

**Public surfaces see an approximate point.** Feed, map, proximity search, and a
stranger's profile all read stored `*_approx` columns
([`D321`](../03-decisions/privacy/D321.md)). Not the true point rounded — a
separate stored value.

**Exact coordinates go to the giver, and to a payment-authorized picker.** On the
listing endpoint the disclosure is gated by claim status; on the claim endpoints
it is **latched at authorization**, so cancelled and no-show receipts keep the
address they were shown ([`D320`](../03-decisions/privacy/D320.md),
[`D322`](../03-decisions/privacy/D322.md)).

That latching matters. A receipt whose address disappears when the claim ends is
not a receipt. The correct sentence is the two-tier one; **"exact coordinates
only during an active claim" is wrong** and is not claimed here.

## The two properties that make fuzzing work

Most naive obfuscation fails one of these:

1. **The offset is stable per listing.** A point that moves between requests is a
   triangulation oracle: sample repeatedly and the true position is the centre of
   the cloud.
2. **Distance is computed from the fuzzed point.** Displaying a fuzzed pin beside
   a distance measured from the truth leaks the truth through the distance.

## The defect, and why it was reversible

The original derivation seeded a PRNG from the **listing id** — a value printed
in every feed row. The offset was therefore a pure function of something the
attacker already had. Anyone who reconstructed the recipe could recover every
true point **offline, retroactively, sending no request**: no rate limit to hit,
no log line, nothing to detect.

The audit performed that reversal on eight listings and recovered true
coordinates to nanometre precision. Demonstrated, not argued.

## The fix, and the half people forget

Angle and distance now come from an HMAC-SHA256 of the listing id under a server
secret ([`D323`](../03-decisions/privacy/D323.md)). Replay is impossible without
the secret; both properties above are preserved exactly.

The fix is **not** the HMAC alone. Changing the derivation changes the output,
and stored columns do not recompute themselves — points would have changed
silently *for new listings only*, leaving the whole existing corpus reversible
while the code looked fixed. So the fix is the HMAC **plus** a recompute of all
127 listings' approximate columns in a single transaction, with every resulting
offset verified inside the expected metre band **before commit**.

Rotation carries the same obligation, and the code's docstring says so.

## Tests

Fifteen collected cases; ten `def test_` functions. Two carry the properties: the
derived offset lands inside the metre band, and the same listing yields the same
point every time.

## Limitations

- An unset secret **warns and continues unkeyed** rather than refusing to start.
  A misconfigured deployment degrades to the reversible scheme with a log line.
- Rotation is a **manual recorded procedure**, performed and verified once.
  Nothing enforces it is done correctly next time.
- **No server-side EXIF strip and no regression guard.** A live check on
  2026-08-11 found a stored published photo carrying no GPS and no camera
  identifiers — one flow, one date. That is a dated observation, not a control.

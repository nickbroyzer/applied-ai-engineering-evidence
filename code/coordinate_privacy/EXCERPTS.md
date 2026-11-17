# `code/coordinate_privacy/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## The keyed approximate point, and the warning when the key is unset

`backend/app/services/coordinate_privacy.py`, lines 18–48, at `4772472b`. Cited by: 04-troubleshooting/05-location-scheme-reversal.md; LIMITATIONS.md (Location privacy).

```python
def generate_approximate_point(
    true_lat: float, true_lng: float, listing_id: uuid.UUID
) -> tuple[float, float]:
    """Derive the listing's public fuzzed point from its id AND a server secret.

    The previous derivation seeded a PRNG from the listing id alone — a pure
    function of a value printed in every feed row — so anyone who reconstructed
    the recipe could replay both draws and recover every listing's true point
    offline, retroactively, sending no request. The audit performed that
    reversal to within nanometres on eight listings. Keying the derivation with
    COORD_FUZZ_SECRET ([secrets manager], dev+prd) makes replay impossible without the
    secret while preserving the two properties the design got right: the offset
    is stable per listing, and distance is computed from the fuzzed point,
    which is what defeats triangulation. Rotating the secret requires
    recomputing every stored *_approx column, or points silently change only
    for NEW listings.
    """
    secret = os.environ.get("COORD_FUZZ_SECRET", "")
    if not secret:
        # Deterministic fallback so test runs work without [secrets manager]; loud so a
        # misconfigured production cannot go silently unkeyed.
        _logger.warning("COORD_FUZZ_SECRET is not set; coordinate fuzzing is UNKEYED")
    digest = hmac.new(secret.encode(), listing_id.bytes, hashlib.sha256).digest()
    # Two independent 8-byte words from the digest drive angle and distance.
    angle = (int.from_bytes(digest[0:8], "big") / 2**64) * 2 * math.pi
    distance_m = 120 + (int.from_bytes(digest[8:16], "big") / 2**64) * 130
    dlat = (distance_m * math.cos(angle)) / 111320
    dlng = (distance_m * math.sin(angle)) / (111320 * math.cos(math.radians(true_lat)))
    out_lat = max(-90.0, min(90.0, true_lat + dlat))
    out_lng = ((true_lng + dlng + 540) % 360) - 180
    return (out_lat, out_lng)
```

## Who sees the true location

`backend/app/services/coordinate_privacy.py`, lines 51–70, at `4772472b`. Cited by: 01-product-logic/location-privacy-design.md.

```python
def should_reveal_true_location(
    listing_id: uuid.UUID,
    requester_id: uuid.UUID,
    giver_id: uuid.UUID,
    db: "Session",
) -> bool:
    from app.models import Claim  # local import avoids circular dependency

    if requester_id == giver_id:
        return True
    claim = (
        db.query(Claim)
        .filter(
            Claim.listing_id == listing_id,
            Claim.picker_id == requester_id,
            Claim.status.in_(_REVEAL_STATUSES),
        )
        .first()
    )
    return claim is not None
```

## Test: the nearby feed returns approximate points, never true ones

`backend/tests/test_coordinate_privacy.py`, lines 80–93, at `4772472b`. Cited by: 04-troubleshooting/05-location-scheme-reversal.md.

```python
def test_nearby_returns_approx_not_true_coords(client, active_listing):
    resp = client.get(
        "/listings/nearby",
        params={"lat": active_listing.location_lat, "lng": active_listing.location_lng, "radius_km": 1},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 1
    item = next(i for i in items if i["id"] == str(active_listing.id))
    # Feed must return approx values
    assert item["location_lat"] == pytest.approx(active_listing.location_lat_approx, abs=1e-9)
    assert item["location_lng"] == pytest.approx(active_listing.location_lng_approx, abs=1e-9)
    # And approx differs from true
    assert item["location_lat"] != pytest.approx(active_listing.location_lat, abs=1e-9)
```

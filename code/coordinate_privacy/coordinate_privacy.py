import hashlib
import hmac
import logging
import math
import os
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_REVEAL_STATUSES = frozenset({"authorized", "pickup_scheduled", "completed", "auto_captured"})


_logger = logging.getLogger(__name__)


def generate_approximate_point(
    true_lat: float, true_lng: float, listing_id: uuid.UUID
) -> tuple[float, float]:
    """Derive the listing's public fuzzed point from its id AND a server secret.

    The previous derivation seeded a PRNG from the listing id alone — a pure
    function of a value printed in every feed row — so anyone who reconstructed
    the recipe could replay both draws and recover every listing's true point
    offline, retroactively, sending no request. The audit performed that
    reversal to within nanometres on eight listings. Keying the derivation with
    COORD_FUZZ_SECRET (Doppler, dev+prd) makes replay impossible without the
    secret while preserving the two properties the design got right: the offset
    is stable per listing, and distance is computed from the fuzzed point,
    which is what defeats triangulation. Rotating the secret requires
    recomputing every stored *_approx column, or points silently change only
    for NEW listings.
    """
    secret = os.environ.get("COORD_FUZZ_SECRET", "")
    if not secret:
        # Deterministic fallback so test runs work without Doppler; loud so a
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

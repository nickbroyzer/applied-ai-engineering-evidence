"""
Daily recommendations scan job.

For each located user, derives their interest categories from saves and claims
in the last 60 days, then finds new active listings posted in the last 24 hours
within 50 miles that match those categories. If any are found, fires one rollup
push notification per user per day.

Per-user-per-day idempotency: send_push uses (notification_type="recommended_listings",
entity_id=user.id, date_bucket=today) as the key. The idempotency row is only
written on a successful HTTP push. Users with notify_recommendations=False will
receive an inbox row but no push, and the idempotency row is not written — so a
second scan run the same day produces another inbox row for them. Acceptable for
now; no new tables added.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Claim, Listing, Saved, User
from app.services.notification_service import send_push

logger = logging.getLogger(__name__)

_RADIUS_M = 50 * 1609.34
_CATEGORY_WINDOW_DAYS = 60
_LISTING_WINDOW_HOURS = 24


def run_recommendation_scan(db: Session) -> int:
    now = datetime.utcnow()
    category_cutoff = now - timedelta(days=_CATEGORY_WINDOW_DAYS)
    listing_cutoff = now - timedelta(hours=_LISTING_WINDOW_HOURS)

    users = (
        db.query(User)
        .filter(
            User.location_lat.isnot(None),
            User.location_lng.isnot(None),
        )
        .all()
    )

    notified = 0
    notifications_added = False

    for user in users:
        saved_categories = {
            row[0]
            for row in (
                db.query(Listing.category)
                .join(Saved, Saved.listing_id == Listing.id)
                .filter(
                    Saved.user_id == user.id,
                    Saved.created_at >= category_cutoff,
                )
                .distinct()
                .all()
            )
        }
        claimed_categories = {
            row[0]
            for row in (
                db.query(Listing.category)
                .join(Claim, Claim.listing_id == Listing.id)
                .filter(
                    Claim.picker_id == user.id,
                    Claim.claimed_at >= category_cutoff,
                )
                .distinct()
                .all()
            )
        }
        categories = saved_categories | claimed_categories
        if not categories:
            continue

        candidates = (
            db.query(Listing)
            .filter(
                Listing.status == "active",
                Listing.available_since >= listing_cutoff,
                Listing.category.in_(list(categories)),
                Listing.giver_id != user.id,
                ~Listing.id.in_(
                    db.query(Saved.listing_id).filter(Saved.user_id == user.id)
                ),
            )
            .filter(
                text(
                    "ST_DWithin("
                    "ST_MakePoint(listings.location_lng, listings.location_lat)::geography, "
                    "ST_MakePoint(:lng, :lat)::geography, "
                    ":radius_m"
                    ")"
                ).bindparams(
                    lng=user.location_lng,
                    lat=user.location_lat,
                    radius_m=_RADIUS_M,
                )
            )
            .order_by(Listing.available_since.desc())
            .all()
        )

        if not candidates:
            continue

        n = len(candidates)
        title = "New finds near you"
        body = f'"{candidates[0].title}" and more are waiting nearby.'

        try:
            send_push(
                db,
                user.id,
                title,
                body,
                {"type": "recommended_listings", "count": n},
                "recommended_listings",
                user.id,
                digest=True,
            )
        except Exception:
            logger.exception("send_push_failed_recommendation")

        notified += 1
        notifications_added = True

    if notifications_added:
        db.commit()

    return notified

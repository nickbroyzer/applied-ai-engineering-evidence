import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Listing
from app.services.notification_service import send_push

logger = logging.getLogger(__name__)


def expire_active_listings(db: Session) -> int:
    expiring = (
        db.query(Listing)
        .filter(Listing.status == "active", Listing.expires_at < datetime.utcnow())
        .all()
    )
    count = 0
    for listing in expiring:
        if listing.auto_relist:
            listing.expires_at = datetime.utcnow() + timedelta(days=7)
        else:
            listing.status = "expired"
            count += 1
    db.commit()
    return count


def send_listing_expiring_reminders(db: Session) -> tuple[int, int]:
    now = datetime.utcnow()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    listings = (
        db.query(Listing)
        .filter(
            Listing.status == "active",
            Listing.expires_at >= window_start,
            Listing.expires_at < window_end,
        )
        .all()
    )

    sent_count = 0
    skipped_count = 0
    for listing in listings:
        try:
            sent = send_push(
                db=db,
                user_id=listing.giver_id,
                title="Listing expiring soon",
                body=listing.title,
                data={
                    "type": "listing_expiring",
                    "listing_id": str(listing.id),
                },
                notification_type="listing_expiring",
                entity_id=listing.id,
            )
            if sent:
                sent_count += 1
            else:
                skipped_count += 1
        except Exception:
            logger.exception("send_push_failed_listing_expiring")
            skipped_count += 1

    return sent_count, skipped_count

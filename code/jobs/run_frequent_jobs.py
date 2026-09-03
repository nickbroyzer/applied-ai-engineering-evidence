import logging

from app.database import SessionLocal
from app.jobs.listing_expiry import expire_active_listings, send_listing_expiring_reminders
from app.jobs.pending_payment_sweeper import run_pending_payment_sweeper
from app.jobs.pickup_reminder import run_pickup_reminder
from app.jobs.post_window_sweeper import run_post_window_sweeper
from app.observability import capture_exception, flush_sentry, init_sentry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    init_sentry("frequent-jobs")
    jobs = [
        ("expire_active_listings", expire_active_listings),
        ("send_listing_expiring_reminders", send_listing_expiring_reminders),
        # T-1h reminder searches a 10-minute band, so it must run at least every
        # 10 minutes or it silently matches nothing. Safe at this cadence: per-claim
        # per-day idempotency lives in notification_idempotency.
        ("run_pickup_reminder", run_pickup_reminder),
        # The sweeper's own module docstring specifies a 5-minute cadence; it had been
        # running once daily, so a 24h capture threshold behaved like 24-48h. Safe here:
        # capture and cancel both transition claim status, and every reminder inside it
        # goes through per-claim per-day idempotency.
        ("post_window_sweeper", run_post_window_sweeper),
        # Abandoned pending_payment claims (PENDING_PAYMENT_TIMEOUT = 5 minutes) are
        # never selected by any other job, so this must run at least that often or
        # a killed-app checkout can strand a listing indefinitely.
        ("pending_payment_sweeper", run_pending_payment_sweeper),
    ]
    db = SessionLocal()
    failures = 0
    try:
        for label, fn in jobs:
            try:
                result = fn(db)
                logger.info("frequent_job_completed job=%s result=%s", label, result)
            except Exception as exc:
                failures += 1
                capture_exception(exc, job=label)
                logger.exception("frequent_job_failed job=%s", label)
    finally:
        db.close()
        flush_sentry()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

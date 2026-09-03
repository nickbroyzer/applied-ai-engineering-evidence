import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.jobs.saved_deadline_scan import run_saved_deadline_scan
from app.jobs.recommendation_scan import run_recommendation_scan
from app.services.notification_service import send_daily_digest_summaries
from app.observability import capture_exception, flush_sentry, init_sentry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    init_sentry("daily-jobs")
    run_start = datetime.now(timezone.utc)
    jobs = [
        ("saved_deadline_scan", run_saved_deadline_scan),
        ("recommendation_scan", run_recommendation_scan),
    ]
    db = SessionLocal()
    failures = 0
    try:
        for label, fn in jobs:
            try:
                result = fn(db)
                logger.info("daily_job_completed job=%s result=%s", label, result)
            except Exception as exc:
                failures += 1
                capture_exception(exc, job=label)
                logger.exception("daily_job_failed job=%s", label)
        try:
            sent = send_daily_digest_summaries(db, since=run_start)
            logger.info("daily_job_completed job=daily_digest_summaries result=%s", sent)
        except Exception as exc:
            failures += 1
            capture_exception(exc, job="daily_digest_summaries")
            logger.exception("daily_job_failed job=daily_digest_summaries")
    finally:
        db.close()
        flush_sentry()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.jobs.saved_deadline_scan import run_saved_deadline_scan
from app.jobs.knowledge_log_retention import run_knowledge_log_retention
from app.jobs.recommendation_scan import run_recommendation_scan
from app.services.notification_service import send_daily_digest_summaries
from app.observability import capture_exception, flush_sentry, init_sentry
from app.services.job_runs import counts_text, record_run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    init_sentry("daily-jobs")
    run_start = datetime.now(timezone.utc)
    jobs = [
        ("saved_deadline_scan", run_saved_deadline_scan),
        ("recommendation_scan", run_recommendation_scan),
        ("knowledge_log_retention", run_knowledge_log_retention),
    ]
    db = SessionLocal()
    failures = 0
    try:
        for label, fn in jobs:
            started_at = datetime.now(timezone.utc)
            try:
                result = fn(db)
                logger.info("daily_job_completed job=%s result=%s", label, result)
            except Exception as exc:
                failures += 1
                capture_exception(exc, job=label)
                logger.exception("daily_job_failed job=%s", label)
                record_run(label, started_at, result="failed", error=f"{type(exc).__name__}: {exc}")
            else:
                record_run(label, started_at, result="ok", counts=counts_text(label, result))
        digest_started_at = datetime.now(timezone.utc)
        try:
            sent = send_daily_digest_summaries(db, since=run_start)
            logger.info("daily_job_completed job=daily_digest_summaries result=%s", sent)
        except Exception as exc:
            failures += 1
            capture_exception(exc, job="daily_digest_summaries")
            logger.exception("daily_job_failed job=daily_digest_summaries")
            record_run("daily_digest_summaries", digest_started_at, result="failed", error=f"{type(exc).__name__}: {exc}")
        else:
            record_run("daily_digest_summaries", digest_started_at, result="ok", counts=counts_text("daily_digest_summaries", sent))
    finally:
        db.close()
        flush_sentry()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

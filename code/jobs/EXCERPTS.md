# `code/jobs/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## The 10-minute runner and its job list

`backend/app/jobs/run_frequent_jobs.py`, lines 18–57 (first 40 lines of the function), at `4772472b`. Cited by: 06-case-studies/01; 01-product-logic/marketplace-state-machine.md.

```python
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
        # D553: a welcome that failed at profile completion, and the invite email three days
        # on. The invite send has a local-daytime window, so it needs this cadence. Both
        # return at once while EMAIL_POSTAL_ADDRESS is empty.
        ("retry_welcome_emails", retry_welcome_emails),
        ("send_invite_emails", send_invite_emails),
        # D578 §4.8: deadline alerts at hours 20 and 23 always; the hour-23 agent action only
        # while the agents master switch is on and support is not Off.
        ("agent_check", agent_timer.run_agent_check),
        # D622: App Review watcher; returns "off" at once while REVIEW_WATCHER_ENABLED is off.
        ("review_watcher", run_review_watcher),
    ]
    db = SessionLocal()
    failures = 0
    try:
        for label, fn in jobs:
            started_at = datetime.now(timezone.utc)
            try:
                result = fn(db)
                logger.info("frequent_job_completed job=%s result=%s", label, result)
            except Exception as exc:
                failures += 1
                capture_exception(exc, job=label)
```

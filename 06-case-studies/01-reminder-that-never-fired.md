# The reminder that had never fired

**In short:** four production notifications had never sent once. The job ran every ten minutes and reported success, and the test for it was green. The test passed only because it built a claim the app can never create.

## What broke
Zelbi sends a "your pickup is tomorrow" reminder to both people, with a different version for curbside and meet-up. That's four notification types. None of them had ever been sent in production. Nothing errored and no alert fired. They were found while the app's notifications were being reworked in late August (D410).

## The cause
These reminders had been added inside an existing loop: the deadline nudges that chase claims where nothing has been arranged yet. That loop's query selects claims with status `authorized`.

Every route that sets a pickup time also sets the status to `pickup_scheduled`, in the same statement. A claim with a pickup time can therefore never still be `authorized`. No claim could match the query, so the reminders could never fire.

## Why the test didn't catch it
The test for this reminder was green the whole time. Its fixture writes status `authorized` and a pickup time together in one raw SQL update:

```python
"UPDATE claims SET status='authorized', authorized_at=:a,"
" pickup_mode=:m, proposed_times=CAST(:pt AS jsonb),"
" pickup_scheduled_at=:psa"
```

The application can never produce that row. The test proved the reminder works for a claim that cannot exist.

## The fix
The reminders got their own query, selecting on what their words promise: a pickup between 23 and 25 hours away, in either status.

```python
def _eligible_for_imminent_reminder(db: Session, now: datetime) -> list[Claim]:
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)
    return (
        db.query(Claim)
        .filter(
            Claim.status.in_(("authorized", "pickup_scheduled")),
            Claim.pickup_scheduled_at.isnot(None),
            Claim.pickup_scheduled_at >= window_start,
            Claim.pickup_scheduled_at < window_end,
        )
        .all()
    )
```

Shipped in commit `906a60a` on 2026-08-29. The function's docstring records the cause, so the next reader doesn't re-create it.

## What I'd do differently
Any state a scheduled job selects on should be built in tests through the app's own write paths, not through raw SQL. A fixture that can write any row will happily write an impossible one.

That test now exists: `test_imminent_reminder_fires_for_a_claim_booked_through_the_real_routes` (commit `0cd7e3ce`). The giver proposes times through the real route and the picker selects one, so the claim reaches `pickup_scheduled` the way production writes it. One sweep sends both reminders, and a second sends nothing new. The test stubs only the 9 AM to 9 PM pickup-hours check: a pickup exactly 24 hours out falls outside those hours for part of every day, so it couldn't otherwise be booked at every hour the suite might run.

## The same family: jobs that report success while doing nothing
- **The one-hour reminder** searched a 10-minute window but ran on the daily job, so it almost never matched. It moved to the 10-minute job (`a2197e88`, 2026-07-27). The rule since then: a job that searches a time window must run at least as often as the window is wide.
- **Time-critical pickup and money notifications** went through the daily-digest path. That path writes an inbox row and returns before any push is sent, so these never reached a phone. They now send immediately (`f857bd2e`, 2026-07-27).
- **iOS silently drops every push that arrives while the app is open** unless the app registers a notification handler. Zelbi had none. The handler was added in `93213060` (2026-08-27).

## What this shows
"It ran" and "it worked" are different claims, and only the second one counts. Tests have to start from states production can actually reach.

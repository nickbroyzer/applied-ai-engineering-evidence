# 4. One error code with two opposite meanings

**In short:** when the payment sweeper cancelled an expired hold and Stripe answered "no such payment", the claim was written off. That's right when the id was never real. It's dangerous when the id is real but the server is talking to a different Stripe account, because a live hold on someone's card would be abandoned while our records say it's gone.

## What broke
Found on 2026-07-26 while tracing why an expired claim still showed in the app. Any claim whose cancel failed was dropped by the sweeper permanently, with no alert.

## The cause
Stripe's `resource_missing` has two causes:
1. **The id was never issued by Stripe.** Seeded and test rows carry hand-written ids. Nothing is held, so it's safe to move on.
2. **The id is real but belongs to another account,** for example a wrong or rotated key. A real hold may still be live. Writing the claim off would abandon a customer's money.

## The fix
The case is forgiven only when the id itself cannot be one Stripe issued:

```python
# A PaymentIntent id Stripe actually issued is "pi_" followed by 24 or more
# alphanumeric characters. Seeded and reproduction rows carry hand-written
# references that cannot match this, and those never had a hold behind them.
_REAL_PI_RE = re.compile(r"^pi_[A-Za-z0-9]{24,}$")
```

A real-looking id that Stripe can't find is no longer written off. The claim is left exactly as it is and logged at error level as `auto_cancel_orphaned_hold_suspected`, for a person to resolve. Commit `db9cb43f`, 2026-07-27.

Tests cover the synthetic branch: it skips the synthetic id and still captures the real one. A related rule came later (D584): seed-marked ids never reach Stripe at all.

Both branches are now tested (commit `0cd7e3ce`):
- `test_real_shaped_id_that_stripe_cannot_find_is_left_untouched_and_logged`: the claim and listing rows are unchanged after the sweep, and one `auto_cancel_orphaned_hold_suspected` error is logged.
- `test_synthetic_id_that_stripe_cannot_find_is_forgiven_and_cancelled`: the claim is cancelled, the listing goes back to active, and no orphan log is written.

## What this shows
An error code isn't a diagnosis. When one code can mean "safe" or "someone's money is stuck", decide on something you can check, and send the other case to a human.

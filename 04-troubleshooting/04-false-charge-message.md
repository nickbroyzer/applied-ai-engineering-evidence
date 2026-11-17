# The sweeper that would have cancelled claims people had paid for

**Commit:** `14243ef3cbc1d93b3d4fffe60666b6c6e9f17572` · 2026-08-11
**Message, verbatim:** `claims: a picker who actually paid keeps his claim when the authorize webhook never lands`
**Code:** [`../code/payments/EXCERPTS.md`](../code/payments/EXCERPTS.md)
**Tests:** [`../code/payments/EXCERPTS.md`](../code/payments/EXCERPTS.md)

## Symptom

This one was found by reasoning about a state, not by an error report — which is
the only reason it is in this file. It would have produced the worst class of
bug the platform can have: **a person is charged, and the thing they paid for is
taken away.**

## Diagnosis

A claim sits in `pending_payment` between checkout and Stripe's confirmation. A
sweeper existed to clean up the abandoned ones: the picker closed the app before
the client-side cancel ran, or Stripe never confirmed. Nothing else selects on
that status, so nothing else was releasing them. The sweeper cancelled the
PaymentIntent, cancelled the claim, and relisted the item.

The sweeper's assumption was that `pending_payment` past the timeout means *no
money moved*. That assumption has a hole.

A claim can also sit in `pending_payment` because **the authorization webhook was
never delivered.** In that case the picker did pay: a live hold exists on their
card, and the only thing missing is the platform's own record of it. To the
sweeper, that claim is indistinguishable from an abandoned one — same status,
same age. It would have cancelled a paid claim and relisted the item.

The database was not the authority here. Stripe was, and nothing was asking it.

## Fix

Before cancelling anything, read the PaymentIntent's true state from the
provider and branch on what comes back:

- **A live hold at the full claim fee** is *promoted* — routed through the same
  webhook handler the missing webhook would have triggered — rather than
  cancelled. The claim completes the transition it was owed.
- **A claim whose state cannot be read** is left alone. A Stripe failure raises,
  and the sweep skips that claim. A claim that cannot be verified must not be
  cancelled, or a live hold is orphaned.
- **A claim with no intent id, or an id that cannot be one Stripe issued,**
  proceeds to cancel with no provider call.

The result type gained a `promoted` counter alongside `cancelled` and `errored`,
so the promotion path is observable rather than silent.

## Two details that carry the engineering

**The synthetic-id check is shared, not re-implemented.** The sweeper decides
"could a hold exist behind this id?" by calling the same helper the cancel path
uses. Its docstring says why in one line: *that reuses the same convention
`cancel_payment_intent` applies, so the two paths cannot disagree about which
ids are real.* Two independent implementations of "is this a real Stripe id"
will eventually disagree, and the disagreement lands on someone's card.

**Unreadable is not the same as absent.** The natural error handling — catch the
Stripe exception, log it, carry on cancelling — is exactly wrong here. Failing
to reach the provider tells you nothing about whether a hold exists, so the only
safe action is to do nothing and retry on the next sweep. The sweep runs every
ten minutes; a claim left alone costs one cycle, and a claim wrongly cancelled
costs a charge and an item.

## Test

The fix shipped with 104 lines of new tests in the same commit. They cover:
a pending claim past the window is cancelled and relisted; one inside the window
is untouched; an authorized claim is never touched however old; a listing that
has already moved on is left alone; and — the case this commit exists for — a
**live hold is promoted, not cancelled**.

## Limitation, stated

The double-capture guards elsewhere in the money path are read-then-write in
Python, not row locks, and no test proves behaviour under simultaneous
double-capture. See [`../LIMITATIONS.md`](../LIMITATIONS.md). "Money can never be
taken twice or lost" is not a claim this repository makes.

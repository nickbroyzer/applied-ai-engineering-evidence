# A redirect loop, and the invariant that ended it

**Commit:** `f17a378d1656bdc3ddd27bb43af82ae5d0d2841e` · 2026-06-30
**Message, verbatim:** `Fix auth-redirect loop: single onboarding read + fixpoint guard stops / onboarding / home churn that reset the OTP screen`
**Later related:** `7b533109c57751a87c0476946e2cda95e87ad3ca` — `auth: a suspended session is sent to the disabled screen and held there`

## Symptom

Entering a one-time code, the OTP screen would reset itself. The user's typed
code vanished and the screen re-rendered from scratch.

## Diagnosis

The root layout computed a redirect target from auth and onboarding state on
every render. Three routes were involved — the root, onboarding, and home — and
under some state combinations the target computed at one route sent the user to
a second route, whose own computation sent them back. The navigation churned,
and every re-entry remounted the OTP screen, discarding its local state.

Two separate defects fed it:

1. **The onboarding state was read more than once** during a single redirect
   decision. Two reads at different moments could disagree, so the decision was
   made on inconsistent inputs.
2. **Nothing guaranteed the redirect terminated.** The target function was
   correct for each individual case and had no property tying the cases
   together.

## Fix

**One read.** The onboarding state is read once and that value drives the whole
decision, so the inputs cannot disagree with themselves mid-decision.

**A fixpoint guard.** The redirect function must satisfy:

```
target(target(x)) === null
```

In words: wherever the router sends you, the destination must be somewhere it
would not send you onward from. One hop, then stop. This converts "no loop"
from a property you hope holds across every pair of routes into a single
condition checkable on the function itself.

That is the transferable part. A redirect loop is not usually fixed by finding
"the bad case" — the cases are individually reasonable, and the loop lives in
their *composition*. Stating the invariant and checking it case by case is a
finite job; chasing pairs is not.

## Verification

The property was walked case by case after a later change removed the onboarding
branch entirely: unauthenticated on a protected route returns the root, and the
root returns null. Both hops terminate.

The same layout later gained the suspended-session case (`7b53310`): a suspended
session is sent to the disabled screen **and held there** — the "held there"
half is the fixpoint condition applied to a new state, not an afterthought.

The project record also corrects itself here, which is worth showing rather than
tidying away: an entry summarising this arc described an anonymous-browse path
as reachable through a screen sequence that, on re-reading the code, did not
exist as written. The underlying defect was real and closed; the narrative
around it was wrong and is marked so in the source document.

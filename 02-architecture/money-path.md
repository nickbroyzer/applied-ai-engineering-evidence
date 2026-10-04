# The money path

Code: [`../code/payments/`](../code/payments/). Tests: 118 `def test_` functions
(122 collected) across nine payment files — the six published in September (92)
plus the deferred-intent, claim-fee and curbside-sweeper tests — itemised in
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md).
All passed in the recorded run at Zelbi `8875721`.

## The lifecycle

**Authorize** at claim — a manual-capture hold, not a charge. **Capture or void**
at pickup, by outcome and timing. **Refund** on an upheld dispute. A **scheduled
sweep** reconciles anything the webhooks did not.

**The client surface.** Checkout is a first-party screen ([`D305`](../03-decisions/money/D305.md)),
with the Stripe React Native SDK's payment sheet behind it. The sheet is
initialised with an Apple Pay merchant identifier and a US merchant country, so
Apple Pay is an offered payment method inside our own screen rather than a
wallet takeover of it. The wallet configuration is client-side and is not
exercised by the backend suite.

The reason it is a hold and not a charge is in
[`../01-product-logic/marketplace-state-machine.md`](../01-product-logic/marketplace-state-machine.md):
at the moment of claiming, the event that decides whether money should move has
not happened yet.

## Fifteen failure states, and the answer to each

The reason this section exists is that a money path is defined by its failure
states, not its happy path. Each row below is a state the code handles, with the
principle behind the handling.

| Failure | Response | Principle |
|---|---|---|
| 1. Webhook never delivered | Sweeper reads the intent's true state and **promotes** the live hold | The provider is the authority, not our row |
| 2. Provider unreachable during a sweep | Claim **left alone**, retried next cycle | Unreadable ≠ absent |
| 3. Intent already captured | **Adopt** it and log the divergence | Never re-capture |
| 4. Capture underfunded | Dedicated error, not a generic failure | Different causes need different responses |
| 5. Provider raises mid-transaction | Local state **rolls back** | Never diverge from the provider silently |
| 6. Hold lapses before pickup | Cancel and void. **Never capture** | Void costs nothing; a wrong capture invites a dispute fee exceeding the margin on ~9 claims |
| 7. Void succeeds, status write fails | Void **first**, write cancelled only after the void returns | A row marked cancelled with a live hold is the leak |
| 8. Duplicate webhook delivery | Idempotency keys + a database uniqueness constraint | The constraint is what makes it true, not the key |
| 9. Forged webhook | Signature verification before any handling | — |
| 10. Claim reopened twice | Reopen is idempotent | — |
| 11. Nobody confirms the pickup | Auto-capture on a timer, with consent recorded in advance at the tap | Client-reported arrival means someone must decide |
| 12. Picker disputes and wins | Refund through the provider **before** the ruling is written | A failed refund must not leave a ruling standing |
| 13. Picker blocks the giver mid-claim | Claim cancelled through the shared cancel service; **no fee, no strike** | A safety action must never cost money |
| 14. Account deleted mid-claim | Claims cancelled and open holds voided as part of deletion | Deletion must not orphan a hold |
| 15. Bank-debit payment method attempted | Structurally impossible: that method type cannot do manual capture at all | Found by reading the provider's constraints, not by shipping and discovering |

## Three details that carry the argument

**The synthetic-id convention is shared.** Deciding "could a hold exist behind
this id?" runs through one helper, used by both the sweeper and the cancel path.
Its docstring states the reason: *the two paths cannot disagree about which ids
are real.* Two independent implementations of that question will eventually
disagree, and the disagreement lands on a card.

**Order is load-bearing, repeatedly.** Void before writing cancelled (row 7).
Refund before writing the ruling (row 12). In both, the irreversible external
action goes first, so a failure leaves the system in the *safe* inconsistent
state rather than the dangerous one.

**Consent is stamped at the tap.** The checkout screen creates its claim on
mount, so a consent timestamp written at claim creation records a consent not yet
given. The wording *version* is recorded at creation (which text was shown); the
*acceptance* is written by a separate idempotent endpoint called at the
place-hold tap, and payment is blocked if that call fails. Device-proven: a
13.1-second gap between claim creation and consent, against 0.09 seconds under
the old behaviour ([`D319`](../03-decisions/money/D319.md),
[`D317`](../03-decisions/money/D317.md)).

## Vocabulary, ruled

"Authorization" for the hold. "Released" for an uncaptured hold. "Refund" **only**
for money returned after a capture ([`D431`, `D315`](../03-decisions/money/)).
The hub's system replies describe money as authorized and released, never taken
and refunded, matching the checkout disclosure. Getting this wrong is not a
copy nit — telling someone they were "refunded" when their hold was released
tells them money moved that never did.

## The stated limitation

Double-capture guards are **read-then-write in Python**. There are zero row locks
in the backend, and no test exercises simultaneous double-capture. What is
claimed: *built and tested safeguards for duplicate capture, rollback, and
provider reconciliation.* What is not claimed, and would be false: that money can
never be taken twice or lost.

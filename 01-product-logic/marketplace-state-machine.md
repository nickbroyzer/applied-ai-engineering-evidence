# The claim lifecycle

Zelbi is a giveaway marketplace. Items are free; the picker pays a small
**claim fee** to claim one. That fee is the whole reason a state machine exists:
a free item with no commitment attached is claimed and abandoned, and the giver
waits at the door for someone who was never coming.

So the fee is not revenue. It is a commitment device — and it is taken as a
**card authorization hold**, not a charge, because the outcome that decides
whether money should move has not happened yet at the moment of claiming.

## The states

Claim status is a database check constraint, not a convention
(`ck_claims_status`, [`../code/database/`](../code/database/)):

```
pending_payment · authorized · pickup_scheduled · completed
no_show · cancelled · auto_captured
```

Listing status is likewise constrained (`ck_listings_status`):

```
active · claimed · completed · expired · removed · hidden_pending_review
```

## The path

```
                        ┌──────────────────┐
  picker taps claim ───►│ pending_payment  │  no hold yet; listing still active
                        └────────┬─────────┘
                                 │ Stripe confirms the hold
                                 │ (amount_capturable_updated webhook)
                                 ▼
                        ┌──────────────────┐
                        │   authorized     │  hold live · exact address released
                        └────────┬─────────┘  · listing now claimed
                                 │ giver and picker agree a time
                                 ▼
                        ┌──────────────────┐
                        │ pickup_scheduled │  time bounded by the hold's own life
                        └────────┬─────────┘
              ┌──────────────────┼───────────────────┬─────────────────┐
              ▼                  ▼                   ▼                 ▼
      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
      │  completed   │   │ auto_captured│   │   no_show    │   │  cancelled   │
      │ hold captured│   │ nobody       │   │ picker did   │   │ hold voided  │
      │              │   │ confirmed;   │   │ not arrive;  │   │ no money     │
      │              │   │ captured on  │   │ fee forfeit  │   │ moves        │
      │              │   │ the timer    │   │              │   │              │
      └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                 │
                                 │ picker disputes, and wins
                                 ▼
                          refund, issued through the provider
                          before the ruling is written  (D324)
```

## Why each transition is where it is

**`pending_payment` exists at all** because the claim row is created when the
checkout screen opens, before any hold. Nothing has been paid yet, and the
listing deliberately stays `active` — what blocks a second picker is a partial
unique index on claims, so cancelling the claim is what frees the item. A claim
stuck here past a short timeout is swept; the sweeper's near-miss is
[the fourth troubleshooting write-up](../04-troubleshooting/04-false-charge-message.md),
and it is the most important thing in this repository.

**Exact coordinates cross at `authorized`, not before** ([`D320`](../03-decisions/privacy/D320.md)).
A `pending_payment` claim — created on checkout mount, before any hold —
discloses nothing. The address is what the fee buys, so it moves when the money
is committed.

**The pickup time is bounded by the hold's own lifetime**
([`D218`](../03-decisions/money/D218.md)). A card authorization does not live
forever. The booking ceiling is *derived* from that lifetime minus the
auto-capture wait minus a sweep-margin cushion — not a round number of days
picked because it looked reasonable. That derivation is why no backstop sweep is
needed: a capture can never land after its hold has died, because a time past
that point is not offerable.

**Expiry resolves as cancel, never capture** ([`D217`](../03-decisions/money/D217.md)).
If a hold lapses without a completed pickup, the claim is cancelled and the hold
voided. Voiding costs nothing; capturing without a pickup invites a dispute
whose fee exceeds the margin on roughly nine completed claims. The order is
load-bearing: **void at the provider first, write the cancelled status only
after the void returns.** A row marked cancelled with a live hold attached is
precisely the leak the rule exists to close.

**`auto_captured` exists because arrival confirmation is client-reported.**
Nobody may be watching when the pickup happens. Capture is on a timer after the
scheduled time, and the picker consents to that in advance
([`D317`](../03-decisions/money/D317.md), [`D319`](../03-decisions/money/D319.md))
— consent recorded *at the tap*, with its wording version and timestamp, not at
screen mount. The gap between those two is 13.1 seconds against 0.09 on the
verification walk; a consent stamped at mount records a consent not yet given.

**Blocking never costs the picker money** ([`D318`](../03-decisions/trust/D318.md)).
A safety action must never carry a financial penalty, whatever the timing —
otherwise the fee becomes a reason not to block someone you should block.

## What this machine does not guarantee

Double-capture guards are read-then-write in Python. There are no row locks and
no test proving behaviour under simultaneous double-capture. The claim this
repository makes is *built and tested safeguards for duplicate capture,
rollback, and provider reconciliation* — not that money can never be taken
twice. See [`../LIMITATIONS.md`](../LIMITATIONS.md).

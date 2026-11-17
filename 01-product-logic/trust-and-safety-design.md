# Trust and safety — the shape of the model

The *shape* of the model is the design, and the shape is here. The tuned
numbers — deduction weights, heal threshold, score bounds, strike thresholds and
window lengths — are published in the code excerpts
([`../code/trust/`](../code/trust/)); they were withheld in September, but the
published tests and the user-facing notice copy already stated them, so
withholding them protected nothing ([`../MANIFEST.md`](../MANIFEST.md) §1.2).
The scam-detection pattern table in
[`../code/message_guard/`](../code/message_guard/) is still withheld: there,
publishing the patterns would publish the evasion recipe. Line numbers below
are at Zelbi `8875721`.

## Reputation: earned per handoff, not granted on arrival

The model was rebuilt once, and the reason is the interesting part
([`D182`](../03-decisions/trust/D182.md) → [`D299`](../03-decisions/trust/D299.md)).

The first model started a new account at the floor, jumped it to the **ceiling**
on the first completed transaction, and only deducted thereafter. So the first
handoff handed out a perfect score and the ring never moved again. A perfect
score that everyone reaches immediately carries no information.

The rebuild made every completed transaction worth a flat award, so a full ring
takes many handoffs and is **meant to be rare**. Deductions were re-weighted by a
constant factor to keep the same proportions between offence types.

Four properties survived deliberately:

- **Ordering, not magnitude, is the design.** `late_cancel` < `no_show` <
  `dispute_lost`, with the two dispute roles weighted equally — a giver who
  loses a dispute is penalised exactly as a picker is.
- **The first infraction is free**, and after the rebuild the grace applies to
  the oldest *unhealed* infraction rather than the oldest ever, so grace resets
  after healing. One bad day should not be permanent.
- **Infractions heal, points do not return.** After enough clean completions an
  infraction stops counting and returns to the free pool — but healing never
  awards points. Points come only from handoffs, which is what *earned* means.
- **The scale is signed, with no floor at zero.** An account that has done more
  harm than good must be visibly distinct from one that has done nothing yet.
  A floor at zero collapses "new" and "damaged" into the same number.

**Every score carries a word**, computed from the history behind the number
rather than the number alone — because a low score alone cannot distinguish a
new account from a damaged one. Trust reads *Poor* below zero, *New* at no
completions, *Mixed* whenever any infraction exists, then ascending by
completion count.

The scoring function is pure — no session, no write-back, no I/O — which is what
lets the same rules run against a *hypothetical* event set. The score-delta
endpoint replays a user's history with one ending's events removed and takes the
difference, so a user can be shown what an outcome would cost before it happens.

## Strikes: a punctuated rule, not an escalating ladder

The original design was an escalating suspension ladder. It was replaced
([`D21`](../03-decisions/trust/D21.md)) once the claim fee existed: forfeiting
the fee is already sufficient deterrent for one-off flaking, so the ladder was
solving a problem the fee had taken over.

What remains is single-tier: a strike count inside a rolling window produces a
fixed-duration timeout, the counter resets after the timeout is served, and
there is **no escalation between cycles**. In-flight claims at timeout start are
cancelled, their listings released, and their holds voided — a timeout that left
live holds attached would be the leak
[`D217`](../03-decisions/money/D217.md) exists to close.

Only giver-marked no-shows count. Picker-initiated cancellations do not, because
a rule that punishes cancelling punishes the honest signal.

## Blocking: symmetric, and free

Blocking is enforced in **both directions** from a single pair of helpers — a
boolean check and a reusable SQL predicate — across listings, messages and
claims. Fourteen call sites invoke them: three in the listings router, seven in
claims, two in messages, two in the post-window sweeper (the command and its
output are in
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md)).

Sharing the predicate is the point. Two hand-written block checks eventually
disagree, and the disagreement is a leak. **The feed does not yet follow its own
rule:** the nearby and map feed queries carry the block filter as an inlined
SQL subquery, written out four times (`routers/listings.py:69, 109, 164, 201`),
and the shared `NEARBY_BLOCK_FILTER_SQL` constant is imported there but unused.
The four copies agree today; that is exactly the situation the shared predicate
exists to prevent.

Blocking someone mid-claim cancels the live claim through the shared cancel
service and records it as a flag for the operator console.

Two rulings make blocking usable rather than merely available:

- It **never costs the picker money and never files a strike**, whatever the
  timing ([`D318`](../03-decisions/trust/D318.md)).
- A blocked party **still gets their receipt**, minus the address
  ([`D322`](../03-decisions/privacy/D322.md)).

## The message guard: a normalizer, not a classifier

Launch-scope content detection is regex and keyword only — **explicitly no
per-message model** ([`D226`](../03-decisions/trust/D226.md)) — because this runs
at a send-time choke point where latency and cost are bounded.

Three rules are active: the listing-tempo guard (rule 2), the message guard on
send and edit (rule 3, seven checks, blocking with a 400), and pricing words on a
free listing (rule 6). Rule 1 was retired, rule 4 is marked not active (its only
caller was never called and was deleted as dead code), and rule 5, duplicate
photos, is a stub — `RULE_DEFINITIONS` in `scam_detection.py` states each
status, and the operator console reads it from there.

The engineering is not in the patterns; it is in what runs **before** them.
A normalizer decodes evasion first, so every rule matches against the decoded
form and a rule added later cannot forget to call it. It:

- collapses spaced-out letters (`t e x t   m e` → `text me`)
- collapses repeated-character runs
- maps look-alike digits and symbols back to letters — but **only when the
  character sits between two real letters**, so `v3nmo` becomes `venmo` while
  `3pm`, `742` and `$20` are left untouched
- maps meaning-carrying emoji to words
- squashes separators for brand names that defeat the spacing pass

That look-alike rule is the whole craft of the thing: the naive version
(substitute every `3` for `e`) destroys phone numbers and prices, which are
exactly the content the guard is trying to reason about.

**Normalization is match-time only.** It is never applied to what is stored or
shown to the user. The user's words are the user's words.

The refusal carries a **category taxonomy** — phone, payment, contact,
scheduling — so the client can respond specifically
([`D232`](../03-decisions/trust/D232.md)), and copy is written per category in a
safety voice rather than one generic block message
([`D228`](../03-decisions/trust/)).

Two rules govern enforcement rather than detection:

- The scheduling block **redirects into the real pickup flow**
  ([`D227`](../03-decisions/trust/)). A block with nowhere to go gets routed around.
- The guard extends the existing engine at the existing choke point rather than
  adding a parallel module ([`D225`](../03-decisions/trust/D225.md)) — a lesson
  the backend lessons file records independently.

## Rules that were deleted

[`D264`](../03-decisions/trust/D264.md) and [`D270`](../03-decisions/trust/D270.md)
retire two shipped detection rules. The new-account rule fired on any account
under a day old publishing a listing; the GPS-spam rule flagged givers by
location. Both were **deleted, not disabled** — and the one still needed was
replaced by something narrower, a location-free listing tempo guard.

Deleting is the harder call. A disabled rule looks like coverage in an audit and
is nobody's job to remove.

## Credits that cannot be farmed

The free-pickup credits added in September are a trust feature too: a giveaway
or invite credit cannot be spent until the iPhone that earned it passes Apple
DeviceCheck. See [`device-check-credits.md`](device-check-credits.md).

## Stated limitations

- **Arrival confirmation is client-reported** ([`D444`](../03-decisions/ops/D444.md)).
  The endpoint accepts no coordinates. "Server-verified geofence" would be false.
- **Message-guard enforcement is partial.** Detection is built; not every
  enforcement action is wired.
- **Duplicate-photo detection is a stub.**
- **No test proves a non-admin receives 403 on the dispute-resolve route**
  specifically; the dispute list and message routes have one
  (`test_admin_disputes.py:244, 372`).
- **A separate trust-word raw counter has no writer and does not heal** — dead
  code, filed for deletion.
- Prohibited-item handling: withheld from the public repository; available on
  request.

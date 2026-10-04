# What the platform does when things go wrong

A marketplace is mostly failure states. The happy path — item posted, item
claimed, item collected — is the smallest part of the design. Everything below
is a state someone actually reaches, with the ruling that governs it and where
the code lives.

| # | Failure | What happens | Where |
|---|---|---|---|
| 1 | **Picker never shows up** | The giver marks a no-show. The held fee is forfeited — that is the deterrent the fee exists to be. A strike is recorded against the picker; at a threshold, a rolling-window timeout blocks new claims and cancels in-flight ones (thresholds withheld). | [`D21`](../03-decisions/trust/D21.md), [`code/trust/strike_service.py`](../code/trust/strike_service.py) |
| 2 | **Giver never shows up** | Symmetric handling was deliberately deferred, not forgotten: no event currently records a giver no-show, so there is nothing to score against. The gap is filed rather than papered over. | [`D207`](../03-decisions/money/D207.md), [`D183`](../03-decisions/trust/D183.md) |
| 3 | **Item is not as described** | The picker raises a dispute with support by email; there is no in-app filing route ([`D533`](../03-decisions/money/D533.md)). Disputes are picker-only — the giver paid nothing, so they have nothing to dispute. | [`D208`, `D210`](../03-decisions/money/), [`D533`](../03-decisions/money/D533.md) |
| 4 | **Dispute is upheld** | The captured fee is refunded **through the provider, as part of the resolve action** — never by operator hand-work in a dashboard. The refund is issued *before* the ruling is written, so a refund failure cannot leave a ruling standing with no money returned. | [`D324`](../03-decisions/money/D324.md) |
| 5 | **Authorization webhook is lost** | The picker paid and a live hold exists, but the platform never recorded it. The sweeper reads the intent's true state from the provider and **promotes** the live hold instead of cancelling the claim. | [`04-troubleshooting/04`](../04-troubleshooting/04-false-charge-message.md) |
| 6 | **Provider cannot be reached during a sweep** | The claim is **left alone**, not cancelled. Unreadable is not the same as absent; a claim whose state cannot be verified must not be written off, or a live hold is orphaned. Next sweep, ten minutes later, tries again. | [`code/payments/pending_payment_sweeper.py`](../code/payments/pending_payment_sweeper.py) |
| 7 | **Provider raises mid-transaction** | Local state rolls back rather than diverging from the provider's record. | [`code/payments/stripe_service.py`](../code/payments/stripe_service.py) |
| 8 | **The intent was already captured** | The already-captured intent is **adopted** and the divergence logged, rather than re-captured. Re-capturing is the failure mode that charges someone twice. | [`code/payments/stripe_service.py`](../code/payments/stripe_service.py) |
| 9 | **Capture is underfunded** | A dedicated error is emitted rather than a generic failure, because the two need different responses. An investigated instance of the "underfunded loop" was ruled **not a defect** rather than patched. | [`D261`](../03-decisions/money/D261.md) |
| 10 | **Hold lapses before pickup** | Cancel and relist. Never capture. | [`D217`](../03-decisions/money/D217.md) |
| 11 | **Both parties block each other** | Enforced symmetrically at every call site across listings, messages and claims. A block cancels the in-flight claim through the shared cancel service — and **costs the picker nothing** and files no strike, whatever the timing. | [`D318`](../03-decisions/trust/D318.md), [`code/trust/block_service.py`](../code/trust/block_service.py) |
| 12 | **A blocked party needs their receipt** | The receipt endpoint stays unfiltered by blocks — *a receipt is a record*. But the picker's copy strips both coordinate fields. The giver keeps them; it is their address. The map is silently absent for the blocked viewer: no placeholder, no explanation. | [`D322`](../03-decisions/privacy/D322.md) |
| 13 | **Listing is removed mid-claim** | The listing status set includes `removed` and `hidden_pending_review` as distinct terminal states; an in-flight claim goes through the shared cancel path, which voids the hold. | [`code/payments/claim_cancel_service.py`](../code/payments/claim_cancel_service.py) |
| 14 | **Listing expires** | A ten-minute cron sweep, not a daily one. A scheduled job querying a bounded window must run at least as often as that window is wide, or it silently matches nothing and reports success — a lesson learned the hard way on the pickup reminder. | [`D238`](../03-decisions/ops/D238.md), [`04-troubleshooting/lessons-backend.md`](../04-troubleshooting/lessons-backend.md) |
| 15 | **User deletes their account** | Real in-app soft delete: the account is marked deleted, the session ends immediately, re-login is blocked, and the public identity is anonymised. **Active claims are cancelled and open holds voided as part of deletion.** Records needed for integrity — completed pickups, disputes, block and report history — are retained de-identified and never shown publicly. Hard delete was considered and rejected: it breaks claim, dispute and payment record links. | [`D215`](../03-decisions/privacy/D215.md) |
| 16 | **A deleted user signs up again** | Deletion retains a one-way, unkeyed SHA-256 email fingerprint. Called a *fingerprint*, never a "salted hash" — because it is not salted, and describing it as one would overstate it. | [`code/database/`](../code/database/) |
| 17 | **A message tries to move the deal off-platform** | The guard fires on send *and on edit*, at a single choke point, with a category taxonomy on the refusal so the client can respond specifically. Detection is regex and heuristic — **no per-message model** — to keep latency and cost bounded at a send-time choke point. | [`D225`, `D226`, `D232`](../03-decisions/trust/), [`code/message_guard/`](../code/message_guard/) |
| 18 | **A scheduling message tries to bypass the pickup flow** | Hard-blocked, and the user is redirected **into the real pickup-setup flow** — an actual route, not a warning. A block that leaves the user with nowhere to go gets routed around. | [`D227`](../03-decisions/trust/) |
| 19 | **A listing looks like spam at post time** | It is still posted. No listing is ever hidden at post time; the check informs review, it does not gate publication. | [`D272`](../03-decisions/trust/D272.md) |
| 20 | **A detection rule turns out to be wrong** | It is **deleted, not disabled**. The new-account rule and the GPS-spam rule were both removed outright and, where still needed, replaced by something narrower — a location-free tempo guard. | [`D264`](../03-decisions/trust/D264.md), [`D270`](../03-decisions/trust/D270.md) |
| 21 | **A cron job crashes in production** | Historically: nothing paged, and it was found sixteen hours later by accident. That gap is why explicit capture calls now sit inside each `except` block — a runner that catches everything gives the error reporter nothing to notice. | [`04-troubleshooting/01`](../04-troubleshooting/01-prepared-statements-vs-pooler.md), [`D274`](../03-decisions/ops/D274.md) |
| 22 | **A user hits a rate limit** | Treated as an **admin signal, not a user-facing bug**: the ceilings stay. This was ruled after a 30-per-hour ceiling sized for claim creation, mounted at router level, locked a real user out of reading their own receipts — the ceiling then moved to writes only, reads unmetered. | [`D442`](../03-decisions/ops/D442.md), [`D275`](../03-decisions/ops/D275.md) |

## Three patterns worth naming

**Fail closed, then retry.** Rows 5, 6 and 7: when the platform cannot establish
the truth, it does nothing and tries again, rather than acting on an assumption.
The sweep runs every ten minutes, so doing nothing costs one cycle.

**A block must leave somewhere to go.** Rows 18 and 20: an enforcement action
that dead-ends the user gets routed around by the user. The scheduling block
redirects into the real flow; a rule that fired wrongly is deleted rather than
left disabled to rot.

**Safety actions must be free.** Rows 11 and 12: blocking someone costs the
picker no money and files no strike, and a blocked user still gets their
receipt. The moment a safety control has a price, people stop using it.

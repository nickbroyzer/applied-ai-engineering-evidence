# Case studies — index

Nine short write-ups of problems found and fixed in Zelbi, each with its
commits, tests and decisions. One line per study: its title, then its
"In short" text, verbatim.

01. [The reminder that had never fired](01-reminder-that-never-fired.md) — four production notifications had never sent once. The job ran every ten minutes and reported success, and the test for it was green. The test passed only because it built a claim the app can never create.

02. [Consent recorded before anyone agreed](02-consent-before-the-tap.md) — the app stored the moment a person agreed to the $2 hold. That moment was being written when the checkout screen opened, before they had read anything. The fix moved the record to the tap. A device walk measured the gap the fix exposed: 13.1 seconds, against 0.09 seconds before.

03. [An old notification opened a stranger's pickup](03-an-old-notification-opened-a-strangers-pickup.md) — after a cancel, a relist and a re-claim, tapping an old notification could open someone else's handoff, with their pickup details. One screen loaded "the newest claim on this item" when it should have loaded "the claim this notification is about".

04. [One error code with two opposite meanings](04-one-error-code-with-two-opposite-meanings.md) — when the payment sweeper cancelled an expired hold and Stripe answered "no such payment", the claim was written off. That's right when the id was never real. It's dangerous when the id is real but the server is talking to a different Stripe account, because a live hold on someone's card would be abandoned while our records say it's gone.

05. [Rejected by Apple, then proving the feature needed the permission](05-rejected-by-apple-then-proving-the-feature-needed-the-permission.md) — Apple rejected the app under Guideline 2.5.4 for asking for background location. The first fix kept the feature without the permission, and real walk data showed it couldn't fire at the door. The final answer was a narrowly scoped use of the permission plus a recording that proved it. Apple approved build 20 by 2026-11-03, and it was released on 2026-11-04.

06. [Live Activities: a 200 that means nothing](06-live-activities-a-200-that-means-nothing.md) — Apple answers 200 to an update for a lock-screen card the phone no longer shows. The server trusted its own records and its 200s, so it held back an arrival banner for a card that wasn't there. The fix was to make the phone report what it really has, then to send the card or a banner for each moment, never both and never neither.

07. [Help search: fix the content first, then add vectors](07-help-search-fix-the-content-first-then-add-vectors.md) — a 24-question test of the in-app help found 6 refusals and 4 answers from the wrong article. Rewriting the articles came first and got refusals down to 2. Adding meaning-based search got them to 0, with the right article first on all 24. It went live only together with cost and abuse limits.

08. [The support agent: 4 of 10, then 9 of 10, then 4 of 4](08-the-support-agent-4-of-10-then-9-of-10-then-4-of-4.md) — a Claude agent reviews trust-and-safety reports and proposes a decision for a person to approve. Its first scored round got 4 of 10 right, by handing hard cases back. Its reasons were saved, before any fix, in its own words. After the fixes it scored 9 of 10, then 4 of 4 on a new kind of case.

09. [A security pass before submitting to Apple](09-a-security-pass-before-submitting-to-apple.md) — a security audit of the server before App Store submission found a set of issues, all fixed in one batch (D588). This page lists the categories, not the attack details.

# Consent recorded before anyone agreed

**In short:** the app stored the moment a person agreed to the $2 hold. That moment was being written when the checkout screen opened, before they had read anything. The fix moved the record to the tap. A device walk measured the gap the fix exposed: 13.1 seconds, against 0.09 seconds before.

## Why it matters
Zelbi places a $2 hold on the picker's card, and the hold is captured automatically if the pickup isn't confirmed. Consent to that automatic capture is a legal and dispute-handling record. A claim stores which wording was shown (`disclosure_version`) and when the person accepted it (`disclosure_accepted_at`). If the timestamp is wrong, the record proves nothing.

## What broke
The checkout screen creates the claim as soon as it opens, so the price and the disclosure can load from the server. The consent timestamp was written in the same request that created the claim. So every claim carried a "consented at" time from before the person had seen the disclosure, let alone tapped the button.

## The fix
The two facts were split, because they happen at different moments:
- **At claim creation**, the server records only which wording was shown. A claim can't be created with an unknown version.
- **At the tap**, the server stamps the acceptance time. Only the picker on that claim can do it, and only while the claim is still waiting for payment (otherwise it answers 409). If the call fails, the payment doesn't go ahead.

**Proof on a real phone:** on the verification walk, 13.1 seconds passed between claim creation and consent. Under the old code the gap was 0.09 seconds, which was just the time between two writes in one request.

## The detail that makes it a good story
The fix broke two existing tests. They hadn't missed the bug: they had been written to **assert** the open-screen timestamp as correct. They were rewritten to assert the tap-time stamp, and the tests now say plainly what must never happen:

```text
test_create_claim_stamps_version_but_never_the_timestamp
test_create_claim_422_when_disclosure_version_missing
test_create_claim_400_when_disclosure_version_unknown
test_reuse_path_does_not_overwrite_original_consent_stamp
```

## Where it ended up
About six weeks later, checkout moved to Stripe's deferred intent: nothing is held until the pay tap. Consent moved with it, into the same request that creates the hold:

```python
claim.disclosure_version = body.disclosure_version
claim.disclosure_accepted_at = datetime.now(timezone.utc)
```

Consent and the hold now come from one tap and one request, so they can't drift apart again. That request still refuses an unknown wording version (400), anyone other than the picker (403), a claim that isn't awaiting payment (409), and a card that belongs to another customer (403). If the price changes after a refused tap, the stored version is the one actually agreed to.

## What I'd do differently
A test that asserts current behaviour isn't a test that the behaviour is right. For anything legal or financial, write the test from the rule ("consent is the tap"), not from what the code does today.

Sources: decisions D317, D319 and D549. Commits `f38dd81d` (record consent), `c1a2fc55` (stamp at the tap) and `7dd9faf6` (tests assert the tap-time stamp). `backend/tests/test_claim_consent.py`; `backend/app/routers/claims.py`, `create_claim_payment_intent`.

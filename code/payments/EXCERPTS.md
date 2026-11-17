# `code/payments/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## A real PaymentIntent id, by shape (case study 04)

`backend/app/services/stripe_service.py`, lines 58–68, at `4772472b`. Cited by: 06-case-studies/04; 01-product-logic/failure-state-matrix.md.

```python


# A PaymentIntent id Stripe actually issued is "pi_" followed by 24 or more
# alphanumeric characters. Seeded and reproduction rows carry hand-written
# references that cannot match this, and those never had a hold behind them.
_REAL_PI_RE = re.compile(r"^pi_[A-Za-z0-9]{24,}$")


def is_synthetic_payment_intent_id(pid: str | None) -> bool:
    """True when `pid` cannot be an id Stripe issued, so no hold can exist behind it."""
    return not bool(pid) or _REAL_PI_RE.match(pid) is None
```

## A real id Stripe cannot find is left untouched (case study 04)

`backend/app/jobs/post_window_sweeper.py`, lines 296–322, at `4772472b`. Cited by: 06-case-studies/04.

```python
def _run_auto_cancels(db: Session, now: datetime) -> int:
    """Void + cancel claims that never completed pickup coordination after 6d (D105), and
    curbside proposals the picker never confirmed by the set-out time (D524)."""
    auto_cancelled = 0
    for claim in _eligible_for_auto_cancel(db, now) + _eligible_for_curbside_auto_cancel(db, now):
        listing = db.get(Listing, claim.listing_id)
        try:
            cancel_payment_intent(claim.id, "auto_cancel_no_pickup", db)
        except StripeServiceError as exc:
            db.rollback()
            # A real id Stripe cannot find means the hold may still be live on a
            # different account. The claim is NOT written off — it is left exactly as
            # it is and raised at error level under its own event name so it can be
            # alarmed on and resolved by a human. Every other Stripe failure keeps the
            # prior behaviour: log and move to the next claim.
            if getattr(exc, "code", None) == "resource_missing":
                logger.error(
                    json.dumps(
                        {
                            "event": "auto_cancel_orphaned_hold_suspected",
                            "claim_id": str(claim.id),
                            "payment_intent_id": claim.stripe_payment_intent_id,
                            "action": "left untouched for manual review",
                        }
                    )
                )
                continue
```

## The imminent-reminder query (case study 01)

`backend/app/jobs/post_window_sweeper.py`, lines 142–163, at `4772472b`. Cited by: 06-case-studies/01.

```python
def _eligible_for_imminent_reminder(db: Session, now: datetime) -> list[Claim]:
    """Claims whose PICKUP is roughly a day away.

    Separate from the deadline nudges below, which select on how old the claim is. These
    reminders say "your pickup is coming up at 3pm", so they must be chosen by when the
    pickup is, not by when the claim was made. They shared the deadline query until
    2026-08-29, which also required status "authorized" — and every route that sets a
    pickup time writes "pickup_scheduled" in the same statement, so no claim could ever
    satisfy both and none of these four types had ever fired.
    """
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

## Already captured: adopt, never re-capture

`backend/app/services/stripe_service.py`, lines 665–700, at `4772472b`. Cited by: 01-product-logic/failure-state-matrix.md (row 8).

```python
        # a3 RECONCILIATION — Stripe already holds this claim's money while the claim
        # row does not record it: a capture whose local write was lost after the money
        # moved. Adopt Stripe's record rather than re-capturing. Without this branch the
        # next run reads zero capturable and reports an auto-void that never happened,
        # every run, forever. Sits ahead of the underfunded branch deliberately.
        pi_status = getattr(current, "status", None)
        amount_received = getattr(current, "amount_received", None)
        if (
            pi_status == "succeeded"
            and amount_received is not None
            and int(amount_received) >= CLAIM_AMOUNT_CENTS
        ):
            now = datetime.now(timezone.utc)
            _apply_capture_outcome(claim, reason, now)
            db.add(claim)
            db.flush()
            logger.error(
                json.dumps(
                    {
                        "event": "stripe_capture_divergence_already_captured",
                        "claim_id": str(claim_id),
                        "payment_intent_id": pid,
                        "amount_received": int(amount_received),
                        "reason": reason,
                        "note": "captured_at set to reconciliation time, not the original capture time",
                    }
                )
            )
            return current

        # D539 (1) LOST-WRITE ADOPT — the mirror of a3 for a credit release: the intent
        # is canceled AND carries our release mark for this claim, so Zelbi released the
        # hold for a covered completion but the local write was lost. Adopt the release.
        # Reachable from EVERY caller, the sweeper included: without it the sweeper would
        # read zero capturable on a still-live claim and report an auto-void every run,
        # forever. A canceled intent WITHOUT the mark is Stripe's own cancel and falls
```

## Consent stamped at the pay tap: contract (case study 02)

`backend/app/routers/claims.py`, lines 1402–1414, at `4772472b`. Cited by: 06-case-studies/02.

```python
    """D549 (survey A2): the pay tap. The PaymentSheet's confirmHandler sends the chosen
    PaymentMethod here; this creates the $2 manual-capture intent for it and returns the
    client secret the SDK then confirms, which is when the hold is placed. Nothing is
    held before this call.

    Consent is stamped here, with the disclosure variant on screen at the tap, and it
    overwrites while the claim is pending_payment: after a refused tap the second tap
    may be to a different price, and the stored version must say what was actually
    agreed.

    The card fingerprint is written from the PaymentMethod so later slices can run the
    credit card rules before any hold exists. A PaymentMethod that belongs to another
    Stripe customer is refused.
```

## Consent stamped at the pay tap: checks and stamp (case study 02)

`backend/app/routers/claims.py`, lines 1416–1455, at `4772472b`. Cited by: 06-case-studies/02.

```python
    if body.disclosure_version not in KNOWN_DISCLOSURE_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown consent version",
        )
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    if claim.picker_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    if claim.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim is not awaiting payment",
        )

    try:
        pm = retrieve_payment_method(body.payment_method_id)
    except StripeServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment setup failed",
        ) from None
    pm_customer = getattr(pm, "customer", None)
    if pm_customer is not None and not isinstance(pm_customer, str):
        pm_customer = getattr(pm_customer, "id", None)
    if pm_customer is not None and pm_customer != current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    claim.disclosure_version = body.disclosure_version
    claim.disclosure_accepted_at = datetime.now(timezone.utc)
```

## Unreadable is not absent: the pending-payment sweeper

`backend/app/jobs/pending_payment_sweeper.py`, lines 84–123 (first 40 lines of the function), at `4772472b`. Cited by: 04-troubleshooting/04-false-charge-message.md; 01-product-logic/failure-state-matrix.md (row 6).

```python
def _sweep_one(db: Session, claim: Claim) -> str:
    """The sweeper's decision for one eligible claim: "promoted", "cancelled" or "errored"."""
    # a4 — the money's true home is Stripe, not this row. Read it before
    # deciding this claim was abandoned.
    try:
        intent = _retrieve_intent(claim)
    except Exception:
        logger.exception(
            "pending_payment_sweeper_intent_read_failure claim_id=%s",
            str(claim.id),
        )
        return "errored"

    if intent is not None and _is_live_hold(intent):
        logger.error(
            json.dumps(
                {
                    "event": "pending_payment_divergence_live_hold",
                    "claim_id": str(claim.id),
                    "payment_intent_id": claim.stripe_payment_intent_id,
                    "action": "promoted to authorized; authorize webhook was never applied",
                }
            )
        )
        try:
            _handle_amount_capturable_updated(db, intent)
        except Exception:
            db.rollback()
            logger.exception(
                "pending_payment_sweeper_promote_failure claim_id=%s",
                str(claim.id),
            )
            return "errored"
        return "promoted"

    try:
        cancel_payment_intent(claim.id, "pending_payment_abandoned", db)
    except StripeServiceError:
        db.rollback()
        logger.error(
```

## Test: a live hold is promoted, not cancelled

`backend/tests/test_pending_payment_sweeper.py`, lines 148–187, at `4772472b`. Cited by: 04-troubleshooting/04-false-charge-message.md.

```python
def test_live_hold_is_promoted_not_cancelled(
    db_session, picker_user, active_listing, mocker, mock_stripe_pi_cancel,
):
    """a4 — the authorize webhook never arrived but the picker DID pay. The claim must
    be promoted to authorized, not cancelled out from under him."""
    pi_id = _real_shaped_pi_id()
    claim = models.Claim(
        listing_id=active_listing.id,
        picker_id=picker_user.id,
        status="pending_payment",
        stripe_payment_intent_id=pi_id,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    db_session.execute(
        text("UPDATE claims SET claimed_at=:t WHERE id=:cid"),
        {"cid": claim.id, "t": datetime.utcnow() - timedelta(minutes=6)},
    )
    db_session.commit()
    db_session.expire_all()

    mocker.patch(
        "app.jobs.pending_payment_sweeper.stripe.PaymentIntent.retrieve",
        return_value=_stripe_intent(
            pi_id, status="requires_capture", amount_capturable=200
        ),
    )

    result = run_pending_payment_sweeper(db_session)

    assert result.promoted == 1
    assert result.cancelled == 0
    mock_stripe_pi_cancel.assert_not_called()

    db_session.expire_all()
    fresh = db_session.get(models.Claim, claim.id)
    assert fresh.status == "authorized"
    assert fresh.authorized_at is not None
    assert fresh.cancelled_at is None
```

## The shared cancel path

`backend/app/services/claim_cancel_service.py`, lines 22–61 (first 40 lines of the function), at `4772472b`. Cited by: 01-product-logic/failure-state-matrix.md (rows 11, 13).

```python
def cancel_claim_for_initiator(
    db: Session,
    claim: Claim,
    listing: Listing,
    initiator_id: UUID,
    *,
    suppress_giver_trust_event: bool = False,
    bypass_grace_window: bool = False,
) -> None:
    """
    Core cancel logic shared by the manual cancel endpoint and the block handler.

    Applies the 2-hour grace window rule: if the initiator is the picker and a
    pickup is scheduled within 2h, the $2 hold is captured (late-cancel penalty);
    otherwise it is released. Does NOT commit — caller is responsible for committing
    and handling post-cancel notifications.

    bypass_grace_window=True (block handler only) skips the grace window
    entirely regardless of pickup proximity: the hold is always released, no
    late_cancel trust event is filed, and no strike is applied. Per Nick's
    2026-08-10 ruling, blocking someone never costs the picker money and never
    files a strike — the consented fee disclosure promises the hold is
    released on a block, with no exception for timing.

    Raises StripeServiceError on Stripe failures (with the same messages the cancel
    endpoint uses so the router can produce identical API responses).
    """
    is_picker = claim.picker_id == initiator_id
    is_giver = listing.giver_id == initiator_id

    inside_grace_window = False
    if (
        not bypass_grace_window
        and is_picker
        and claim.status in ("authorized", "pickup_scheduled")
        and claim.pickup_scheduled_at is not None
    ):
        sched = claim.pickup_scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
```

# `code/credits_devicecheck/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Which credits wait for DeviceCheck

`backend/app/services/credit_service.py`, lines 1–35, at `4772472b`. Cited by: 01-product-logic/device-check-credits.md; LIMITATIONS.md (Credits).

```python
"""Zelbi credits — earning (D539 step 4, D542, D580).

Slice 1: the first-giveaway credit. Every ending that completes a handoff earns it
(the picker's photo, the giver's yes, and the post-window sweeper's silence branches),
once per person, only while the ``giveaway_credit`` program switch is on. The write sits
inside the completion's own transaction, in a savepoint, so losing the once-per-person
index race never fails the completion. Nothing here commits; the caller's commit does.

D580: the giver-no-show credit, the picker's remedy when the support agent confirms that
the giver missed the pickup. It is a remedy, not an incentive: no program switch, no card
fingerprint, no DeviceCheck. One per claim, through uq_credits_giver_no_show_per_claim.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Claim, Credit, DeletedEmailFingerprint, ProgramSwitch, User, WatcherEvent
from app.utils.email_fingerprint import email_fingerprint

logger = logging.getLogger(__name__)

# D543 (5): a DeviceCheck refusal is a Control Center abuse alert, written to watcher_events
# the way api_abuse.record_api_signal writes a single-account signal.
DEVICE_REFUSAL_FAMILY = "account"
DEVICE_REFUSAL_KIND = "giveaway_credit_device_refused"
# D549 (survey C5): an invite credit refused because its iPhone already used a friend's code.
INVITE_DEVICE_REFUSAL_KIND = "invite_credit_device_refused"
# The credit kinds that wait for the iPhone check: giveaway (bit0, D542 (4)) and invite (bit1, D549).
DEVICE_CHECKED_CREDIT_KINDS = ("giveaway", "invite")
DEVICE_REFUSAL_SEVERITY = 4  # api_abuse's severity for a single-account signal
```

## The pending-credit lookup

`backend/app/services/credit_service.py`, lines 175–190, at `4772472b`. Cited by: 01-product-logic/device-check-credits.md.

```python
def pending_device_check_credit(db: Session, user_id: UUID) -> Credit | None:
    """The user's giveaway or invite credit still waiting for its iPhone check (D542 (4),
    D549 C5): unused, neither passed nor refused. None when there is nothing to check. With
    both kinds pending the giveaway credit comes first; the next app open checks the other."""
    return (
        db.query(Credit)
        .filter(
            Credit.user_id == user_id,
            Credit.kind.in_(DEVICE_CHECKED_CREDIT_KINDS),
            Credit.used_at.is_(None),
            Credit.device_checked_at.is_(None),
            Credit.device_check_refused_at.is_(None),
        )
        .order_by(Credit.kind.asc(), Credit.earned_at.asc())
        .first()
    )
```

## DeviceCheck fails closed when unconfigured

`backend/app/services/devicecheck_service.py`, lines 1–8, at `4772472b`. Cited by: 01-product-logic/device-check-credits.md.

```python
"""Apple DeviceCheck client (D542 (4), slice 1): the two per-device bits Apple keeps for us.

Backend client only; no route or caller yet. The Apple host comes from
settings.apple_devicecheck_environment, never from the phone. An unconfigured key or key id
fails closed with DeviceCheckError("not configured") before any network call.

Never logs the device token, the JWT or the private key: log lines are JSON events carrying
the endpoint path and Apple's status code only.
```

# ---------------------------------------------------------------------------
# SANITIZED FOR PUBLICATION. This file is copied verbatim from the private
# zelbi.ai repository except where a line reads "withheld". Withheld values
# are tuned product constants, not secrets; the logic that consumes them is
# unchanged. See MANIFEST.md for the exact line ranges and reasons.
# ---------------------------------------------------------------------------
"""Phase 6 STEP 2 slice (a) — scam detection rule engine.

Implements five enforced scam-detection rules per docs/agents/10-implementation-plan.md
§9, plus rule 5 (duplicate photo hash) explicitly stubbed as deferred per canonical
decision 11. Each rule is a pure function returning (triggered, reason, action);
the dispatchers collect triggered results into a list[ScamCheckResult] for the
caller. Empty list means no signals — proceed normally.

Locked decisions (Session 88, captured in the session plan file):

- Rule 3 blocks message send with HTTP 400, not strip-and-warn. The service
  returns the trigger; the caller raises 400.
- Rule 4 fires restrict_listing in STEP 2; STEP 3 layers cooldown/suspension
  on top later.

Wiring into routers/listings.py, routers/messages.py, and routers/claims.py
is slice (b)'s scope. This module ships only the engine and unit tests.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Report


# Action allowlist (per canonical Phase 6 STEP 2 spec).
ACTION_FLAG_FOR_REVIEW = "flag_for_review"
ACTION_RESTRICT_LISTING = "restrict_listing"

# D264 — listing tempo guard, replaces the retired GPS-spam rule.
# Tempo values withheld. The guard's shape: a minimum interval between two
# consecutive listings, and a per-day ceiling.
MIN_LISTING_INTERVAL_SECONDS = WITHHELD
MAX_LISTINGS_PER_DAY = WITHHELD

# Admin-facing name and meaning for every value write_auto_flag stores in
# reports.triggered_rule. The Control Center reads these through GET /admin/flags
# and GET /admin/listings/{id}; the dashboard keeps no copy.
RULE_DEFINITIONS: dict[str, tuple[str, str]] = {
    "rule_1": (
        "New account posting by hand",
        "Retired in Session 376 (D270); no longer fires",
    ),
    "rule_2": (
        "Listing tempo",
        "Listings posted faster than a person can post them, or more than the (withheld) daily ceiling",
    ),
    "rule_3": (
        "Contact or payment",
        "A message carried a phone number, email, handle, link, off-app payment term, "
        "urgency pattern or pickup time, and was blocked",
    ),
    # Not active: its only caller, run_claim_creation_checks, was never called and was
    # deleted (D568, Nick's call 2026-10-03). The number is kept.
    "rule_4": (
        "Repeated no-shows",
        "Not active",
    ),
    "rule_5": (
        "Duplicate photo",
        "Deferred past MVP (canonical decision 11); does not fire",
    ),
    "rule_6": (
        "Pricing on a free listing",
        "A listing's title or description mentions a price, a currency or best offer",
    ),
    "block_ended_claim": (
        "Block ended a claim",
        "A user blocked the other party while a claim between them was live, and the block cancelled it",
    ),
}
_UNKNOWN_RULE_TEXT = "No rule definition in the backend for this value"


def rule_definition(triggered_rule: str | None) -> tuple[str, str]:
    """(label, text) for a stored triggered_rule; an unknown value labels as itself."""
    if triggered_rule is None:
        return ("No rule recorded", _UNKNOWN_RULE_TEXT)
    return RULE_DEFINITIONS.get(triggered_rule, (triggered_rule, _UNKNOWN_RULE_TEXT))


@dataclass(frozen=True)
class ScamCheckResult:
    rule_name: str
    triggered: bool
    reason: str | None
    action: str | None


# --- Match-time normalization ---------------------------------------------
# Decodes common evasion tricks before any rule or deflect check runs. Only
# ever used to decide matches — never applied to what is stored or shown to
# the user. Every rule/deflect dispatcher normalizes ONCE at its entry point
# (run_message_send_checks, run_picker_question_deflect) so a rule added
# later cannot forget to call this.
_EMOJI_WORD_MAP = {
    "\U0001F4B5": "money",  # 💵
    "\U0001F4B0": "money",  # 💰
    "\U0001F4F1": "phone",  # 📱
    "\U0001F4CD": "pin",  # 📍
}
_REPEAT_RUN_REGEX = re.compile(r"([a-z])\1{2,}")
_SPACED_LETTERS_REGEX = re.compile(r"\b(?:[a-z][ .])+[a-z]\b")
_LOOKALIKE_CHARS = {"3": "e", "4": "a", "1": "i", "0": "o", "$": "s"}
_WHITESPACE_REGEX = re.compile(r"\s+")


def _decode_lookalikes(token: str) -> str:
    """Replace a look-alike digit/symbol only when it sits BETWEEN two real
    letters (v3nmo -> venmo, addr3ss -> address), so a genuine number stays
    a number — "3pm", "742", "$20", "2065550142" are all left untouched
    because the substitutable character doesn't have a letter on both sides."""
    chars = list(token)
    for i, ch in enumerate(chars):
        if ch not in _LOOKALIKE_CHARS:
            continue
        prev_is_letter = i > 0 and chars[i - 1].isalpha()
        next_is_letter = i < len(chars) - 1 and chars[i + 1].isalpha()
        if prev_is_letter and next_is_letter:
            chars[i] = _LOOKALIKE_CHARS[ch]
    return "".join(chars)


def normalize_for_match(content: str) -> str:
    """Normalize message content for matching only. Lowercases; collapses
    spaced-out single letters ("t e x t me" -> "text me"); maps look-alike
    digits/symbols back to letters when the character sits between two real
    letters (v3nmo -> venmo) while leaving pure numbers and number+unit
    tokens (phone digits, prices, "3pm") untouched; replaces meaning-carrying
    emoji with the word they stand in for; collapses stretched-out repeated
    letters; normalizes whitespace."""
    text = content.lower()
    for emoji, word in _EMOJI_WORD_MAP.items():
        text = text.replace(emoji, f" {word} ")
    text = _REPEAT_RUN_REGEX.sub(r"\1\1", text)
    text = _SPACED_LETTERS_REGEX.sub(
        lambda m: m.group(0).replace(" ", "").replace(".", ""), text
    )
    text = " ".join(_decode_lookalikes(tok) for tok in text.split())
    return _WHITESPACE_REGEX.sub(" ", text).strip()


# rule table withheld
#
# SHAPE OF WHAT WAS REMOVED (source lines 148-461 of the original file, 314
# lines): a flat table of module-level compiled regular expressions, one or
# more per detection category, each built from an alternation of literal
# trigger phrases and their evasion variants. The categories are the ones the
# dispatchers below reference by name: external payment brands (including a
# separator-squashed brand check for "p ay pal"-style spacing), phone numbers
# and phone solicitation (including spaced and spelled-out digits), urgency,
# currency and pricing keywords, email addresses and email solicitation,
# social handles and handle solicitation, links, weekdays / relative days /
# clock times / dayparts / loose hours / proposals / meeting verbs (which
# combine into the scheduling-intent signal), street addresses, cancel and
# confirm intents, and the picker-question deflect categories (location,
# availability, payment, schedule, pickup process, reschedule, cancel).
#
# The patterns themselves are the product's anti-abuse surface: publishing them
# publishes the evasion recipe. The normalizer above (which decodes the evasion
# tricks BEFORE any pattern runs) and the dispatcher framework below (which
# shows how rules compose, what each returns, and where enforcement happens)
# are the parts that carry the engineering argument, and both are intact.
#
# Every name referenced below is defined in the original file within this range.


def check_rule_2_listing_tempo(
    db: Session,
    user_id: UUID,
    now: datetime | None = None,
) -> tuple[bool, str | None, str | None]:
    """Rule 2 — Listing tempo (D264, replaces the retired GPS-spam rule).

    Trigger: another listing from the same giver inside
    MIN_LISTING_INTERVAL_SECONDS, or more than MAX_LISTINGS_PER_DAY listings
    from that giver in the last 24 hours. No location component — a move-out
    giver posting many items from one address is the intended user, not an
    attacker. The listing being created is not yet in the table when this runs
    (routers/listings.py adds and flushes after the checks), so it is not
    counted against itself.
    """
    if now is None:
        now = datetime.utcnow()
    row = db.execute(
        text(
            "SELECT "
            "  COUNT(*) FILTER (WHERE created_at >= :burst_cutoff) AS burst, "
            "  COUNT(*) FILTER (WHERE created_at >= :day_cutoff) AS day_count "
            "FROM listings WHERE giver_id = :giver_id"
        ),
        {
            "giver_id": user_id,
            "burst_cutoff": now - timedelta(seconds=MIN_LISTING_INTERVAL_SECONDS),
            "day_cutoff": now - timedelta(hours=24),
        },
    ).one()
    burst = row[0] or 0
    day_count = row[1] or 0
    if burst >= 1:
        return (True, "Listings posted faster than a person can post them", ACTION_FLAG_FOR_REVIEW)
    if day_count >= MAX_LISTINGS_PER_DAY:
        return (True, "Daily listing ceiling exceeded", ACTION_FLAG_FOR_REVIEW)
    return (False, None, None)


def check_rule_3_message_pattern(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 — Urgency pattern detection.

    Trigger: urgency phrases (hurry, urgent, limited time, act now).

    Locked Session 88: block with HTTP 400; no strip-and-warn. Caller raises.
    """
    if _URGENCY_REGEX.search(content):
        return (True, "Urgency pattern detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_phone(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 — Phone detection.

    Trigger: phone-number-like sequences (10-digit runs with optional
    separators), or a solicitation for a number (e.g. "what's your number",
    "call me at") even when no digits are present.
    """
    if (
        _PHONE_REGEX.search(content)
        or _SPACED_PHONE_REGEX.search(content)
        or _PHONE_SOLICIT_REGEX.search(content)
        or _SPELLED_PHONE_REGEX.search(content)
    ):
        return (True, "Phone number / solicitation detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_payment(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 — Off-platform payment detection.

    Trigger: regex match for external payment terms (venmo, paypal, cashapp,
    zelle).
    """
    if _EXTERNAL_PAY_REGEX.search(content):
        return (True, "External payment term detected", ACTION_RESTRICT_LISTING)
    squashed = _SQUASHED_SEPARATORS_REGEX.sub("", content)
    if _SQUASHED_PAY_BRANDS_REGEX.search(squashed):
        return (True, "External payment term detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_contact_email(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 extension — email address in message body. Same block action as
    rule 3 (restrict_listing); caller applies the existing 400 response."""
    if _EMAIL_REGEX.search(content) or _EMAIL_SOLICIT_REGEX.search(content):
        return (True, "Email address detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_contact_handle(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 extension — social/messaging handle (platform keyword or @handle)."""
    if (
        _HANDLE_KEYWORD_REGEX.search(content)
        or _AT_HANDLE_REGEX.search(content)
        or _SIGNAL_CUED_REGEX.search(content)
    ):
        return (True, "Social/messaging handle detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_contact_link(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 extension — external URL in message body."""
    if _URL_REGEX.search(content):
        return (True, "External link detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_rule_3_scheduling_intent(
    content: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 3 extension — high-confidence off-platform scheduling proposal.

    Biased toward pairs (a day reference plus a time reference) rather than
    single keywords, to avoid false catches on general chatter — e.g. "Monday"
    or "morning" alone don't trigger, but "Monday morning" or "3pm tomorrow"
    do. "after work" is treated as unambiguous on its own.
    """
    has_day = bool(_WEEKDAY_REGEX.search(content) or _RELATIVE_DAY_REGEX.search(content))
    has_time_ish = bool(_CLOCK_TIME_REGEX.search(content) or _DAYPART_REGEX.search(content))
    has_loose_hour = bool(_LOOSE_HOUR_REGEX.search(content))
    has_after_work = bool(_AFTER_WORK_REGEX.search(content))
    has_meet_verb = bool(_MEET_VERB_REGEX.search(content))
    has_propose = bool(_PROPOSE_REGEX.search(content))
    if (
        has_after_work
        or (has_day and (has_time_ish or has_loose_hour))
        or (has_meet_verb and (has_time_ish or has_loose_hour))
        or (has_propose and (has_time_ish or has_loose_hour))
    ):
        return (True, "Scheduling/time-proposal pattern detected", ACTION_RESTRICT_LISTING)
    return (False, None, None)


def check_signal_address_in_chat(content: str) -> tuple[bool, str | None]:
    """Tier 2 — street-address pattern in chat. Does not block; caller logs
    and returns an optional hint alongside the normal send response."""
    if _ADDRESS_REGEX.search(content):
        return (True, "address")
    return (False, None)


def check_signal_cancel_intent(content: str) -> tuple[bool, str | None]:
    """Tier 2 — cancel intent. Does not block."""
    if _CANCEL_REGEX.search(content):
        return (True, "cancel")
    return (False, None)


def check_signal_confirm_intent(content: str) -> tuple[bool, str | None]:
    """Tier 2 — pickup-confirmation intent. Does not block."""
    if _CONFIRM_REGEX.search(content):
        return (True, "confirm")
    return (False, None)


def check_rule_5_duplicate_photo_hash(
    *args: Any,
    **kwargs: Any,
) -> tuple[bool, str | None, str | None]:
    """Rule 5 — Duplicate photo hash. DEFERRED PAST MVP per canonical decision 11.

    The photo_content_hash column on listings is populated on upload, but the
    detection rule is not enforced for MVP. This stub returns
    (False, None, None) unconditionally regardless of inputs.

    See canonical decision 11 in docs/agents/10-implementation-plan.md and
    Section 5b of docs/agents/00-current-state.md. Do not enable without an
    explicit unlock decision.
    """
    # Canonical decision 11: deferred past MVP.
    return (False, None, None)


def check_rule_6_forbidden_keywords(
    title: str,
    description: str,
) -> tuple[bool, str | None, str | None]:
    """Rule 6 — Forbidden keywords in listing text.

    Trigger: case-insensitive substring match in title or description against
    currency symbols ($, €, £, ¥) or pricing keywords (asking, price,
    best offer).
    """
    haystack = f"{title} {description}"
    if _CURRENCY_REGEX.search(haystack) or _PRICING_KEYWORDS_REGEX.search(haystack):
        return (True, "Mentions pricing on free platform", ACTION_FLAG_FOR_REVIEW)
    return (False, None, None)


# --- Dispatchers ---------------------------------------------------------

def run_listing_creation_checks(
    listing: Any,
    user: Any,
    db: Session,
) -> list[ScamCheckResult]:
    """Run rules that fire on listing creation: rules 2, 5 (deferred), 6.

    Rule 1 (new account + manual listing) was deleted in Session 376 per D270:
    the mobile client hardcodes ai_generated=true on its only publish path, so
    the rule could never fire for a real user, and any non-app caller sets the
    flag itself. It cost nothing and caught nobody who had read a request.
    """
    results: list[ScamCheckResult] = []

    triggered, reason, action = check_rule_2_listing_tempo(
        db,
        user_id=user.id,
    )
    if triggered:
        results.append(ScamCheckResult(
            "rule_2_listing_tempo", True, reason, action,
        ))

    triggered, reason, action = check_rule_5_duplicate_photo_hash(
        getattr(listing, "photo_content_hash", None),
    )
    if triggered:
        results.append(ScamCheckResult(
            "rule_5_duplicate_photo_hash", True, reason, action,
        ))

    triggered, reason, action = check_rule_6_forbidden_keywords(
        title=listing.title,
        description=listing.description,
    )
    if triggered:
        results.append(ScamCheckResult(
            "rule_6_forbidden_keywords", True, reason, action,
        ))

    return results


_RULE_3_CHECKS: tuple[tuple[str, Any], ...] = (
    ("rule_3_phone", check_rule_3_phone),
    ("rule_3_payment", check_rule_3_payment),
    ("rule_3_message_pattern", check_rule_3_message_pattern),
    ("rule_3_contact_email", check_rule_3_contact_email),
    ("rule_3_contact_handle", check_rule_3_contact_handle),
    ("rule_3_contact_link", check_rule_3_contact_link),
    ("rule_3_scheduling_intent", check_rule_3_scheduling_intent),
)


def run_message_send_checks(message_content: str) -> list[ScamCheckResult]:
    """Run rules that fire on message send/edit: rule 3 (payment/phone/urgency)
    plus its contact-channel and scheduling-intent extensions. Callers treat
    any non-empty result list as a block (see routers/messages.py). Content is
    normalized once here — see normalize_for_match — before any rule runs."""
    normalized = normalize_for_match(message_content)
    results: list[ScamCheckResult] = []
    for rule_name, check in _RULE_3_CHECKS:
        triggered, reason, action = check(normalized)
        if triggered:
            results.append(ScamCheckResult(rule_name, True, reason, action))
    return results


def run_message_soft_signal_checks(message_content: str) -> str | None:
    """Tier 2 dispatcher: address / cancel / confirm intent. The message has
    already been allowed to send; the caller logs a structured signal and may
    surface an additive "hint" on the response. Checked in priority order —
    returns the first matching category, or None."""
    for check in (
        check_signal_address_in_chat,
        check_signal_cancel_intent,
        check_signal_confirm_intent,
    ):
        triggered, category = check(message_content)
        if triggered:
            return category
    return None


# --- Picker-side question-deflection (D251/D252) -------------------------
# These do NOT flag a scam. They intercept a platform-owned question the app
# already answers so the giver isn't bombarded. Picker-only, run AFTER the
# hard-block rules. The caller raises a 400 carrying the returned category and
# does NOT persist the message or write an auto-flag. First match wins.
# Buckets 1 (scheduling), 5 (pickup-process), 6 (cancel) are state-aware via
# is_scheduled; pickup_mode is no longer threaded through here — mode-specific
# wording is rendered by the app from the claim.
def check_deflect_location_q(content: str) -> str | None:
    """Bucket 2 — 'where do I pick up / what's the address'."""
    return "location_info" if _LOCATION_Q_REGEX.search(content) else None


def check_deflect_availability_q(content: str) -> str | None:
    """Bucket 3 — only 'am I confirmed?' (NOT 'is it still available')."""
    return "availability" if _AVAILABILITY_Q_REGEX.search(content) else None


def check_deflect_payment_q(content: str) -> str | None:
    """Bucket 4 — 'did my payment go through / was I charged / how much'.

    Distinct from the venmo/paypal hard block, which runs first and wins.
    """
    return "payment_info" if _PAYMENT_Q_REGEX.search(content) else None


def check_deflect_schedule_q(content: str) -> str | None:
    """Bucket 1 — a scheduling question ('when can I pick it up?', 'what time?',
    'are we still on?'). Distinct from an off-platform time PROPOSAL, which the
    hard block catches first. Client renders state-aware copy off the claim."""
    return "schedule_q" if _SCHEDULE_Q_REGEX.search(content) else None


def check_deflect_pickup_process_q(content: str) -> str | None:
    """Bucket 5 — 'is this curbside or do we meet?', 'do I knock?'. Only
    meaningful once scheduled (mode is set); the dispatcher gates on that.
    Client renders mode-aware copy (porch note inline / meet)."""
    return "pickup_process" if _PICKUP_PROCESS_Q_REGEX.search(content) else None


def check_deflect_reschedule_q(content: str) -> str | None:
    """Bucket 6 (reschedule) — 'can I reschedule?', 'change my pickup time?'.
    Checked before cancel so it wins over the generic cancel copy."""
    return "reschedule_info" if _RESCHEDULE_Q_REGEX.search(content) else None


def check_deflect_cancel_q(content: str) -> str | None:
    """Bucket 6 (cancel) — 'how do I cancel?', 'do I get my $2 back?'. Client
    renders the 2-hour grace rule off the claim (refund vs late-cancel)."""
    return "cancel_info" if _CANCEL_Q_REGEX.search(content) else None


def run_picker_question_deflect(
    content: str,
    *,
    is_scheduled: bool,
) -> str | None:
    """Picker-side platform-owned-question deflection dispatcher (D251/D252).
    Content is normalized once here — see normalize_for_match — before any
    deflect check runs."""
    normalized = normalize_for_match(content)
    for check in (
        check_deflect_schedule_q,
        check_deflect_reschedule_q,
        check_deflect_cancel_q,
        check_deflect_location_q,
        check_deflect_availability_q,
        check_deflect_payment_q,
    ):
        category = check(normalized)
        if category is not None:
            return category
    # Pickup-process only makes sense once a time is set. Pickup mode is not read
    # here — the app renders the mode-specific wording from the claim.
    if is_scheduled and check_deflect_pickup_process_q(normalized) is not None:
        return "pickup_process"
    return None


def write_auto_flag(
    db: Session,
    *,
    target_user_id: UUID,
    rule_name: str,
    reason: str,
    listing_id: UUID | None,
    report_reason: str = 'scam',
) -> None:
    """Stage an auto-flag Report row in the session. Caller controls commit timing.

    Constructs a Report with reporter_id=None (no human reporter), source='auto',
    and the supplied triggered_rule label. Does not call db.commit — the caller
    decides when to flush/commit so that auto-flags can either be batched with
    other writes (listing creation) or committed before raising (message send).

    report_reason sets the stored Report.reason (must satisfy ck_reports_reason);
    defaults to 'scam' for the original scam-detection callers. Non-scam callers
    (e.g. the block handler recording a block that ended a live claim) pass
    'other' so the review surface doesn't mislabel the report.
    """
    db.add(
        Report(
            reporter_id=None,
            reported_user_id=target_user_id,
            listing_id=listing_id,
            reason=report_reason,
            description=reason,
            status='pending',
            source='auto',
            triggered_rule=rule_name,
        )
    )

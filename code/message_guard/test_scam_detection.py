"""Phase 6 STEP 2 slice (a) — scam detection rule engine tests.

Eighteen tests, three per rule. Calls each check_rule_N function directly.
Rules 1, 3, 5, 6 are pure-function tests; rules 2 and 4 use the db_session
fixture from conftest. Wiring tests are slice (b)'s scope.
"""
from datetime import datetime, timedelta

import pytest

from app import models
from app.services.scam_detection import (
    MAX_LISTINGS_PER_DAY,
    check_rule_2_listing_tempo,
    check_rule_3_contact_email,
    check_rule_3_contact_handle,
    check_rule_3_contact_link,
    check_rule_3_message_pattern,
    check_rule_3_payment,
    check_rule_3_phone,
    check_rule_3_scheduling_intent,
    check_rule_4_repeated_no_shows,
    check_rule_5_duplicate_photo_hash,
    check_rule_6_forbidden_keywords,
    check_signal_address_in_chat,
    check_signal_cancel_intent,
    check_signal_confirm_intent,
    run_message_send_checks,
    run_message_soft_signal_checks,
    run_picker_question_deflect,
)


def _create_listing(
    db_session,
    giver_user,
    *,
    lat: float = 37.7749,
    lng: float = -122.4194,
    ai_generated: bool = True,
    created_at: datetime | None = None,
) -> models.Listing:
    now = datetime.utcnow()
    listing = models.Listing(
        giver_id=giver_user.id,
        title="Test",
        description="Desc",
        category="Other",
        photo_urls=["https://example.com/1.jpg"],
        location_lat=lat,
        location_lng=lng,
        location_lat_approx=lat + 0.001,
        location_lng_approx=lng + 0.001,
        status="active",
        ai_generated=ai_generated,
        created_at=created_at or now,
        expires_at=now + timedelta(days=7),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return listing


def _create_no_show_claim(
    db_session,
    listing,
    picker,
    *,
    no_show_at: datetime,
) -> models.Claim:
    claim = models.Claim(
        listing_id=listing.id,
        picker_id=picker.id,
        status="no_show",
        no_show_at=no_show_at,
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


# --- Rule 2: Listing tempo (D264) ---------------------------------------

def test_rule2_listing_inside_interval_triggers(db_session, giver_user):
    _create_listing(db_session, giver_user)
    triggered, reason, action = check_rule_2_listing_tempo(
        db_session,
        user_id=giver_user.id,
    )
    assert triggered is True
    assert reason == "Listings posted faster than a person can post them"
    assert action == "flag_for_review"


def test_rule2_same_location_outside_interval_does_not_trigger(db_session, giver_user):
    # Three listings at one address is the move-out giver, not an attacker.
    # Location plays no part; only elapsed time does.
    for _ in range(3):
        _create_listing(db_session, giver_user)
    triggered, reason, action = check_rule_2_listing_tempo(
        db_session,
        user_id=giver_user.id,
        now=datetime.utcnow() + timedelta(hours=2),
    )
    assert triggered is False
    assert reason is None
    assert action is None


def test_rule2_daily_ceiling_triggers(db_session, giver_user):
    for _ in range(MAX_LISTINGS_PER_DAY):
        _create_listing(db_session, giver_user)
    triggered, reason, action = check_rule_2_listing_tempo(
        db_session,
        user_id=giver_user.id,
        now=datetime.utcnow() + timedelta(seconds=60),
    )
    assert triggered is True
    assert reason == "Daily listing ceiling exceeded"
    assert action == "flag_for_review"


# --- Rule 3: Message pattern detection ----------------------------------

def test_rule3_urgency_triggers():
    triggered, reason, action = check_rule_3_message_pattern("act now, limited time!")
    assert triggered is True
    assert reason == "Urgency pattern detected"
    assert action == "restrict_listing"


def test_rule3_clean_message_does_not_trigger():
    triggered, reason, action = check_rule_3_message_pattern(
        "Hi, when can I pick this up?"
    )
    assert triggered is False
    assert reason is None
    assert action is None


# --- Rule 3: Phone detection ---------------------------------------------

def test_rule3_phone_digits_trigger():
    triggered, reason, action = check_rule_3_message_pattern("call me at 5551234567")
    assert triggered is False  # digits are no longer part of the message-pattern rule
    triggered, reason, action = check_rule_3_phone("call me at 5551234567")
    assert triggered is True
    assert action == "restrict_listing"


def test_rule3_phone_solicitation_no_digits_triggers():
    triggered, reason, action = check_rule_3_phone("what's your number?")
    assert triggered is True
    assert action == "restrict_listing"


def test_rule3_phone_solicitation_curly_apostrophe_triggers():
    triggered, reason, action = check_rule_3_phone("What’s your number?")
    assert triggered is True


def test_rule3_phone_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_phone("Is this still available?")
    assert triggered is False


# --- Rule 3: Payment detection --------------------------------------------

def test_rule3_venmo_triggers():
    triggered, reason, action = check_rule_3_payment("send me venmo @nick")
    assert triggered is True
    assert reason == "External payment term detected"
    assert action == "restrict_listing"


def test_rule3_payment_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_payment("Is this still available?")
    assert triggered is False


# --- Rule 3 extension: contact channels & scheduling --------------------

def test_rule3_email_triggers():
    triggered, reason, action = check_rule_3_contact_email(
        "reach me at nick@example.com"
    )
    assert triggered is True
    assert reason == "Email address detected"
    assert action == "restrict_listing"


def test_rule3_email_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_contact_email(
        "Is this still available?"
    )
    assert triggered is False


def test_rule3_handle_keyword_triggers():
    triggered, reason, action = check_rule_3_contact_handle(
        "add me on instagram"
    )
    assert triggered is True
    assert reason == "Social/messaging handle detected"
    assert action == "restrict_listing"


def test_rule3_handle_at_mention_triggers():
    triggered, reason, action = check_rule_3_contact_handle("hit me up @nickb")
    assert triggered is True


def test_rule3_handle_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_contact_handle(
        "Sounds great, thank you!"
    )
    assert triggered is False


def test_rule3_bare_signal_word_does_not_trigger():
    triggered, reason, action = check_rule_3_contact_handle(
        "give me a signal when you're there"
    )
    assert triggered is False


def test_rule3_cued_signal_triggers():
    triggered, reason, action = check_rule_3_contact_handle("hit me up on signal")
    assert triggered is True
    assert action == "restrict_listing"


def test_rule3_link_triggers():
    triggered, reason, action = check_rule_3_contact_link(
        "details here https://example.com/listing"
    )
    assert triggered is True
    assert reason == "External link detected"
    assert action == "restrict_listing"


def test_rule3_link_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_contact_link("See you soon!")
    assert triggered is False


def test_rule3_scheduling_day_and_time_triggers():
    triggered, reason, action = check_rule_3_scheduling_intent(
        "Can you do Monday morning?"
    )
    assert triggered is True
    assert reason == "Scheduling/time-proposal pattern detected"
    assert action == "restrict_listing"


def test_rule3_scheduling_after_work_triggers():
    triggered, reason, action = check_rule_3_scheduling_intent(
        "I can swing by after work"
    )
    assert triggered is True


def test_rule3_scheduling_day_alone_does_not_trigger():
    triggered, reason, action = check_rule_3_scheduling_intent(
        "Monday was a busy day"
    )
    assert triggered is False


def test_rule3_scheduling_clean_does_not_trigger():
    triggered, reason, action = check_rule_3_scheduling_intent(
        "Is this still available?"
    )
    assert triggered is False


# --- Tier 2: address / cancel / confirm signals --------------------------

def test_signal_address_triggers():
    triggered, category = check_signal_address_in_chat(
        "I'm at 742 Evergreen Terrace"
    )
    assert triggered is True
    assert category == "address"


def test_signal_address_clean_does_not_trigger():
    triggered, category = check_signal_address_in_chat("Is this still available?")
    assert triggered is False
    assert category is None


def test_signal_cancel_triggers():
    triggered, category = check_signal_cancel_intent("sorry, I need to cancel")
    assert triggered is True
    assert category == "cancel"


def test_signal_cancel_cant_make_it_triggers():
    triggered, category = check_signal_cancel_intent("can't make it today")
    assert triggered is True
    assert category == "cancel"


def test_signal_confirm_triggers():
    triggered, category = check_signal_confirm_intent("picked it up, thanks!")
    assert triggered is True
    assert category == "confirm"


def test_signal_confirm_clean_does_not_trigger():
    triggered, category = check_signal_confirm_intent("Is this still available?")
    assert triggered is False
    assert category is None


def test_run_message_soft_signal_checks_plain_chatter_returns_none():
    assert run_message_soft_signal_checks("Is this still available?") is None


def test_run_message_soft_signal_checks_returns_first_match_category():
    assert run_message_soft_signal_checks("got it thanks") == "confirm"


# --- Rule 4: Repeated no-shows ------------------------------------------

def test_rule4_three_no_shows_in_30d_triggers(db_session, picker_user, giver_user):
    now = datetime.utcnow()
    for _ in range(3):
        listing = _create_listing(db_session, giver_user)
        _create_no_show_claim(
            db_session, listing, picker_user, no_show_at=now - timedelta(days=5),
        )
    triggered, reason, action = check_rule_4_repeated_no_shows(
        db_session, picker_user_id=picker_user.id, now=now,
    )
    assert triggered is True
    assert reason == "Repeated no-shows in trailing 30 days"
    assert action == "restrict_listing"


def test_rule4_two_no_shows_in_30d_does_not_trigger(
    db_session, picker_user, giver_user,
):
    now = datetime.utcnow()
    for _ in range(2):
        listing = _create_listing(db_session, giver_user)
        _create_no_show_claim(
            db_session, listing, picker_user, no_show_at=now - timedelta(days=5),
        )
    triggered, reason, action = check_rule_4_repeated_no_shows(
        db_session, picker_user_id=picker_user.id, now=now,
    )
    assert triggered is False


def test_rule4_old_no_shows_outside_window_do_not_trigger(
    db_session, picker_user, giver_user,
):
    now = datetime.utcnow()
    for _ in range(3):
        listing = _create_listing(db_session, giver_user)
        _create_no_show_claim(
            db_session, listing, picker_user, no_show_at=now - timedelta(days=31),
        )
    triggered, reason, action = check_rule_4_repeated_no_shows(
        db_session, picker_user_id=picker_user.id, now=now,
    )
    assert triggered is False


# --- Rule 5: Duplicate photo hash (DEFERRED stub) -----------------------

def test_rule5_stub_returns_false_on_any_input():
    triggered, reason, action = check_rule_5_duplicate_photo_hash()
    assert triggered is False
    assert reason is None
    assert action is None


def test_rule5_stub_returns_false_with_hash_present():
    triggered, reason, action = check_rule_5_duplicate_photo_hash("a" * 64)
    assert triggered is False
    assert reason is None
    assert action is None


def test_rule5_stub_docstring_contains_deferred():
    doc = check_rule_5_duplicate_photo_hash.__doc__
    assert doc is not None
    assert "deferred" in doc.lower()


# --- Rule 6: Forbidden keywords -----------------------------------------

def test_rule6_currency_in_title_triggers():
    triggered, reason, action = check_rule_6_forbidden_keywords(
        title="Couch $50",
        description="Old couch.",
    )
    assert triggered is True
    assert reason == "Mentions pricing on free platform"
    assert action == "flag_for_review"


def test_rule6_best_offer_in_description_mixed_case_triggers():
    triggered, reason, action = check_rule_6_forbidden_keywords(
        title="Lamp",
        description="Or Best Offer accepted.",
    )
    assert triggered is True
    assert action == "flag_for_review"


def test_rule6_clean_text_does_not_trigger():
    triggered, reason, action = check_rule_6_forbidden_keywords(
        title="Free couch",
        description="Lightly used, comes with cushions.",
    )
    assert triggered is False
    assert reason is None
    assert action is None


# --- Rule 3 payment: squashed-separator brand scan -----------------------

def test_rule3_payment_squashed_spaces_triggers():
    assert run_message_send_checks("p ay pal me") != []


def test_rule3_payment_squashed_emoji_triggers():
    assert run_message_send_checks("\U0001F4B0 works") != []


def test_deflect_availability_reserve_4_me_scheduled_triggers():
    assert run_picker_question_deflect("reserve it 4 me", is_scheduled=True) == "availability"


def test_deflect_availability_reserve_for_me_scheduled_triggers():
    assert run_picker_question_deflect("reserve it for me", is_scheduled=True) == "availability"


def test_deflect_availability_reserve_4_me_unscheduled_triggers():
    assert run_picker_question_deflect("reserve it 4 me", is_scheduled=False) == "availability"


# --- Arrival phrases still pass both paths --------------------------------

@pytest.mark.parametrize(
    "content",
    [
        "on my way",
        "running late",
        "im outside",
        "knocking now",
        "be there in 5",
        "just parked",
    ],
)
def test_arrival_phrase_does_not_trigger_message_send_checks(content):
    assert run_message_send_checks(content) == []


@pytest.mark.parametrize(
    "content",
    [
        "on my way",
        "running late",
        "im outside",
        "knocking now",
        "be there in 5",
        "just parked",
    ],
)
def test_arrival_phrase_does_not_trigger_picker_deflect(content):
    assert run_picker_question_deflect(content, is_scheduled=True) is None


# --- Squashed scan does not affect spaced-digit prices --------------------

def test_spaced_digit_price_unaffected_by_squashed_brand_scan():
    # Current guard does not treat spaced-out digits as a phone or payment
    # signal; the squashed-separator brand scan only matches brand names,
    # so this stays uncaught by either path.
    # Was "2 0 6 5 5 5 0 1 4 2" until 2026-08-13 — that is a real area code plus seven
    # digits, i.e. a phone number, and _SPACED_PHONE_REGEX now correctly blocks it.
    # This test is about the squashed-brand scan, not phone numbers, so the example
    # moves to spaced digits that are NOT ten long. Nick ruled the change.
    assert run_message_send_checks("2 0 6 5 5 5 0 1 4") == []


def test_rule3_fully_spaced_phone_number_is_blocked():
    """A number typed one digit at a time slipped every phone pattern: the normalizer
    leaves numeric tokens alone on purpose (so "$5" and "3pm" survive for other rules),
    and _PHONE_REGEX allows only ONE separator between groups. Filed Session 404, closed
    2026-08-13."""
    assert check_rule_3_phone("2 0 6 5 5 5 1 2 3 4")[0] is True
    assert check_rule_3_phone("2.0.6.5.5.5.1.2.3.4")[0] is True
    assert check_rule_3_phone("call me at 4 2 5 8 6 7 5 3 0 9 thanks")[0] is True


def test_rule3_ordinary_messages_with_numbers_still_send():
    """Guards the fix above: the spaced-digit pattern must never catch prices,
    quantities or times. If one of these starts failing, the pattern is too loose."""
    for msg in (
        "I have 2 of them, can do 3 pm",
        "$5 for 20 lbs, 2 left",
        "see you at 4",
        "order 1 2 3 is ready",
        "it's 6 ft by 3 ft",
    ):
        assert check_rule_3_phone(msg)[0] is False, msg

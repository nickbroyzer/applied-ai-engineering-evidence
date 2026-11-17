# Draft fact check — 2026-11-17

Every checkable fact in the three case-study drafts, checked against the private
Zelbi repository at `4772472bdf2f370ea3b54971d8e94c9474cf7aaf` (`4772472b`,
2026-11-16), read from `~/Projects/zelbi.ai` on `master`.

Drafts checked (read-only, in `evidence-drafts-2026-11-17/`):

| File | md5 | Expected |
|---|---|---|
| `case-study-01-reminder-that-never-fired.md` | `ddf2429b3bd10307d3fb5d5ffd4b4e6d` | match |
| `case-study-02-consent-before-the-tap.md` | `6c0d26795ddeb76a561c61750122663d` | match |
| `case-studies-03-09.md` | `59aaef1a6e6b1d3c6b79f7739ddf1916` | match |

Method: `git show --stat <hash>` for commits; `grep` for tests, functions and
constants; the decision text in `docs/agents/10-implementation-plan.md`; the
backlog, current-state and test-case records in `docs/agents/` for figures;
`node --test` for the Node test count.

**Result: all rows OK.**

History: a first pass on the same day, against an earlier `case-studies-03-09.md`
(md5 `1ddba3dcdea014fd762011b16c3e9ea2`), found three mismatches (the build 15
and 16 TestFlight claim, the build 20 approval date, and the giver's
confirm-after time). Nick corrected the draft; this table re-checks the
corrected text. Drafts 01 and 02 and the Zelbi HEAD are unchanged since that
pass.

---

## 01 — The reminder that had never fired

| # | Claim | Where checked | Result |
|---|---|---|---|
| 01-a | Four "coming up" notification types, giver and picker, curbside and meet-up versions | `backend/app/jobs/post_window_sweeper.py:440-480`: `pickup_imminent_reminder_{giver,picker}{,_porch}` | OK |
| 01-b | None had ever sent in production | D410 (2026-08-29): "All four 'coming up' types had NEVER FIRED IN PRODUCTION"; commit body of `906a60a` | OK |
| 01-c | Found during the late-August notification rework (D410) | D410 LOCKED 2026-08-29, Session 426; neighbouring notification commits `93213060` (08-27), `138cce7` (08-28) | OK |
| 01-d | The reminders sat inside the deadline-nudge loop, whose query selects status `authorized` | `git show 906a60a^:backend/app/jobs/post_window_sweeper.py:97-110`: `_eligible_for_t_minus_24h_reminder` filters `Claim.status == "authorized"` | OK |
| 01-e | Every route that sets a pickup time sets `pickup_scheduled` in the same statement | `backend/app/routers/claims.py:2125,2133` (the only non-null write of `pickup_scheduled_at`); D410 wording | OK |
| 01-f | Fixture writes `authorized` and a pickup time in one raw SQL update; quoted text | `backend/tests/test_post_window_sweeper.py:419-421` (`:415` before `906a60a`), byte-identical | OK |
| 01-g | Fix: own query, pickup 23–25 h away, either status; quoted function | `post_window_sweeper.py:142-165`, `_eligible_for_imminent_reminder`; code lines identical | OK |
| 01-h | Commit `906a60a`, 2026-08-29 | `git show --stat 906a60a`: 2026-08-29 16:29 -0700 | OK |
| 01-i | The docstring records the cause | `post_window_sweeper.py:143-151` | OK |
| 01-j | `test_imminent_reminder_fires_for_a_claim_booked_through_the_real_routes`, commit `0cd7e3ce` | `backend/tests/test_imminent_reminder_real_path.py:31`; `git show --stat 0cd7e3ce` (2026-11-16) | OK |
| 01-k | Giver proposes through the real route, picker selects; claim reaches `pickup_scheduled`; one sweep sends both, second sends nothing new; only the 9 AM–9 PM check is stubbed | same file, lines 36-78 (`_validate_pickup_hours` monkeypatched) | OK |
| 01-l | One-hour reminder: 10-minute window on the daily job, moved to the 10-minute job, `a2197e88`, 2026-07-27 | `git show --stat a2197e88`: 2026-07-27, run_daily_jobs → run_frequent_jobs; `backend/lessons.md:59` (2026-07-27) | OK |
| 01-m | Time-critical notifications went through the digest path, now immediate, `f857bd2e`, 2026-07-27 | `git show --stat f857bd2e`: 2026-07-27, message matches | OK |
| 01-n | iOS drops foreground pushes without a handler; Zelbi had none; added in `93213060`, 2026-08-27 | `git show 93213060 -- mobile/app/_layout.tsx` (handler added, comment "Found 2026-08-27") | OK |

## 02 — Consent recorded before anyone agreed

| # | Claim | Where checked | Result |
|---|---|---|---|
| 02-a | A $2 hold on the picker's card | `claims.py:155-156,345`; `create_claim_payment_intent` docstring ("the $2 manual-capture intent") | OK |
| 02-b | Columns `disclosure_version` and `disclosure_accepted_at` | `f38dd81d` (migration `…078c24e1139_add_disclosure_consent_to_claims.py`); `claims.py:1454-1455` | OK |
| 02-c | The checkout screen creates the claim on open; consent was stamped in the same request | D319; `7dd9faf6` diff of `test_claim_consent.py` (old assertion `disclosure_accepted_at is not None` at creation) | OK |
| 02-d | At creation only the version; unknown version refused | D317; `test_create_claim_422_when_disclosure_version_missing`, `…_400_when_disclosure_version_unknown` | OK |
| 02-e | At the tap: picker only, only while awaiting payment (409); payment blocked if the call fails | D319 text; `7dd9faf6` test `test_accept_disclosure_stamps_once_and_only_in_pending_payment` (409) | OK |
| 02-f | 13.1 s vs 0.09 s on the device walk | D319: "13.1s gap … against 0.09s under the old behavior" | OK |
| 02-g | The fix broke two tests that asserted the open-screen stamp | `git show 7dd9faf6 -- backend/tests/test_claim_consent.py`: two `is not None` assertions inverted (creation test, reuse test) | OK |
| 02-h | The four quoted test names | `backend/tests/test_claim_consent.py:20,33,44,55` | OK |
| 02-i | About six weeks later checkout moved to Stripe's deferred intent | `4ba59f76` 2026-09-27 "checkout hold moves to the pay tap (Stripe deferred intent); D549" (6.7 weeks after `c1a2fc55`) | OK |
| 02-j | Quoted consent lines in the same request that creates the hold | `claims.py:1454-1455`, `create_claim_payment_intent` | OK |
| 02-k | Refuses unknown version 400, non-picker 403, not awaiting payment 409, another customer's card 403 | `claims.py:1416-1452` | OK |
| 02-l | After a refused tap the stored version is the one actually agreed | `create_claim_payment_intent` docstring, `claims.py:1407-1410` | OK |
| 02-m | Decisions D317, D319, D549 | `10-implementation-plan.md:2452,2458,2958` | OK |
| 02-n | Commits `f38dd81d` (record consent), `c1a2fc55` (stamp at the tap), `7dd9faf6` (tests assert the tap-time stamp) | `git show --stat` of each: 2026-08-10, 2026-08-11, 2026-08-11; messages match | OK |
| 02-o | `backend/tests/test_claim_consent.py`; `backend/app/routers/claims.py`, `create_claim_payment_intent` | both exist; function at `claims.py:1396` | OK |

## 03 — An old notification opened a stranger's pickup

| # | Claim | Where checked | Result |
|---|---|---|---|
| 03-a | The handoff screen asked for the newest claim on the listing | `git show 138cce7`: `getClaimByListing(listingId)` replaced | OK |
| 03-b | Cancelling returns the same listing to active; after relist and re-claim an old notification resolved to a stranger's claim, or 403 | `138cce7` code comment; D402 | OK |
| 03-c | Quoted snippet (comment line, before and after) | `138cce7` diff of `mobile/app/handoff/[claimId].tsx` — condensed from the diff, every code line present | OK |
| 03-d | Same fix in the choose-a-time screen; `138cce7`, 2026-08-28, D402 | `138cce7` touches `mobile/app/listing/pickup-time.tsx`; dated 2026-08-28; D402 "Shipped at 138cce7" | OK |
| 03-e | `GET /claims/{id}` answers 403 `{"detail": "Not a party to this claim"}` | `claims.py:1018` | OK |
| 03-f | `test_stranger_requesting_a_claim_by_id_is_refused_with_no_pickup_details`, `test_unknown_claim_id_is_404_not_403`, commit `0cd7e3ce`; picker and giver control | `backend/tests/test_claim_access_stranger.py:28,63` | OK |
| 03-g | The app has no screen tests | `git ls-files mobile` shows only three Node test files (`utils/*.test.mjs`) | OK |

## 04 — One error code with two opposite meanings

| # | Claim | Where checked | Result |
|---|---|---|---|
| 04-a | Found 2026-07-26 while tracing why an expired claim still showed | `00-current-state-archive.md:1634`, Session 366 (2026-07-26) | OK |
| 04-b | A claim whose cancel failed was dropped permanently, with no alert | same entry: "abandons any claim whose Stripe cancel fails, permanently and silently" | OK |
| 04-c | `resource_missing` has two causes | `backend/lessons.md:61` (2026-07-27) | OK |
| 04-d | Quoted `_REAL_PI_RE` comment and regex | `backend/app/services/stripe_service.py:60-63`, identical | OK |
| 04-e | Real-looking id left as is, logged at error level as `auto_cancel_orphaned_hold_suspected` | `post_window_sweeper.py:307-322` | OK |
| 04-f | Commit `db9cb43f`, 2026-07-27 | `git show --stat db9cb43f`: 2026-07-27 | OK |
| 04-g | Earlier test: skips the synthetic id, still captures the real one | `test_post_window_sweeper.py:945`, `test_sweeper_skips_synthetic_payment_intent_ids_but_still_captures_real_ones` | OK |
| 04-h | D584: seed-marked ids never reach Stripe | `10-implementation-plan.md:3059` | OK |
| 04-i | The two new tests and what they assert | `backend/tests/test_orphaned_hold_left_untouched.py:73-130` | OK |

## 05 — Rejected by Apple

| # | Claim | Where checked | Result |
|---|---|---|---|
| 05-a | Guideline 2.5.4, background location | `backlog.md:121` | OK |
| 05-b | Build 14 rejected 2026-10-26; location in background modes, no feature needing it; Apple's two options | `backlog.md:121` (rejected 2026-10-26 2:51 PM; both options named) | OK |
| 05-c | Removing the mode alone breaks arrival: the library throws without it; guard patched out | `backlog.md:122` (`startGeofencingAsync` throws `LocationUpdatesUnavailable`); `mobile/patches/expo-location+19.0.8.patch` | OK |
| 05-d | Guard patched out and the mode removed (`a6e663bc`, 2026-10-26) | `git show --stat a6e663bc`: 2026-10-26 16:05 -0700, removes the mode from `mobile/app.json`, adds `mobile/patches/expo-location+19.0.8.patch`. (The earlier draft's "builds 15 and 16 shipped to TestFlight" is no longer in the text.) | OK |
| 05-e | Build 19 walked on a real iPhone, every check logged | D635 (walk evidence, `user_events arrival_check`) | OK |
| 05-f | 150 m ring: 18 checks in 4 s at 118–119 m, accuracy 8–9 m | D635 | OK |
| 05-g | 100 m ring: 3 checks at 67 m, then no wakes; nothing fired at the door | D635 | OK |
| 05-h | Each wake about 32 m inside its ring | D635 | OK |
| 05-i | At the door the data load failed on the network; manual retry stamped at 11 m | D635 | OK |
| 05-j | Silent 50 m ring and retrying loads (D635) | D635 (1), (3) | OK |
| 05-k | Background mode back for arrival only (D636, amended by D637): 600 m hub check, 1 km first significant-change report; stops at 15 min, 1.5 km or window end; blue indicator on; rings as fallback | D636, D637 | OK |
| 05-l | Stamp rule unchanged: one reading within 25 m at 20 m accuracy or better; no coordinates reach the server | D635 ("the 25 m / 20 m stamp rule (D629) is unchanged"); D628 (`arrival_check` "never coordinates"); `confirm_geofence` stamps a time (D71) | OK |
| 05-m | The walk doubled as the recording; reply 2026-10-28 with build 20; fallback build 21 without the mode | D636 answers (5), (8); `backlog.md:765` (reply 2026-10-28 11:30 PT) | OK |
| 05-n | Apple approved build 20 by 2026-11-03; released 2026-11-04 (also in the In-short line) | Approval: commit `5a066b85` (2026-11-03 17:44 -0800, "build 20 approved"). Release: `00-current-state.md:12,104` ("released 2026-11-04") | OK |
| 05-o | Device walk and recording drive passed | `00-current-state-archive.md:3075` (Session 489) | OK |
| 05-p | Arrival rule's own Node test file: 110 tests as `node --test` reports | `node --test mobile/utils/arrivalRule.test.mjs` on 2026-11-17, Node v24.14.0: `tests 110, pass 110, fail 0` | OK |

## 06 — Live Activities

| # | Claim | Where checked | Result |
|---|---|---|---|
| 06-a | Native Swift: widget target, island views, App Intent | `mobile/targets/pickup-activity/{PickupActivityWidget,PickupIslandView,CollectAnswerIntent}.swift` | OK |
| 06-b | The three wrong assumptions (card gone only reported while running; APNs 200 for a missing card; `card_carries` trusted its own row) | D625 "Found:" | OK |
| 06-c | Reconcile (D625): launch, foreground, push wake, sign-in, before every arrival call (at most 4 s); unlisted open cards marked dismissed | D625 (1)–(2) | OK |
| 06-d | Build 18 test: swipe reaches the server in about a second with the app force-quit (D627) | D627 "Evidence" | OK |
| 06-e | Card only if a card that can still show it exists, otherwise a banner (D627) | D627 (1) | OK |
| 06-f | The server keeps the latest swipe (D628) | D628 | OK |
| 06-g | 135 backend test functions across the Live Activity and push-sender test files | `grep -cE '^(async )?def test_'`: `test_live_activity_*.py` (9 files) 121 + `test_apns_service.py` 14 = 135 | OK |

## 07 — Help search

| # | Claim | Where checked | Result |
|---|---|---|---|
| 07-a | Session 463, 24 real questions: 6 refusals, 4 wrong-article answers, 1,600–2,000-character pastes, all 8 articles last edited in July, golden table empty | `backlog.md:524` ("last edited 2026-07-07", "the table was empty") | OK |
| 07-b | Articles rewritten, 4 added, no title-only answers; golden set loaded, 22/22 with 0 leaks; 2 refusals, answers mostly 200–900 characters (D536, backlog) | D536; `backlog.md:524` STEP 1 | OK |
| 07-c | Voyage `voyage-3.5` | `backend/app/services/knowledge/embeddings.py:15` | OK |
| 07-d | `VECTOR_TOP_N = 8`, `RRF_K = 60`, `VECTOR_SIMILARITY_FLOOR = 0.45`, quoted fusion line | `retrieval.py:50,51,54,283`, identical | OK |
| 07-e | Floor calibrated on 24 real and 5 off-topic questions; any embedding failure falls back to text | D537 | OK |
| 07-f | 0 refusals, right article first on all 24, off-topic still refused, 22/22 0 leaks, 114 knowledge tests (D537, backlog) | D537; `backlog.md:524` STEP 2 | OK |
| 07-g | D538: sign-in, 30 an hour; 1,000 a day counted from the query log; text fallback; 300 characters; abuse alerts | D538; `main.py:106-107`; `retrieval.py:58`; `schemas/knowledge.py:12` | OK |
| 07-h | No model writes the answer | `answer.py` (deterministic composer); `backend/app` Anthropic call sites (see README refresh) | OK |
| 07-i | 7 tests in `test_knowledge_hybrid_path.py` (`0cd7e3ce`), Voyage never called, covering the four listed behaviours | `backend/tests/test_knowledge_hybrid_path.py:1-7,105-248` (7 `def test_`) | OK |
| 07-j | The 24-question run was not saved as a file; recorded golden evals ran text-only | no run file in `docs/`; LIMITATIONS and `hybrid-retrieval.md` | OK |

## 08 — The support agent

| # | Claim | Where checked | Result |
|---|---|---|---|
| 08-a | Claude Haiku, ten read-only tools, each locked to the one case | `services/agents/__init__.py:5` (`claude-haiku-5-5`); `services/agents/tools.py` (10 tool functions, each resolving the run's own complaint) | OK |
| 08-b | Proposes, a person approves; never suspends or moves money; exception: a confirmed missed pickup gives an undoable Zelbi credit | D578 (3), (10); D580 (Q1, credit never cash) | OK |
| 08-c | Text inside a case is information, never instructions | `services/agents/support.py:80` | OK |
| 08-d | Every failure path hands the case to a person | `services/agents/runner.py` docstring, "Fail-safe" | OK |
| 08-e | Daily spending cap, alerts at 80% and 100% | `services/agents/spend.py:4,55-67`; D578 (8) | OK |
| 08-f | Leak guard on the one user-visible line | `services/agents/leak_guard.py:1-15` | OK |
| 08-g | Hour 23: undoable decisions only; deadline alerts involve no AI | D578 (5), (6) | OK |
| 08-h | 15 seeded cases with a written answer key | `docs/agents/test-cases/agent-test-cases-2026-10-08.md` (cases 1–15) | OK |
| 08-i | Run 1 (Oct 8): 4 of 10, 1 partial, 5 handed back; the four quoted reasons; $0.037 | `run-1-results-2026-10-08.md` Summary ($0.0370) | OK |
| 08-j | Run 2 (Oct 8): 9 of 10, $0.028; miss "rude in person"; case 1 "stronger than the key" (hide and pause) | `run-2-results-2026-10-08.md` ($0.0278) | OK |
| 08-k | Run 3 (Oct 9, new missed-pickup rule): 4 of 4, $0.012 | `run-3-results-2026-10-09.md` ($0.0118, D580 cases) | OK |
| 08-l | 275 agent tests against a fake model | `cat backend/tests/agents/*.py \| grep -cE '^(async )?def test_'` → 275; `tests/agents/fake_model.py` | OK |

## 09 — A security pass before submitting to Apple

| # | Claim | Where checked | Result |
|---|---|---|---|
| 09-a | A giver can confirm a collection or a missed pickup only once the "did they collect it?" question is due: three hours after the pickup window ends, moved into 9 AM–9 PM local | D588 ("only after a booked pickup's ask time"); `backend/app/services/collect_ask.py:12-41` (`COLLECT_ASK_DELAY = timedelta(hours=3)`, 9:00 and 21:00 bounds, past 9 PM moves to 9 AM next day); `claims.py:195-201` refuses before it | OK |
| 09-b | Stored photo addresses must be the user's own objects; deletes touch only the owner's folder | D588 | OK |
| 09-c | The agent fetches photos without following redirects | D588 ("fetches only R2 objects without redirects") | OK |
| 09-d | Admin push-device route requires an admin | D588 | OK |
| 09-e | Cancelled and missed claims show only the approximate point | D588 | OK |
| 09-f | Rate limits on payments, messages, listing creation, completion uploads, signed-out browsing; IP limiter keys on the one header the edge sets | D588; `backend/app/utils/client_ip.py:1-29` (`X-Real-IP`) | OK |
| 09-g | API docs off in production; a second batch for the admin dashboard followed | D588 | OK |
| 09-h | Done before App Store submission | D588 2026-10-13; first submission 2026-10-19 (`backlog.md:121`) | OK |

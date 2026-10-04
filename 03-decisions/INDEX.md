# Decision records — index

Forty-eight entries selected from the 564 in the private decision log at
`8875721`, grouped by theme. Each is copied **verbatim**, with no edits.

The count is verifiable: every line that opens a `D<n>` entry — including
list-item and struck-through entries — yields 564 distinct decisions, highest
`D574`. The command is in
[`../verification/repo-metrics-2026-10-03.md`](../verification/repo-metrics-2026-10-03.md).

**Correction.** The September version of this page said "406 distinct
decisions" from "parsing every `D<n>` entry". That figure reproduces exactly at
`3413d028`, but only by counting entries that open a line as `D<n>` or
`**D<n>` — it missed 37 list-item entries and 8 struck-through ones. The
inclusive count at that commit was 435. The metrics file shows both commands.

Read as: **the question → the ruling → what shipped.**

---

## money — the claim-fee lifecycle

| D | The question | The ruling | What shipped |
|---|---|---|---|
| [D23](money/D23.md) | What happens to money at each terminal claim transition? | Per-event rules rather than one blanket policy | The capture / void / forfeit branches of the money path |
| [D207](money/D207.md) | What happens when the giver doesn't show? | Symmetric handling designed, then deferred — no event records it | A named gap, not a silent one |
| [D211](money/D211.md) | When does auto-capture fire? | On a timer after the scheduled pickup | The post-window sweeper |
| [D212](money/D212.md) | What protects against an authorization expiring? | Protection at the booking gate, not a backstop sweep | The derived booking ceiling |
| [D217](money/D217.md) | A hold lapses with no pickup — capture or cancel? | **Cancel, never capture.** Void first, write cancelled after | Retired in favour of D218's prevention |
| [D218](money/D218.md) | How far ahead may a pickup be booked? | A duration *derived from the hold's own lifetime*, not a calendar count | The booking validator |
| [D261](money/D261.md) | Is the sweeper's "underfunded loop" a bug? | **No.** Investigated and ruled not a defect | Nothing — the finding is the output |
| [D305](money/D305.md) | Should the native wallet own checkout? | No — a first-party checkout screen; the wallet sits behind it | The checkout screen |
| [D306](money/D306.md) | Are D305's technical premises right? | Two were wrong; corrected in place | Route and copy settled |
| [D317](money/D317.md) | How is consent to auto-capture recorded? | Against the claim, with wording version and timestamp | The consent columns |
| [D319](money/D319.md) | When is consent stamped? | **At the tap, never at mount** | The separate idempotent accept endpoint |
| [D324](money/D324.md) | How is an upheld dispute refunded? | Through the provider, as part of resolve — never by hand | The refund path, refund before ruling |
| [D533](money/D533.md) | How does a dispute start? | **By email to support** — no app screen files one | The in-app filing route later removed as dead code |

## trust — reputation, strikes, blocking, message guard

| D | The question | The ruling | What shipped |
|---|---|---|---|
| [D21](trust/D21.md) | Escalating suspension ladder for no-shows? | No — a single-tier punctuated rule; the fee is the deterrent | The strike service |
| [D182](trust/D182.md) | How should trust be scored? | Flat deductions, first infraction free, infractions heal | The rebuilt model + a backfill |
| [D183](trust/D183.md) | What did the rebuild replace? | An explicit record of every retired rule | The record itself |
| [D225](trust/D225.md) | New module or extend the existing engine? | **Extend it, at the one choke point** | The universal send interceptor |
| [D226](trust/D226.md) | Per-message model for scam detection? | **No** — regex and keyword only, to bound latency and cost | The rule engine |
| [D232](trust/D232.md) | What does a blocked message return? | A category taxonomy, so the client can respond specifically | The 400 body |
| [D264](trust/D264.md) | Keep the GPS-spam rule? | Retire it; replace with a location-free tempo guard | Rule deleted, tempo guard added |
| [D270](trust/D270.md) | Keep the new-account rule? | **Delete, not disable** | Rule removed outright |
| [D272](trust/D272.md) | Hide a suspicious listing at post time? | Never | Post-time hiding removed |
| [D299](trust/D299.md) | Is trust granted or earned? | Earned per handoff on a signed scale; every score carries a word | The rebuilt rings and descriptors |
| [D318](trust/D318.md) | Does blocking cost the picker money? | **Never** — no fee, no strike, whatever the timing | The block cancel path |
| [D542](trust/D542.md) | What earns a first-giveaway credit, and what stops it being farmed? | Only a completed handoff, once per person; **unspendable until the iPhone passes Apple DeviceCheck** | The credit service and the DeviceCheck gate |
| [D544](trust/D544.md) | When does a referral pay the referrer? | Only on the friend's first qualifying donation; matching cards or one iPhone for two friends earn nothing | The referral credit rules |

## privacy — location and data

| D | The question | The ruling | What shipped |
|---|---|---|---|
| [D125](privacy/D125.md) | How is a listing shown on a public map? | An approximate point, stable per listing | The approximate-point generator |
| [D137](privacy/D137.md) | What does the map surface show? | Approximate location with a vicinity circle | The map popup |
| [D215](privacy/D215.md) | Hard delete or soft delete? | Soft, with anonymisation; hard delete breaks record links | The deletion endpoint |
| [D320](privacy/D320.md) | When do true coordinates cross? | **Only at authorization** — the paywall seam | The claim response gate |
| [D321](privacy/D321.md) | What does a stranger's profile show? | The approximate point, matching every feed query | The by-user endpoint override |
| [D322](privacy/D322.md) | Does a blocked party keep their receipt? | Yes — minus the address. A receipt is a record | The receipt filter |
| [D323](privacy/D323.md) | The fuzzing was reversible. Now what? | Key it with a server secret **and recompute every stored point** | The HMAC derivation + a 127-row recompute |

## ai — the vision pipeline, Help search, and their scope

| D | The question | The ruling | What shipped |
|---|---|---|---|
| [D18](ai/D18.md) | How does the model's output reach the user? | Two options, A/B, user picks and edits | The structured listing flow |
| [D87](ai/D87.md) | The model hallucinates brands | Recorded as a known failure mode | The constraint work that followed |
| [D122](ai/D122.md) | Do some categories need more photos? | Yes — enforced at launch for a named set | The photo gate |
| D213 — withheld from the public repository; available on request. |
| [D438](ai/D438.md) | How is the photo gate voiced? | One voice, the camera pill — implements D122 | The capture screen |
| [D440](ai/D440.md) | Cached analysis skips the beat? | No — it still plays | The AI screen timing |
| [D538](ai/D538.md) | How is paid Help search kept from running up the bill? | Signed-in only, 30 an hour; **1,000 embedded questions a day, then text-only**; alerts at 80% and 100% | The daily ceiling and its alerts |

## ops — observability, limits, auth, jobs

| D | The question | The ruling | What shipped |
|---|---|---|---|
| [D198](ops/D198.md) | One notification lane or two? | Two — instant and daily digest | The two-lane policy |
| [D200](ops/D200.md) | How are daily jobs scheduled? | A single runner module | The daily runner |
| [D238](ops/D238.md) | How often does listing expiry run? | Every ten minutes — a window-bounded query must run at least as often as its window is wide | The frequent-jobs cron |
| [D274](ops/D274.md) | Logs or an error reporter? | An error reporter, superseding the log-only ruling | Reporting on the API and both crons |
| [D275](ops/D275.md) | Where does rate limiting live? | In-process, on the model-calling router | The rate-limit module |
| [D276](ops/D276.md) | May the primary auth client use PKCE? | **Never** — the runtime has no WebCrypto | PKCE split to an OAuth-only client |
| [D277](ops/D277.md) | May a background poll end a session? | **Never** | Polls gated on a restored session |
| [D442](ops/D442.md) | Is a rate-limit hit a user-facing bug? | No — an admin signal. The ceilings stay | Ceilings kept, reads unmetered |
| [D444](ops/D444.md) | Does the claim depend on the arrival ping? | No — the ping is a fast lane, not the engine | The arrival path |

---

## How these 48 were chosen

Selected by theme against the five areas the résumé makes claims about — money,
trust, privacy, AI, and operations — with three further filters:

1. **The ruling has a consequence in shipped code**, so a reviewer can follow it
   into [`../code/`](../code/).
2. **Decisions that reversed something are preferred over decisions that
   confirmed something.** D183 (what the rebuild retired), D217 (superseded by
   D218), D264 and D270 (rules deleted), D306 (correcting D305's premises) are
   here because a log that only records wins is a marketing document.
3. **Rulings against building something are included deliberately** — D226
   (no per-message model), D207 (deferred, with the blocker named). Deciding not
   to build is the harder half of the record.

Per-entry reasons for all 48 are in [`../MANIFEST.md`](../MANIFEST.md) for
review at the gate.

**Not selected, and worth saying:** the log is dominated by UI and copy rulings —
panel heights, corner radii, button labels, animation timing. They are real
decisions and they are most of the 564, but they prove craft in a domain the
résumé does not claim, so they are out.

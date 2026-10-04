# Credits gated by Apple DeviceCheck

Code and tests: [`../code/credits_devicecheck/`](../code/credits_devicecheck/).
Line numbers are at Zelbi `8875721`. Governing decisions published here:
[`D542`](../03-decisions/trust/D542.md), [`D544`](../03-decisions/trust/D544.md);
the rest of the credit series (D539, D543, D545, D549) is cited by number.

## The problem

A giver's first completed giveaway earns a credit worth one free pickup
(`credit_service.py:1-8, 55-117`). An invite code earns the friend one too. A
credit that anyone can earn by making a new account is a money printer: sign up
again, give something away to yourself, collect. Email checks catch the lazy
version. They do not catch a second account on the same phone.

## The rule

**A giveaway or invite credit cannot be spent until the iPhone that earned it
passes Apple DeviceCheck** — one credit of each kind per iPhone, not per
account. The spend gate is a single SQL predicate on credit lookup
(`routers/claims.py:436-440`, excerpt — the router is not published whole):

```python
or_(Credit.kind.notin_(("giveaway", "invite")), Credit.device_checked_at.isnot(None)),
```

## How the check works

DeviceCheck gives every app two bits per physical device, stored by Apple, that
survive a new account. Zelbi uses `bit0` for "this iPhone has earned a giveaway
credit" and `bit1` for "this iPhone has used a friend's code".

1. **The phone asks for a token.** A 20-line Swift module wraps `DCDevice`
   (`ios_ZelbiDeviceCheckModule.swift`): `isSupported` and `generateToken`,
   base64 with no line breaks. That is all it does — there is no logic on the
   phone to trust or bypass.
2. **The app only asks when the server says so.** On sign-in and each return to
   the foreground, `ensureDeviceCheck` reads `/auth/me`, and only if a credit is
   waiting does it generate a token and post it (`mobile_utils_deviceCheck.ts:33-61`).
   One check in flight at a time.
3. **The server asks Apple, under a lock.** `POST /users/me/device-check`
   (`routers/users.py:530-596`, excerpt) takes a Postgres advisory lock, re-reads
   the pending credit `FOR UPDATE`, and queries the device's bits
   (`devicecheck_service.py:165-182`).
4. **Already set → refused.** The credit is stamped `device_check_refused_at`,
   stays as a record but can never be spent, and an abuse signal goes to the
   operator console (`users.py:563-574`; `credit_service.py:138+`).
5. **Not set → set it, then pass.** Both bits are written every time — the one
   being claimed set, the other passed back unchanged — because Apple's
   documentation does not say whether an omitted bit is kept or cleared
   (`devicecheck_service.py:185-189`; `users.py:576-596`). One retry on failure,
   then "unavailable" with nothing written.

**Talking to Apple** (`devicecheck_service.py`): an ES256 JWT signed with the
team's DeviceCheck key, cached for 50 minutes and re-minted once if Apple says it
expired (:87-105, :151-153). The key and key id come from the environment; if
either is missing the client refuses before any network call (:82-84). The device
token, the JWT and the key are never logged (:7-8; `users.py:525-527`).

## Why the lock matters

Apple offers no compare-and-set between reading and writing the bits. Two
accounts on one iPhone, checking at the same moment, could both read "unset" and
both pass. The advisory lock serialises every check through the one database
both backends share (`users.py:500-503`). It closes the race on Zelbi's side
only — and the comment says exactly that.

## Tests

63 `def test_` functions across `test_credits_devicecheck.py` (23),
`test_devicecheck_service.py` (17) and `test_credits_giveaway.py` (23). The
Apple client tests generate their own ES256 key at runtime; no real key is in
the repository.

## Honest limits

- **Referral credits are not gated.** Only `giveaway` and `invite` credits wait
  for the check; a `referral` credit spends without it (`claims.py:439`).
- **iOS only, and not in the simulator.** `DCDevice` is unsupported there; the
  app reports `unsupported` and the credit simply stays unspendable on that
  device.
- **Per-device, not per-person.** Someone with two iPhones can earn twice. That
  is the stated scope of the rule, not an oversight.
- **A development-only reset route** clears the bits for device walks; it answers
  404 against Apple's production host (`users.py:599-609`).
- **Stale docstring.** `devicecheck_service.py:3` still says "no route or caller
  yet"; both exist.

## What is never claimed

That every credit is device-gated, that DeviceCheck identifies a person, or that
the Swift module does more than hand Apple's token to the server.

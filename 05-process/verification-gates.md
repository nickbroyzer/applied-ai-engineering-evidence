# Verification gates — what counts as done

The rules below come from [`behavioral-rulebook.md`](behavioral-rulebook.md).
Together they define a single stance: **a claim is worth what its source is
worth, and an unsourced claim is worth nothing.**

## The ladder

Four rules stack, each closing a hole the one above it left.

### U1 — PRIME DIRECTIVE (overrides everything)

> NEVER GUESS — ALWAYS VERIFY. Do not state anything as fact unless verified in
> this session. If you cannot verify it yourself, use the tools available […]
> If none of those can verify it either, say "I can't verify this" BEFORE
> responding. This overrides all other rules.

### U4 — NEVER INVENT / NEVER GUESS

Every fact, identifier, status, qualifier, framing, commit hash, field name,
endpoint, file path or implied conclusion needs one of three sources: read from
a document or tool output **this session**; the operator's verbatim message
**this session**; or the operator's explicit instruction **this session**.
Absent all three, the answer is `[UNKNOWN]` plus the exact command that would
resolve it.

Two clauses make it enforceable rather than aspirational:

- **Status words** — passed, failed, blocked, partial, complete, works, broken —
  must be followed by a backtick-quoted source line.
- **A forbidden-phrase list** fires the hook on sight: *likely, probably, should
  be, presumably, appears to, seems to, could be, might be, this implies, we can
  assume, it follows that*, and any "either X or Y" enumeration of unverified
  causes.

The rule's own dated note records why it was expanded on 2026-05-13: one session
broke the prior, narrower version **four times** — on qualifiers, status
framings, editorial sentences, and unverified-cause enumeration. The rule got
wider because the failures did.

### U26 — READ HONESTY

U4 checks the *shape* of a citation. It cannot check that the cited act
occurred — a fabricated source tag passes it. U26 closes that hole, and its
notes say so explicitly.

- **Before:** never assert an incapacity you have not tested. Do not write that
  you cannot read, access, see, reach or check something until you have tried it
  with a tool you already hold this session. Only after an attempt returns an
  error may the limit be stated, and the statement must quote the actual failure.
- **After:** when a read returns empty, blank, truncated, unreadable or absent,
  say so *in those words* and stop. Never describe what the input contained, and
  never let a conclusion reached by other means borrow the read's provenance.
- **Operator-source:** the operator's verbatim statement is a source and
  outranks the assistant's inference. When he says he performed an action, that
  **is** the verification.

That last clause was added mid-session after a live failure: the assistant asked
the operator to re-paste a document he had already said he replaced.

### U27 — IDENTIFIER SOURCE GATE

No executable line may contain a path, module name, package name or command flag
unless that exact identifier has a source this session — a real terminal dump,
tool result, listing or help print, or the operator's verbatim message. *Recall
is never a source; confidence is not a trigger.* When the source is missing, the
read joins the **same block** as the use, so there is no extra round trip.

Field evidence in the rule's own notes: ~10 invented identifiers in one session
— an assumed CLI path under a dependency directory, an assumed database driver,
an invented git flag, an unquoted shell glob — with three of those failure
classes already written down in earlier sessions' lessons files.

## The done gate

### U6 — VERIFICATION GATE

> Never say "this should fix it" or declare done without verification. Say
> "Here's the change — verify by [specific method]." Frontend = browser check.
> Backend = curl. Architecture = Plan mode review.

In practice on Zelbi the methods were: a device walk on a physical iPhone or the
simulator for anything the user sees; `curl` or the pytest dependency-override
fixture for endpoints; a SQL read for anything claimed about stored rows; the
Stripe CLI for the money path. Mobile UI in particular was never "done" on a
screenshot — a still frame cannot show animation, keyboard transitions,
gestures, scroll behaviour, or any flow spanning more than one screen, and the
project's instructions say so in as many words.

## How this repository obeys its own rule

Every number here traces to
[`../verification/repo-metrics-2026-09-03.md`](../verification/repo-metrics-2026-09-03.md)
or [`../verification/pytest-summary-2026-09-03.txt`](../verification/pytest-summary-2026-09-03.txt),
both of which carry the command that produced them. Where a figure could not be
reproduced, [`../LIMITATIONS.md`](../LIMITATIONS.md) says so rather than
repeating it.

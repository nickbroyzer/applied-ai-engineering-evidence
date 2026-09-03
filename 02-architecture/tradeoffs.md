# Trade-offs — the calls, and what they cost

Every item here is a decision I made knowing what it gave up. Listing them is
cheaper than being asked about them.

## No CI

**The call:** the backend suite runs manually at session close. There is no
workflow file in the repository at this commit; `.github/` does not exist.

**The cost:** it is exactly as reliable as I am. The recorded baseline drifted —
a lessons entry records a stale "15 failed" figure that measured 39 at clean HEAD
in one session, later corrected to zero. A suite whose baseline you have to
remember is a suite you are not really running.

**Why:** for a single developer with no branch protection and nobody else
pushing, CI's first-order benefit — stopping someone else's broken change —
does not exist yet, and its cost is real setup time against a launch. That
calculus flips the moment a second person commits, and it flips *before* that if
the manual habit slips again.

**What is never claimed:** "every change was test-gated." It is a prohibited
phrasing, and the honest sentence is "751 backend tests, green from a clean
checkout at the audited commit."

## Client-trusted arrival confirmation

**The call:** the arrival endpoint accepts no coordinates. The client reports
that the picker arrived; the server takes its word
([`D444`](../03-decisions/ops/D444.md), [`D230`](../03-decisions/privacy/)).

**The cost:** a picker can report arrival without arriving.

**Why:** server-verified arrival needs always-on location permission, which is a
large ask at exactly the wrong moment and a meaningful privacy cost to every
honest user, to defend against a case the fee and the strike model already
penalise. The ping is a fast lane, not the engine — the claim never depends on
it, and a no-show is still resolvable by the giver marking it.

**What is never claimed:** "server-verified geofence", or "geofenced arrival".
The correct phrase is *client-reported arrival confirmation*.

## Read-then-write capture guards

**The call:** the double-capture guards read the current state and then write,
in Python. There are zero row locks in the backend.

**The cost:** no guarantee under true concurrency, and no test proving behaviour
under simultaneous double-capture.

**Why:** the realistic concurrency here is a webhook and a ten-minute sweep
touching the same claim, which the adopt-don't-recapture path handles, not
thousands of racing writers. Row locks against a transaction-mode pooler are
their own source of production incidents.

**What is never claimed:** "money can never be taken twice or lost."

## Lexical retrieval instead of embeddings

**The call:** the knowledge system uses PostgreSQL full-text search with a
keyword fallback. No embeddings, no vector store.

**The cost:** it misses paraphrases that a semantic index would catch. The
mitigation is deliberate — a keyword fallback fills the slots full-text search
leaves empty, and anything that does not clear a relevance floor is refused
rather than answered weakly.

**Why:** the failure mode being defended against is a **confidently wrong policy
answer**. A refusal that routes to support costs one email. Retrieval that is
deterministic, inspectable, offline and constrained by SQL visibility rules is
worth more here than recall. See [`ai-boundary.md`](ai-boundary.md).

**What is never claimed:** RAG, vectors, embeddings, or LLM-based policy
answering.

## In-process rate limiting

**The call:** rate limits are held in process, per route
([`D275`](../03-decisions/ops/D275.md)).

**The cost:** limits are per-process, so they do not hold across replicas.

**Why:** there is one API process. Shared-store rate limiting before there is a
second process to share with is infrastructure built for an imagined problem.

**What it already cost once:** a limit mounted at router level applies to every
route on that router, reads included. A ceiling sized for claim creation locked
a real user out of reading their own receipts within twenty minutes, and the
empty list rendered as "Nothing here yet" over their own data — two wrong
theories were chased before the status code was read. The ceiling now sits on
writes only. An empty list in the app is a status code, not a mystery.

## Soft delete instead of hard delete

**The call:** account deletion marks the account deleted, ends the session,
blocks re-login and anonymises the public identity, retaining de-identified
records needed for integrity ([`D215`](../03-decisions/privacy/D215.md)).

**The cost:** data remains, in de-identified form.

**Why:** hard delete breaks claim, dispute and payment record links. It is also
permitted to retain records required for legal or financial reasons. Soft delete
with anonymisation is the honest version of what a marketplace can actually do.

**What is never claimed:** a "salted hash" of the retained email. It is an
unsalted one-way fingerprint, and it is described that way.

## Withholding the scam rule table

**The call:** the detection patterns are removed from the published copy of the
message guard; the normalizer and the dispatcher framework are intact.

**The cost:** a reviewer cannot audit the patterns.

**Why:** publishing the alternation list publishes the evasion recipe. The
normalizer is where the engineering is anyway — see
[`../01-product-logic/trust-and-safety-design.md`](../01-product-logic/trust-and-safety-design.md).

## Legal and compliance work

A ten-section legal and privacy audit was run across the platform on 2026-08-04,
producing roughly four thousand lines of findings, every section marked evidence
complete. Versioned terms acceptance with an 18-plus self-attestation, account
deletion, a country gate and five hosted legal pages were built from those
findings. The audit documents and their evidence files are **not** in this
repository — that is this paragraph's whole job.

Stated plainly: counsel review is outstanding, the operating entity is unnamed,
the country gate is built but ineffective in production until its data source is
configured, and the legal pages carry placeholder limitations. "All launch gates
closed" is not a claim made here.

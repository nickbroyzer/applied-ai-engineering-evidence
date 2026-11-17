# The AI boundary

Three systems in this product touch the words "AI". Two let a model write, one
does not, and the interesting part is *why*.

Every model call site in the backend, by `grep -rn -i "anthropic\|voyage" backend/app`
at Zelbi `4772472b`:

| Call site | Provider and model | What it does |
|---|---|---|
| `services/ai_service.py:170`, `analyze_listing_image` | Anthropic, `claude-sonnet-5-5` (`LISTING_AI_MODEL` in config) | The vision listing call. One photo in; two listing drafts, a confidence label, a soft-item flag and, in the same call, a restricted-item flag judged against the published prohibited-items rules (D620) out |
| `services/agents/runner.py:157`, the support agent's tool loop | Anthropic, `claude-haiku-5-5` (`AGENT_MODEL`) | Up to 12 model calls per trust-and-safety report, with ten read-only tools; ends in a proposal for a person to approve, or a hand-off (D578) |
| `services/knowledge/embeddings.py:30`, `embed_texts` | Voyage, `voyage-3.5` | Embeds policy passages at ingestion (`ingestion.py:431`) and the question at search time (`retrieval.py:214`). Finds text; writes nothing |

There is no other model call. The restricted-item check is not a separate call:
it is three more keys in the vision call's JSON.

| | Vision listing pipeline | Support agent | Knowledge / policy answering |
|---|---|---|---|
| A model writes output | yes — one multimodal call | yes — a proposed decision, and at most one short line a user can see, checked by a leak guard | **no** |
| Embeddings / vectors | no | no (its policy-search tool uses Help's retrieval) | yes — one query embedding to *find* text, optional |
| External API at request time | yes | yes, per queued report, under a daily spending cap | one embedding call; **none** without a key or past the daily ceiling |
| Failure mode if wrong | a bad listing draft the user edits, or a photo wrongly stopped at the camera | a wrong proposal a person rejects; every failure hands the case to a person | a **wrong policy answer** |
| Determinism of the answer | not required | not required; a person decides (one timed exception) | required |
| Tests (`def test_`) | 28 | 275 | 116 |

Line numbers in this page are at Zelbi `4772472b`.

## Why Claude for vision

Turning a photo of a thing into a title, a description and a category is a task
with no closed-form answer and enormous input variety. There is no rule set for
"what is this object", and a wrong answer costs almost nothing: the user is
shown **two drafts** and edits the one they prefer before posting. The model
proposes; the person disposes.

That is the whole justification. Where the human is in the loop and the cost of
being wrong is an edit, a model is the right tool.

The same call also judges the item against the published prohibited-items
rules (D620). A restricted item cannot go past the camera. A missing answer
counts as not restricted, so a model that leaves the keys out never blocks a
giver, and a reason without a block is discarded.

## Why a model for the support agent

Reviewing a trust-and-safety report means reading a listing, its photos, a
message thread and a history, then weighing them against policy. That is
judgement over messy input, like the vision task, and the same rule applies: the
model proposes and a person decides, with one exception: after 23 hours with
no action it may carry out a decision that can be undone. The agent reads
through ten read-only tools locked to the one case, never moves money, and
never suspends anyone. Every error, refusal or malformed proposal hands the case to a person. The one
piece of its text a user can see, a single line when a listing is removed, goes
through a leak guard that fails closed. The scored rounds are in
[`../06-case-studies/08-the-support-agent-4-of-10-then-9-of-10-then-4-of-4.md`](../06-case-studies/08-the-support-agent-4-of-10-then-9-of-10-then-4-of-4.md).

## Why deterministic for Help

Policy answering is the mirror image. A wrong answer about the claim fee, about
what happens to a hold, or about what data is retained on account deletion is
not a bad draft — it is a **false statement about money or privacy, made by the
platform, to a user, at scale**, with nobody in the loop to catch it.

So no model writes a policy answer. Since Session 463 a model does help *find*
the text: retrieval fuses PostgreSQL full-text search (with a keyword fallback)
with one Voyage embedding of the question, by reciprocal rank, and falls back to
text alone when there is no key or the daily ceiling is reached — see
[`hybrid-retrieval.md`](hybrid-retrieval.md). That is a deliberate split: an
embedding can only change *which* passages are considered, never *what* is
said. The answer is composed from retrieved text by code; anything that does not
clear a relevance floor is refused with a support route. The refusal wording
never confirms that a hidden rule exists.

Two structural properties do the safety work:

- **Visibility is a SQL predicate, not a post-filter — on every path.** A
  public query *physically cannot rank* a restricted chunk, by words or by
  meaning, because the same restriction is in the `WHERE` clause of the
  full-text, keyword and vector queries. Post-filtering means the wrong row was retrieved and then
  dropped — one bug away from being returned.
- **Every guarantee is re-asserted on the way out.** The SQL already guarantees
  no internal document and no deny-listed decision; the code checks again on the
  results and again on the assembled answer, and fails closed into a refusal on
  any violation.

The text-only half runs, offline, on a reviewer's machine:
[`../runnable/knowledge-eval/`](../runnable/knowledge-eval/). That package
records something worth reading — three separate attempts to induce a leak
through the eval contract, each of which the composer converted into a refusal
rather than a leak.

## The five-stage model boundary

The vision call's output is untrusted input. Five stages stand between it and
the database (excerpts in [`../code/ai_service/EXCERPTS.md`](../code/ai_service/EXCERPTS.md)):

1. **Fence-tolerant JSON extraction.** Models wrap JSON in markdown fences
   sometimes and not others. The parser strips a leading fence line and a
   trailing fence rather than failing on formatting.
2. **A type check.** Valid JSON that parses to a list or a string is rejected
   before anything reads a field off it.
3. **Schema validation.** A Pydantic model validates the whole structure.
   Anything that does not match raises a typed service error carrying the
   validation message.
4. **An independent allowlist re-check** — and this is the stage worth arguing
   for. The category is *already* constrained by the schema. It is checked again
   against a ten-value allowlist, **on both options**, because the schema
   describes shape and the allowlist describes permitted values. A model that
   returns a plausible category outside the product's set produces a
   well-formed, schema-valid, wrong row. Stage 4 exists because stage 3 cannot
   see that.
5. **Provider-safe error mapping.** Every internal failure becomes a typed
   error, and the route maps it to a generic HTTP 502. Provider messages,
   parse fragments and internal detail do not reach the client.

**Per-request object-key authorization** sits in front of all five: a request
naming an object key not owned by the caller is refused with 403 before any
model call happens. Otherwise the endpoint is a paid oracle over other people's
uploads.

**Logging is structured.** Success logs latency, model id, categories,
confidence and title lengths; failures log their type. That is what makes a
model boundary debuggable after the fact rather than by re-running it.

## Tests

28 backend tests across six files at `4772472b`, provider mocked: four on the
service, one on the route, two on object-key ownership, three on the item-type
flag, thirteen on the restricted-item flag (`test_ai_restricted.py`) and five on
the short title (`test_ai_short_title.py`). At `8875721` there were 10, the
first four files. The failure cases covered include a provider failure, an
out-of-range confidence, an out-of-allowlist category (stage 4) and a foreign
object key (403).

In September there were 21. The other 11 tested the image-readability endpoint,
which had no mobile caller and was deleted as dead code on 2026-10-03 (commit
`b6ced95`). The storage-fetch failure and the 502 mapping were only ever tested
on that path, and the fence-tolerant parse (stage 1) has no dedicated test.

## What this pipeline does not have

Named plainly, because the absence is the honest part: **no retry policy of its
own, no explicit timeout, no circuit breaker, no model routing, no token
accounting, no prompt versioning, no structured-output API, no tool use, no
streaming.** The client is built with the SDK's defaults, so the SDK's own two
retries and its default timeout apply. Earlier versions of this page said "no
retries"; that was never right.

Any of those would be a reasonable next step. None of them is claimed for the
vision call. The support agent is different: it uses tool use, records tokens
and cost for every model call and tool call, turns the SDK's retries off, and
runs under a daily spending cap. Streaming and per-task model selection exist in
the construction-company platform described in
[`system-overview.md`](system-overview.md), not here.

## The model call that was removed

A second endpoint checked whether an uploaded image was readable, using the same
discipline and a two-key schema. It never had a mobile caller, and it was
deleted with its tests on 2026-10-03 (`b6ced95`). At `8875721` the vision
listing call was the only generating model call in the product. Since then the
support agent's tool loop has become the second; the table at the top lists
both.

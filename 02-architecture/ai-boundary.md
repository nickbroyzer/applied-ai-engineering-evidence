# The AI boundary

Two systems in this product touch the words "AI", and they made opposite calls.
The interesting part is *why*.

| | Vision listing pipeline | Knowledge / policy answering |
|---|---|---|
| Calls a model | yes — one multimodal call | **no** |
| Embeddings / vectors | no | no |
| External API at request time | yes | **none** |
| Failure mode if wrong | a bad listing draft the user edits | a **wrong policy answer** |
| Determinism | not required | required |
| Tests | 21 | 108 |

## Why Claude for vision

Turning a photo of a thing into a title, a description and a category is a task
with no closed-form answer and enormous input variety. There is no rule set for
"what is this object", and a wrong answer costs almost nothing: the user is
shown **two drafts** and edits the one they prefer before posting. The model
proposes; the person disposes.

That is the whole justification. Where the human is in the loop and the cost of
being wrong is an edit, a model is the right tool.

## Why deterministic for Help

Policy answering is the mirror image. A wrong answer about the claim fee, about
what happens to a hold, or about what data is retained on account deletion is
not a bad draft — it is a **false statement about money or privacy, made by the
platform, to a user, at scale**, with nobody in the loop to catch it.

So the knowledge system calls no model. Retrieval is PostgreSQL full-text search
with a keyword fallback; the answer is composed from retrieved text by code;
anything that does not clear a relevance floor is refused with a support route.
The refusal wording never confirms that a hidden rule exists.

Two structural properties do the safety work:

- **Visibility is a SQL predicate, not a post-filter.** A public query
  *physically cannot rank* a restricted chunk, because the restriction is in the
  `WHERE` clause. Post-filtering means the wrong row was retrieved and then
  dropped — one bug away from being returned.
- **Every guarantee is re-asserted on the way out.** The SQL already guarantees
  no internal document and no deny-listed decision; the code checks again on the
  results and again on the assembled answer, and fails closed into a refusal on
  any violation.

The whole thing runs, offline, on a reviewer's machine:
[`../runnable/knowledge-eval/`](../runnable/knowledge-eval/). That package
records something worth reading — three separate attempts to induce a leak
through the eval contract, each of which the composer converted into a refusal
rather than a leak.

## The five-stage model boundary

The vision call's output is untrusted input. Five stages stand between it and
the database ([`../code/ai_service/ai_service.py`](../code/ai_service/ai_service.py)):

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

21 backend tests across four files, provider mocked: eight on the service, six
on the route, four specifically on object-key ownership, three on the item-type
flag. Storage, provider, parsing, schema and authorization failures each have a
case.

## What this pipeline does not have

Named plainly, because the absence is the honest part: **no retries, no explicit
timeout, no circuit breaker, no model routing, no token accounting, no prompt
versioning, no structured-output API, no tool use, no streaming.**

Any of those would be a reasonable next step. None of them is claimed. Streaming
and per-task model selection exist in the construction-company platform
described in [`system-overview.md`](system-overview.md), not here.

## One more model call, and its status

A second endpoint checks whether an uploaded image is readable, using the same
discipline and a two-key schema. It exists on the backend and **has no mobile
caller**. It is not presented as a user-facing production flow.

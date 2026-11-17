# `code/ai_service/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Stage 1: fence-tolerant JSON extraction

`backend/app/services/ai_service.py`, lines 94–112, at `4772472b`. Cited by: 02-architecture/ai-boundary.md.

```python
def _parse_json_from_text(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as first:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m is not None:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError as e:
                raise AIServiceError("Model response is not valid JSON") from e
        raise AIServiceError("Model response is not valid JSON") from first
```

## The vision call

`backend/app/services/ai_service.py`, lines 166–193, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; README.md.

```python
Output only the JSON object. No markdown code fences, no extra commentary."""

        client = Anthropic(api_key=settings.anthropic_api_key)
        try:
            message = client.messages.create(
                model=settings.listing_ai_model,
                thinking={"type": "between_tools"},
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": user_prompt},
                        ],
                    }
                ],
            )
        except Exception as e:
            raise AIServiceError(f"Anthropic API request failed: {e!s}") from e

```

## Stages 2–4, and the restricted-item flag (D620)

`backend/app/services/ai_service.py`, lines 195–226, at `4772472b`. Cited by: 02-architecture/ai-boundary.md.

```python
            b.text
            for b in message.content
            if getattr(b, "type", None) == "text" and hasattr(b, "text")
        ]
        if not text_blocks:
            raise AIServiceError("Model returned no text content to parse as JSON")
        raw_text = "".join(text_blocks)

        data = _parse_json_from_text(raw_text)

        if not isinstance(data, dict):
            raise AIServiceError("Parsed JSON is not an object")

        try:
            result = ListingAIAnalysis.model_validate(data)
        except Exception as e:
            raise AIServiceError(f"Response does not match expected schema: {e!s}") from e

        for option_label, option in (("option_a", result.option_a), ("option_b", result.option_b)):
            if option.category not in ALLOWED_CATEGORIES:
                raise AIServiceError(
                    f"Invalid category {option.category!r} in {option_label}; "
                    "must be one of ALLOWED_CATEGORIES",
                )

        # D620: a reason without a block means nothing; a block keeps its reason short.
        if not result.restricted:
            result.restricted_reason = ""
        else:
            result.restricted_reason = result.restricted_reason.strip()[:80]

        # A missing or over-long short name is not a failure: the rule writes one.
```

## Object-key authorization and the 502 mapping (stage 5)

`backend/app/routers/ai.py`, lines 1–40, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 01-product-logic/private-photo-access.md.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_current_user_detached
from app.models import User
from app.services.ai_service import (
    AIServiceError,
    ListingAIAnalysis,
    analyze_listing_image,
)

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzePhotoRequest(BaseModel):
    object_key: str


def _require_own_object_key(object_key: str, current_user: User) -> None:
    owner_id, _, rest = object_key.partition("/")
    if not rest or owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this object key",
        )


@router.post("/analyze-photo", response_model=ListingAIAnalysis)
def analyze_photo(
    payload: AnalyzePhotoRequest,
    current_user: User = Depends(get_current_user_detached),
) -> ListingAIAnalysis:
    _require_own_object_key(payload.object_key, current_user)
    try:
        return analyze_listing_image(payload.object_key)
    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable",
        )
```

## Support agent: the runner's contract (D578)

`backend/app/services/agents/runner.py`, lines 1–26, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 06-case-studies/08.

```python
"""D578 sections 2, 4.1 and 4.9 (revision 3 runner): the support agent's tool loop.

run() takes a queued agent_runs row and ends it as proposed, handed_off or cancelled (or
superseded, when the report was decided before its proposal was ready). It
never dispatches, executes a decision or touches the timer (groups 7 and 8).

- Up to MAX_STEPS model calls. Before every call it re-runs switches.gate (master switch,
  mode, test or real subject, exclusion, status open, the daily cap); a failed gate cancels
  the run, and a reached cap also sends the cap100 alert.
- Append-only history: each assistant content is appended whole, tool_choice auto, no
  temperature, and the per-model thinking field from pricing.PRICES.
- One agent_steps row per model call and per tool call, with tokens and cost; run totals are
  the sum of its steps.
- D579: a proposal with threat set (rule 15) is carried out at once through execute as the
  undoable pause (no actor, so the run ends auto_executed and the person is told), and Nick
  gets the urgent "Threat found" alert once per run (threat:<run id>). A run that ends this
  way sends no suggestion alert.
- Fail-safe: every error, a refusal or max_tokens stop, a turn with no terminal tool, a
  malformed or disallowed proposal, a policy citation this run's search_policy did not return,
  and MAX_STEPS all end in hand-off. Low credit (402, billing_error, or a 400 about the credit
  balance) hands off as low_credit and sends the credit:<day> alert. Nothing retries: the
  client is built with max_retries=0.
"""
import json
import logging
import time
```

## Support agent: the model call, with every failure handed to a person

`backend/app/services/agents/runner.py`, lines 144–168, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 06-case-studies/08.

```python
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": support.SYSTEM_PROMPT,
            "tools": tools.TOOLS + support.TERMINAL_TOOLS,
            "tool_choice": {"type": "auto"},
            "messages": messages,
        }
        thinking = pricing.PRICES[self.model]["thinking"]
        if thinking is not None:
            kwargs["thinking"] = thinking
        started = time.monotonic()
        try:
            response = self.client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            self.step("model", is_error=True, model_text=f"{exc.status_code} {exc.type}: {exc.message}"[:2000],
                      latency_ms=int((time.monotonic() - started) * 1000))
            if is_low_credit(exc):
                self.low_credit_alert()
                raise _hand_off("low_credit", "Anthropic refused the call for low credit.")
            raise _hand_off("api_error", f"The model call failed ({exc.status_code}).")
        except anthropic.APIError as exc:
            self.step("model", is_error=True, model_text=repr(exc)[:2000],
                      latency_ms=int((time.monotonic() - started) * 1000))
            raise _hand_off("api_error", "The model call failed (connection).")
```

## Support agent: the leak guard on the one user-visible line

`backend/app/services/agents/leak_guard.py`, lines 1–15, at `4772472b`. Cited by: 02-architecture/ai-boundary.md; 06-case-studies/08.

```python
"""D578 sections 2 and 4.6 (revision 3 leak_guard): checks the one piece of agent text a user
can see, the listing-removed line.

check_reply flags:
- a policy path (docs/policy/);
- a decision number (D212 is deny-listed; no D-number belongs in a user's email);
- money: a dollar amount, or refunds, charges, payouts, payments, credits, fees or Stripe
  (the agent never says anything about money);
- a run of RUN_WORDS words copied from CX-only policy text: the rag_index 'cx' chunks in the
  database, which is what search_policy can show the agent, plus docs/policy/cx and
  docs/policy/internal when they are on disk (local runs and the eval; the production image
  is built from backend/ and carries no docs/).

With no protected text from either source the check raises, and guard_user_line falls back:
it fails closed. The runner and the eval share it.
```

## Support agent: the daily spending cap and its 80% and 100% alerts

`backend/app/services/agents/spend.py`, lines 43–70, at `4772472b`. Cited by: 06-case-studies/08; LIMITATIONS.md (AI path).

```python
def check_cap(db: Session, agent: str = "support", now: datetime | None = None) -> bool:
    """True while today's spend is below 100% of the cap. No switch row means no cap to
    spend against, so it fails closed."""
    cap = daily_cap(db, agent)
    if cap is None:
        return False
    return spent_today(db, agent, now) < cap


def cap_alerts(
    db: Session, agent: str = "support", now: datetime | None = None, run_id: UUID | None = None,
) -> str | None:
    """Sends the cap100 alert at 100% or more, else the cap80 alert at 80% or more. Each is
    sent once per agent per UTC day. Returns the kind that applies, or None below 80%."""
    cap = daily_cap(db, agent)
    if cap is None or cap <= 0:
        return None
    spent = spent_today(db, agent, now)
    day = _now(now).strftime("%Y-%m-%d")
    # The Platform health signal keeps its own wording; the alert's is the card's (D624).
    if spent >= cap:
        kind, signal = "cap100", f"The {agent} agent reached its daily cap"
        severity = 7
    elif spent >= cap * Decimal("0.8"):
        kind, signal = "cap80", f"The {agent} agent passed 80% of its daily cap"
        severity = 5
    else:
        return None
```

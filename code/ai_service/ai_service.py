import base64
import json
import logging
import mimetypes
import re
import time
from typing import Literal

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from anthropic import Anthropic

from app.config import settings
from app.constants import ALLOWED_CATEGORIES

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    pass


class ListingAIResult(BaseModel):
    title: str
    description: str
    category: str


class ReadabilityResult(BaseModel):
    readable: bool
    reason: str | None = None


class ListingAIAnalysis(BaseModel):
    option_a: ListingAIResult
    option_b: ListingAIResult
    confidence: Literal["low", "medium", "high"]
    soft_item: bool = False


def _r2_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def _guess_image_media_type(object_key: str) -> str:
    guessed, _ = mimetypes.guess_type(object_key)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


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


def analyze_listing_image(object_key: str) -> ListingAIAnalysis:
    start_time = time.perf_counter()
    try:
        s3 = _r2_s3_client()
        try:
            obj = s3.get_object(
                Bucket=settings.r2_bucket_name,
                Key=object_key,
            )
            image_bytes = obj["Body"].read()
        except (ClientError, BotoCoreError) as e:
            raise AIServiceError(f"R2 object fetch failed: {e!s}") from e

        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        media_type = _guess_image_media_type(object_key)

        allowed = ", ".join(ALLOWED_CATEGORIES)
        user_prompt = f"""You are helping classify a single photo for a free-item giveaway listing.

Generate two listing variants.

For BOTH options, the title must be the item's short recognizable name — 2 to 5 words. KEEP the brand and model when they identify the item (e.g. "LEGO Lamborghini", "Trek Mountain Bike", "Sprite Soda Can"), but DROP condition, size, quantity, packaging, and marketing words (e.g. "LEGO Speed Champions Lamborghini Building Set 280 pcs" becomes "LEGO Lamborghini"; "Beautiful Vintage Oak Rocking Chair in Excellent Condition" becomes "Oak Rocking Chair"). Use your judgment about which words a person would actually use to name the item. Put every other detail — condition, color, material, size, model number, features — in the description, never the title.

- Option A is specific: the description includes all identifiable features visible in the photo (brand, model, color, material, condition).
- Option B is generic: the description is a brief plain sentence any feed scanner would recognize without inspecting details.

Both options MUST agree on category.

Also rate your overall confidence that the photo is identifiable enough for a feed listing. Use exactly one of these three labels:
- "low" — the photo is hard to interpret or the object is ambiguous
- "medium" — the object is identifiable but some details are unclear
- "high" — the object is unambiguous and well-presented

Also decide whether this item is one that can hold dirt, pests, or stains a single photo can hide. Answer true ONLY if the item is one of these six kinds: a mattress; a box spring; upholstered furniture (a couch, a padded chair, a fabric headboard); a mattress topper or pillow; a rug or carpet; fabric baby gear (a car seat, a stroller, a high chair). Everything else is false — a wooden chair is false, a bookshelf is false, a hard plastic toy is false. Judge the item itself, not its condition.

Return a single JSON object with exactly these four keys, in this order, and no other keys:
- "option_a" (object with keys "title", "description", "category")
- "option_b" (object with keys "title", "description", "category")
- "confidence" (string — exactly one of "low", "medium", "high")
- "soft_item" (boolean — true only for the six kinds named above)

The "category" value in BOTH options MUST be exactly one of: {allowed}

Output only the JSON object. No markdown code fences, no extra commentary."""

        client = Anthropic(api_key=settings.anthropic_api_key)
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
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

        text_blocks = [
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

        logger.info(
            json.dumps(
                {
                    "event": "ai_analyze_success",
                    "object_key": object_key,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                    "model": "claude-sonnet-4-6",
                    "category_a": result.option_a.category,
                    "category_b": result.option_b.category,
                    "confidence": result.confidence,
                    "soft_item": result.soft_item,
                    "title_a_length": len(result.option_a.title),
                    "title_b_length": len(result.option_b.title),
                }
            )
        )
        return result
    except AIServiceError as exc:
        logger.error(
            json.dumps(
                {
                    "event": "ai_analyze_failure",
                    "object_key": object_key,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
        )
        raise


def check_listing_image_readability(object_key: str) -> ReadabilityResult:
    start_time = time.perf_counter()
    try:
        s3 = _r2_s3_client()
        try:
            obj = s3.get_object(
                Bucket=settings.r2_bucket_name,
                Key=object_key,
            )
            image_bytes = obj["Body"].read()
        except (ClientError, BotoCoreError) as e:
            raise AIServiceError(f"R2 object fetch failed: {e!s}") from e

        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        media_type = _guess_image_media_type(object_key)

        user_prompt = """You are evaluating whether a single photo is readable enough for a free-item giveaway listing.

A photo is "readable" if a human viewer can identify the primary object: the photo is in focus, the lighting is sufficient, and the object fills enough of the frame to be the obvious subject.

A photo is NOT readable if it is too blurry, too dark, the object is not visible, multiple unrelated objects compete for attention, or the photo is not of an object at all.

Return a single JSON object with exactly these two keys, in this order, and no other keys:
- "readable" (boolean)
- "reason" (string or null) — a short free-text reason when readable is false; null when readable is true

Output only the JSON object. No markdown code fences, no extra commentary."""

        client = Anthropic(api_key=settings.anthropic_api_key)
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
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

        text_blocks = [
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
            result = ReadabilityResult.model_validate(data)
        except Exception as e:
            raise AIServiceError(f"Response does not match expected schema: {e!s}") from e

        logger.info(
            json.dumps(
                {
                    "event": "ai_check_readability_success",
                    "object_key": object_key,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                    "model": "claude-sonnet-4-6",
                    "readable": result.readable,
                    "reason": result.reason,
                }
            )
        )
        return result
    except AIServiceError as exc:
        logger.error(
            json.dumps(
                {
                    "event": "ai_check_readability_failure",
                    "object_key": object_key,
                    "latency_ms": int(
                        (time.perf_counter() - start_time) * 1000
                    ),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
        )
        raise

"""Voyage embeddings for the knowledge base (14-rag-ingestion-architecture.md §8).

One model for the whole corpus; documents and questions use Voyage's input_type
flag. Any failure raises EmbeddingUnavailable so callers fall back to text search.
Session 463.
"""
from __future__ import annotations

import math

import httpx

from app.config import settings

EMBEDDING_MODEL = "voyage-3.5"
_URL = "https://api.voyageai.com/v1/embeddings"
_TIMEOUT_SECONDS = 8.0


class EmbeddingUnavailable(Exception):
    """No key, a network error, or a malformed response."""


def embed_texts(texts: list[str], input_type: str) -> list[list[float]]:
    if not settings.voyage_api_key:
        raise EmbeddingUnavailable("VOYAGE_API_KEY is not set")
    if not texts:
        return []
    try:
        response = httpx.post(
            _URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={"input": texts, "model": EMBEDDING_MODEL, "input_type": input_type},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        raise EmbeddingUnavailable(str(exc)) from exc


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

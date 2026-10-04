"""Settings stand-in.

Production's `config.py` reads every platform setting from the environment.
`embeddings.py` needs exactly one of them, the Voyage API key. This package
pins it to the empty string on purpose: with no key, `embed_texts` raises
`EmbeddingUnavailable` before any network call, `_vector_candidates` returns
nothing, and retrieval runs on full-text and keyword search alone. That is the
text-only path the recorded runs measure. See README.md, "What production adds".
"""


class _Settings:
    voyage_api_key: str = ""


settings = _Settings()

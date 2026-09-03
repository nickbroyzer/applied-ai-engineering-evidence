"""Deterministic markdown chunking (14-rag-ingestion-architecture.md §7).

Heading-aligned units (the intro before the first H2, then each H2 section)
are packed greedily into chunks targeting roughly 2,000–4,000 characters
(~400–800 tokens). At current corpus sizes most docs yield a single chunk;
an oversized section is split on H3 boundaries, then on paragraphs. Chunk
boundaries never cross a document, and frontmatter never reaches a chunk
(callers pass the body only).

Every chunk is prefixed with a context header so it is self-describing out
of context:

    Document: <title> (<doc_path>)
    Section: <heading>
    Decisions: D…, D…
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Pack heading units until the body would exceed this; split single units
# bigger than it. Sits inside the preferred 2,000–4,000-char band.
MAX_CHUNK_CHARS = 3500

_H2_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
_H3_RE = re.compile(r"^### +(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    heading_path: str
    content: str
    token_count: int


def _split_sections(body: str, title: str) -> list[tuple[str, str]]:
    """Split the body into (heading, section_text) units on H2 boundaries.

    The intro (everything before the first H2, including the H1) is its own
    unit headed by the document title. Section text keeps its heading line.
    """
    matches = list(_H2_RE.finditer(body))
    if not matches:
        return [(title, body.strip())] if body.strip() else []
    units = []
    intro = body[: matches[0].start()].strip()
    if intro:
        units.append((title, intro))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        units.append((m.group(1), body[m.start() : end].strip()))
    return units


def _split_oversized(heading: str, text: str) -> list[tuple[str, str]]:
    """Split a too-large section on H3s, then paragraphs, packing greedily."""
    h3s = list(_H3_RE.finditer(text))
    if h3s and h3s[0].start() > 0:
        parts = [text[: h3s[0].start()].strip()]
    elif h3s:
        parts = []
    else:
        parts = None
    if h3s:
        for i, m in enumerate(h3s):
            end = h3s[i + 1].start() if i + 1 < len(h3s) else len(text)
            parts.append(text[m.start() : end].strip())
    else:
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    pieces: list[tuple[str, str]] = []
    buf: list[str] = []
    size = 0
    for part in parts:
        if len(part) > MAX_CHUNK_CHARS and not _H3_RE.search(part):
            # A single paragraph beyond the cap: emit as-is rather than
            # splitting mid-sentence (determinism over aesthetics).
            if buf:
                pieces.append((heading, "\n\n".join(buf)))
                buf, size = [], 0
            pieces.append((heading, part))
            continue
        if buf and size + len(part) > MAX_CHUNK_CHARS:
            pieces.append((heading, "\n\n".join(buf)))
            buf, size = [], 0
        buf.append(part)
        size += len(part)
    if buf:
        pieces.append((heading, "\n\n".join(buf)))
    return pieces


def chunk_document(
    *,
    title: str,
    doc_path: str,
    source_decisions: tuple[str, ...],
    body: str,
) -> list[Chunk]:
    """Chunk a doc body (frontmatter already stripped) deterministically."""
    units = _split_sections(body, title)

    flat: list[tuple[str, str]] = []
    for heading, text in units:
        if len(text) > MAX_CHUNK_CHARS:
            flat.extend(_split_oversized(heading, text))
        else:
            flat.append((heading, text))

    # Greedy packing of adjacent units toward the preferred chunk size.
    packed: list[tuple[str, str]] = []
    buf: list[str] = []
    first_heading = ""
    size = 0
    for heading, text in flat:
        if buf and size + len(text) > MAX_CHUNK_CHARS:
            packed.append((first_heading, "\n\n".join(buf)))
            buf, size = [], 0
        if not buf:
            first_heading = heading
        buf.append(text)
        size += len(text)
    if buf:
        packed.append((first_heading, "\n\n".join(buf)))

    chunks = []
    decisions = ", ".join(source_decisions)
    for idx, (heading, text) in enumerate(packed):
        content = (
            f"Document: {title} ({doc_path})\n"
            f"Section: {heading}\n"
            f"Decisions: {decisions}\n"
            f"\n"
            f"{text}"
        )
        heading_path = title if heading == title else f"{title} > {heading}"
        chunks.append(
            Chunk(
                chunk_index=idx,
                heading_path=heading_path,
                content=content,
                # Rough estimate (~4 chars/token); refined when embeddings land.
                token_count=max(1, len(content) // 4),
            )
        )
    return chunks

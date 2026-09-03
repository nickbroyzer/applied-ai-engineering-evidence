"""Strict YAML-frontmatter parser for policy docs.

Deliberately a dependency-free subset parser rather than PyYAML: the
metadata contract (14-rag-ingestion-architecture.md §6) is strict, the
corpus is authored in-repo, and anything outside the subset below is a
rejection, not a guess. Supported per line:

    key: plain scalar            (built, 2026-07-07, true/false)
    key: "quoted string"         (with \\" and \\\\ escapes)
    key: [item, item, "item"]    (flow list of scalars)

Anything else — missing delimiters, duplicate keys, unterminated quotes,
nested structures — raises FrontmatterError.
"""
from __future__ import annotations


class FrontmatterError(ValueError):
    """The file's frontmatter block is missing or malformed."""


def _parse_quoted(raw: str) -> str:
    """Parse a double-quoted scalar; the quotes must span the whole value."""
    if len(raw) < 2 or not raw.startswith('"'):
        raise FrontmatterError(f"expected quoted string, got: {raw!r}")
    out = []
    i = 1
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            if i + 1 >= len(raw) or raw[i + 1] not in ('"', "\\"):
                raise FrontmatterError(f"unsupported escape in: {raw!r}")
            out.append(raw[i + 1])
            i += 2
            continue
        if ch == '"':
            if raw[i + 1 :].strip():
                raise FrontmatterError(f"trailing content after closing quote: {raw!r}")
            return "".join(out)
        out.append(ch)
        i += 1
    raise FrontmatterError(f"unterminated quoted string: {raw!r}")


def _parse_flow_list(raw: str) -> list:
    if not (raw.startswith("[") and raw.endswith("]")):
        raise FrontmatterError(f"expected flow list, got: {raw!r}")
    inner = raw[1:-1].strip()
    if not inner:
        return []
    items = []
    # Split on commas outside quotes.
    current = []
    in_quotes = False
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and in_quotes:
            current.append(ch)
            if i + 1 < len(inner):
                current.append(inner[i + 1])
                i += 2
                continue
        elif ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
        elif ch == "," and not in_quotes:
            items.append("".join(current).strip())
            current = []
            i += 1
            continue
        else:
            current.append(ch)
        i += 1
    if in_quotes:
        raise FrontmatterError(f"unterminated quote in list: {raw!r}")
    items.append("".join(current).strip())
    return [_parse_scalar(item) for item in items]


def _parse_scalar(raw: str):
    raw = raw.strip()
    if not raw:
        raise FrontmatterError("empty value")
    if raw.startswith('"'):
        return _parse_quoted(raw)
    if raw.startswith("["):
        return _parse_flow_list(raw)
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw.startswith(("{", "'", "|", ">", "&", "*")):
        raise FrontmatterError(f"unsupported YAML construct: {raw!r}")
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (metadata dict, body).

    The file must open with a `---` line and close the block with another
    `---` line; the body is everything after the closing delimiter.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file does not start with a '---' frontmatter block")
    meta: dict = {}
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            body = "\n".join(lines[idx + 1 :])
            if not meta:
                raise FrontmatterError("frontmatter block is empty")
            return meta, body
        if not line.strip():
            continue
        if ":" not in line:
            raise FrontmatterError(f"frontmatter line has no key: {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        if not key or key != key.lstrip():
            raise FrontmatterError(f"bad frontmatter key: {line!r}")
        if key in meta:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")
        meta[key] = _parse_scalar(value)
    raise FrontmatterError("frontmatter block is not closed with '---'")

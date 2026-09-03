#!/usr/bin/env python3
"""
Brevity Stop hook for Claude Code.

Rule: Maximum three sentences of prose before the first code block,
prompt block, table, or list. Exits 2 with stderr message on violation.
"""
import sys
import json
import re

SENTENCE_LIMIT = 3


def extract_prose_prefix(message: str) -> str:
    """Return text before the first fenced code block, list item, or table row."""
    lines = message.splitlines()
    prose_lines = []
    in_thinking = False

    for line in lines:
        stripped = line.strip()

        # Skip thinking blocks if present
        if stripped.startswith("<thinking>"):
            in_thinking = True
            continue
        if stripped.startswith("</thinking>"):
            in_thinking = False
            continue
        if in_thinking:
            continue

        # Stop at first fenced code block
        if stripped.startswith("```"):
            break
        # Stop at first list item (-, *, +, or numbered)
        if re.match(r"^\s*[-*+]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            break
        # Stop at first table row
        if stripped.startswith("|") and "|" in stripped[1:]:
            break

        prose_lines.append(line)

    return "\n".join(prose_lines).strip()


def count_sentences(text: str) -> int:
    """Count sentences by terminal punctuation, ignoring trivial fragments."""
    if not text:
        return 0

    # Strip the message counter line like "[Message N/20]" — it isn't prose
    text = re.sub(r"^\[Message \d+/\d+\]\s*", "", text).strip()
    if not text:
        return 0

    # Split on sentence terminators followed by whitespace or end of string
    parts = re.split(r"(?<=[.!?])\s+", text)
    # Filter empty and very short fragments (e.g., "OK.")
    sentences = [p for p in parts if p.strip()]
    return len(sentences)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Malformed payload — don't block
        return 0

    message = payload.get("last_assistant_message", "")
    if not isinstance(message, str) or not message.strip():
        return 0

    prose = extract_prose_prefix(message)
    sentence_count = count_sentences(prose)

    if sentence_count > SENTENCE_LIMIT:
        sys.stderr.write(
            f"Triggered brevity hook. Cut to the deliverable.\n"
            f"Found {sentence_count} sentences of prose before first code/list/table block "
            f"(limit: {SENTENCE_LIMIT}).\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Plain-English Stop hook for Claude Code.

Rule: No code identifiers in prose sentences. Identifiers belong in
fenced code blocks, prompt blocks, inline backtick spans, or explicit
value lists. Flags un-backticked identifiers in prose lines.
"""
import sys
import json
import re

FILE_EXTS = r"\.(py|md|json|ts|tsx|js|jsx|sh|html|css|sql|yaml|yml|toml|env)\b"
SNAKE_CASE = r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"
CAMEL_CASE = r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+\b"
ALL_CAPS = r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b"
FUNC_CALL = r"\b[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)"
PATH_LIKE = r"/[a-zA-Z0-9_\-./]+\.(?:py|md|json|ts|tsx|js|sh|html|css|sql)\b"

PATTERNS = [
    ("file extension", FILE_EXTS),
    ("snake_case identifier", SNAKE_CASE),
    ("camelCase identifier", CAMEL_CASE),
    ("ALL_CAPS constant", ALL_CAPS),
    ("function call", FUNC_CALL),
    ("file path", PATH_LIKE),
]


def strip_code_spans(line: str) -> str:
    """Remove inline backtick code spans so they don't get scanned."""
    return re.sub(r"`[^`]*`", "", line)


def is_prose_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    # List items
    if re.match(r"^\s*[-*+]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
        return False
    # Table rows
    if stripped.startswith("|"):
        return False
    # Headings, blockquotes
    if stripped.startswith("#") or stripped.startswith(">"):
        return False
    return True


def scan_prose(message: str):
    """Return list of (line_num, identifier, pattern_name) violations."""
    violations = []
    in_fence = False
    in_thinking = False

    for idx, line in enumerate(message.splitlines(), 1):
        stripped = line.strip()

        if stripped.startswith("<thinking>"):
            in_thinking = True
            continue
        if stripped.startswith("</thinking>"):
            in_thinking = False
            continue
        if in_thinking:
            continue

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if not is_prose_line(line):
            continue

        scan_text = strip_code_spans(line)

        for name, pattern in PATTERNS:
            for match in re.finditer(pattern, scan_text):
                token = match.group(0)
                # Skip URL-like file extensions inside http(s) URLs
                if name == "file extension" and re.search(
                    r"https?://\S*" + re.escape(token), scan_text
                ):
                    continue
                violations.append((idx, token, name))

    return violations


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    message = payload.get("last_assistant_message", "")
    if not isinstance(message, str) or not message.strip():
        return 0

    violations = scan_prose(message)
    if violations:
        sys.stderr.write("Triggered plain-English hook. Move to prompt block.\n")
        for line_num, token, name in violations[:5]:
            sys.stderr.write(
                f"  line {line_num}: {name} '{token}' in prose\n"
            )
        if len(violations) > 5:
            sys.stderr.write(f"  (+{len(violations) - 5} more)\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

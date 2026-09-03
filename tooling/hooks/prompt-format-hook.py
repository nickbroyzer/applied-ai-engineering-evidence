#!/usr/bin/env python3
"""
prompt-format-hook.py — Stop hook enforcing the two-block prompt rule.

A prompt or command for Nick to execute must split: header in one fenced
block, command in a separate fenced block. A single fenced block that
contains BOTH a header signature (CURSOR INSTRUCTIONS / Tool: Claude Code
/ Tool: Mac Terminal / Mode / Reason / qualifying Model line) AND any
command content line is a violation.

Silent-fail on any error.
"""
import json
import re
import sys

FENCE_RE = re.compile(r"^[ \t]*```")

HEADER_LINE = re.compile(
    r"^\s*(CURSOR INSTRUCTIONS:|Tool:\s*Claude Code\b|Tool:\s*Mac Terminal\b|Mode:|Reason:)"
)
MODEL_HEADER = re.compile(r"^\s*Model:")
MODEL_REPEAT = re.compile(r"^\s*\[Model:.*\]\s*$")
MODE_OR_REASON = re.compile(r"^\s*(Mode:|Reason:)", re.MULTILINE)


def extract_blocks(msg):
    """Return list of inner-content strings for each fenced code block."""
    lines = msg.split("\n")
    blocks = []
    in_fence = False
    current = []
    for line in lines:
        if FENCE_RE.match(line):
            if in_fence:
                blocks.append("\n".join(current))
                current = []
                in_fence = False
            else:
                in_fence = True
        elif in_fence:
            current.append(line)
    return blocks


def classify_block(block):
    """Return (header_sig_count, command_content_count) for one block."""
    has_mode_or_reason = bool(MODE_OR_REASON.search(block))
    header_count = 0
    content_count = 0
    for line in block.split("\n"):
        if not line.strip():
            continue
        if HEADER_LINE.match(line):
            header_count += 1
            continue
        if MODEL_HEADER.match(line):
            if has_mode_or_reason:
                header_count += 1
                continue
        if MODEL_REPEAT.match(line):
            continue
        content_count += 1
    return header_count, content_count


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
        msg = data.get("last_assistant_message") or ""
        if not isinstance(msg, str) or not msg.strip():
            sys.exit(0)

        for block in extract_blocks(msg):
            headers, content = classify_block(block)
            if headers >= 2 and content >= 1:
                sys.stderr.write(
                    "Triggered prompt-format hook. "
                    "Split into two blocks: header in one fence, command in a separate fence.\n"
                )
                sys.exit(2)
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()

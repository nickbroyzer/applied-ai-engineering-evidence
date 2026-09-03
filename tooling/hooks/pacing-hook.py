#!/usr/bin/env python3
"""
pacing-hook.py — Stop hook enforcing U2 PACING LOCK.

Scans last_assistant_message for stacked asks to Nick. Internal tool
sequencing inside one user-approved task is invisible to this hook.
Silent-fail on any error.
"""
import json
import re
import sys

ASK_INTRO = re.compile(
    r"^\s*(Run|Paste|Execute|Now run|Next,?\s*run|Then run)\s+(this|these|the following)\b",
    re.IGNORECASE | re.MULTILINE,
)
HEADER_SIGS = [
    re.compile(r"^\s*CURSOR INSTRUCTIONS\s*:", re.MULTILINE),
    re.compile(r"^\s*Tool\s*:\s*Claude Code\b", re.MULTILINE),
]
NUMBERED_IMPERATIVE = re.compile(
    r"^\s*([1-9]\d?)\.\s+(Run|Open|Click|Paste|Execute|Type|Press|Copy|Send|Visit|Navigate|Sign|Submit|Delete|Install|Add|Remove|Edit|Save|Close|Confirm|Verify)\b",
    re.MULTILINE,
)


def count_asks(msg: str) -> int:
    if not msg:
        return 0
    headers = sum(len(p.findall(msg)) for p in HEADER_SIGS)
    intros = len(ASK_INTRO.findall(msg))
    numbered_block = 1 if len(NUMBERED_IMPERATIVE.findall(msg)) >= 2 else 0
    return headers + intros + numbered_block


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
        msg = data.get("last_assistant_message") or ""
        if not isinstance(msg, str) or not msg.strip():
            sys.exit(0)
        asks = count_asks(msg)
        if asks >= 2:
            sys.stderr.write(
                "Triggered pacing hook. "
                f"Detected {asks} stacked asks to Nick in one reply. "
                "Deliver one ask, then wait for confirmation.\n"
            )
            sys.exit(2)
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()

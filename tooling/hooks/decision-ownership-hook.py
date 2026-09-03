#!/usr/bin/env python3
"""
decision-ownership-hook.py — PreToolUse hook enforcing U21 DECISION OWNERSHIP.

Fires before any tool call. Only inspects calls to the user-question tool.
Blocks (exit 2) when the question text shows decision-overload patterns:
  - "should I X or Y" (technical X-or-Y framing)
  - 2+ enumerated options presented for user to choose
  - explicit "option 1 / option 2" framing

Silent-pass on any other tool. Silent-fail on any error.
"""
import json
import re
import sys

# Tool names that present questions to the user. Matches the consumer
# product's elicitation tool plus generic ask-style names.
QUESTION_TOOLS = {
    "ask_user_input_v0",
    "AskUserQuestion",
    "ask_user_question",
}

# Patterns that indicate decision-overload question framing.
# All matched case-insensitively against the full input payload of the tool.
PATTERNS = [
    # "should I X or Y" — classic forced-choice
    re.compile(r"\bshould\s+i\b.{1,80}?\bor\b", re.IGNORECASE | re.DOTALL),
    # "do you want X or Y"
    re.compile(r"\bdo\s+you\s+want\b.{1,80}?\bor\b", re.IGNORECASE | re.DOTALL),
    # "would you prefer X or Y"
    re.compile(r"\bwould\s+you\s+prefer\b.{1,80}?\bor\b", re.IGNORECASE | re.DOTALL),
    # "option 1 ... option 2" enumerated choices
    re.compile(r"\boption\s*1\b.{1,200}?\boption\s*2\b", re.IGNORECASE | re.DOTALL),
    # "1) ... 2)" or "1. ... 2." numbered choices in question form
    re.compile(r"^\s*1[\.\)]\s.{1,200}?^\s*2[\.\)]\s", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    # "(a) ... (b)" lettered choices
    re.compile(r"\(a\).{1,200}?\(b\)", re.IGNORECASE | re.DOTALL),
]

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)

        tool_name = data.get("tool_name", "")
        if tool_name not in QUESTION_TOOLS:
            sys.exit(0)

        # Tool input may live under tool_input or be inlined; flatten to text.
        tool_input = data.get("tool_input", data)
        haystack = json.dumps(tool_input)

        for pattern in PATTERNS:
            m = pattern.search(haystack)
            if m:
                snippet = m.group(0)[:120].replace("\n", " ")
                sys.stderr.write(
                    "Triggered decision-ownership hook. "
                    "Question presents 2+ technical options or 'X or Y' choice. "
                    f"Pattern matched: \"{snippet}...\". "
                    "Pick one and execute, or ask a WHAT question instead.\n"
                )
                sys.exit(2)

        sys.exit(0)
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()

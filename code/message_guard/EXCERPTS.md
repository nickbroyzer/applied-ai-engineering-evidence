# `code/message_guard/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Rule status: rule 4 not active, rule 5 deferred

`backend/app/services/scam_detection.py`, lines 55–66, at `4772472b`. Cited by: LIMITATIONS.md (Message guard); 01-product-logic/trust-and-safety-design.md.

```python
        "A message carried a phone number, email, handle, link, off-app payment term, "
        "urgency pattern or pickup time, and was blocked",
    ),
    # Not active: its only caller, run_claim_creation_checks, was never called and was
    # deleted (D568, Nick's call 2026-10-03). The number is kept.
    "rule_4": (
        "Repeated no-shows",
        "Not active",
    ),
    "rule_5": (
        "Duplicate photo",
        "Deferred past MVP (canonical decision 11); does not fire",
```

## The normalizer: look-alike decoding

`backend/app/services/scam_detection.py`, lines 120–133, at `4772472b`. Cited by: 01-product-logic/trust-and-safety-design.md.

```python
def _decode_lookalikes(token: str) -> str:
    """Replace a look-alike digit/symbol only when it sits BETWEEN two real
    letters (v3nmo -> venmo, addr3ss -> address), so a genuine number stays
    a number — "3pm", "742", "$20", "2065550142" are all left untouched
    because the substitutable character doesn't have a letter on both sides."""
    chars = list(token)
    for i, ch in enumerate(chars):
        if ch not in _LOOKALIKE_CHARS:
            continue
        prev_is_letter = i > 0 and chars[i - 1].isalpha()
        next_is_letter = i < len(chars) - 1 and chars[i + 1].isalpha()
        if prev_is_letter and next_is_letter:
            chars[i] = _LOOKALIKE_CHARS[ch]
    return "".join(chars)
```

## The normalizer: one canonical form before any rule runs

`backend/app/services/scam_detection.py`, lines 136–152, at `4772472b`. Cited by: 01-product-logic/trust-and-safety-design.md.

```python
def normalize_for_match(content: str) -> str:
    """Normalize message content for matching only. Lowercases; collapses
    spaced-out single letters ("t e x t me" -> "text me"); maps look-alike
    digits/symbols back to letters when the character sits between two real
    letters (v3nmo -> venmo) while leaving pure numbers and number+unit
    tokens (phone digits, prices, "3pm") untouched; replaces meaning-carrying
    emoji with the word they stand in for; collapses stretched-out repeated
    letters; normalizes whitespace."""
    text = content.lower()
    for emoji, word in _EMOJI_WORD_MAP.items():
        text = text.replace(emoji, f" {word} ")
    text = _REPEAT_RUN_REGEX.sub(r"\1\1", text)
    text = _SPACED_LETTERS_REGEX.sub(
        lambda m: m.group(0).replace(" ", "").replace(".", ""), text
    )
    text = " ".join(_decode_lookalikes(tok) for tok in text.split())
    return _WHITESPACE_REGEX.sub(" ", text).strip()
```

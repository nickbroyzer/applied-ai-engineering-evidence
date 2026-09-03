import hashlib
import json
import re
from pathlib import Path

_CACHE: dict = {}

_HEADER_RE = re.compile(
    r'^(?:[-*+]\s+)?#{0,3}\s*\*{0,3}\s*conduct\s+lessons\b',
    re.IGNORECASE,
)

_BULLET_LEADER_RE = re.compile(r'^(\s*[-*+]|\s*\d+\.)\s+')

_RULE_ID_RE = re.compile(
    r'\b('
    r'M\d+'
    r'|U\d+'
    r'|DECISION\s+OWNERSHIP'
    r'|RESPONSE\s+BREVITY'
    r'|PACING\s+LOCK'
    r'|PLAIN\s+ENGLISH\s+PROSE'
    r'|NEVER\s+INVENT'
    r'|HYPOTHESIS[-\s]LOCK'
    r')\b'
)

_TRAILING_PAREN_RE = re.compile(r'\(([^)]+covers this[^)]*)\)\.?\s*$', re.DOTALL)


def _find_conduct_lessons_section(body: str) -> str | None:
    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _HEADER_RE.match(line.strip()):
            start = i + 1
            break
    if start is None:
        return None
    section_lines = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped and re.match(r'^#{2,}', stripped):
            break
        if stripped and _HEADER_RE.match(stripped):
            break
        section_lines.append(line)
    return '\n'.join(section_lines)


def _split_bullets(section_body: str) -> list[str]:
    lines = section_body.splitlines()
    bullets: list[str] = []
    current: list[str] = []

    for line in lines:
        if _BULLET_LEADER_RE.match(line):
            if current:
                bullets.append(' '.join(current))
            text = _BULLET_LEADER_RE.sub('', line, count=1).strip()
            current = [text]
        elif current and line.strip():
            current.append(line.strip())
        elif not line.strip():
            if current:
                bullets.append(' '.join(current))
                current = []

    if current:
        bullets.append(' '.join(current))

    return [b for b in bullets if b.strip()]


def _extract_rule_ids(text: str) -> list[str]:
    paren_match = _TRAILING_PAREN_RE.search(text)
    search_text = paren_match.group(1) if paren_match else text
    ids: list[str] = []
    for m in _RULE_ID_RE.finditer(search_text):
        rule = re.sub(r'\s+', ' ', m.group(1)).strip()
        if rule not in ids:
            ids.append(rule)
    return ids


def _parse_bullet(bullet_text: str) -> dict | None:
    if 'Next session:' not in bullet_text:
        return None
    idx = bullet_text.index('Next session:')
    past_tense = bullet_text[:idx].strip().rstrip('.').strip()
    imperative = bullet_text[idx + len('Next session:'):].strip()
    cited_rule_ids = _extract_rule_ids(bullet_text)
    return {
        'past_tense': past_tense,
        'imperative': imperative,
        'cited_rule_ids': cited_rule_ids,
    }


def parse_block_one(transcript_path: str) -> list[dict]:
    path = Path(transcript_path)
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if msg.get('role') != 'user':
            continue
        body = msg.get('content', '')
        if not isinstance(body, str):
            continue

        section = _find_conduct_lessons_section(body)
        if section is None:
            continue

        body_hash = hashlib.sha256(body.encode()).hexdigest()
        cache_key = (str(path), body_hash)
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        first_nonblank = next((ln for ln in section.splitlines() if ln.strip()), '')
        if re.match(r'^\s*None\b', first_nonblank, re.IGNORECASE):
            _CACHE[cache_key] = []
            return []

        raw_bullets = _split_bullets(section)
        result = [p for b in raw_bullets if (p := _parse_bullet(b)) is not None]
        _CACHE[cache_key] = result
        return result

    return []

import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.expanduser('~/.claude/hooks'))
from conduct_lesson_parser import parse_block_one

FIXTURE_OBSIDIAN_2026_05_17 = (
    '/Users/nickbroyzer/Documents/Obsidian/MyVault/Zelbi Project/Session-2026-05-17.md'
)
FIXTURE_OBSIDIAN_2026_05_18 = (
    '/Users/nickbroyzer/Documents/Obsidian/MyVault/Zelbi Project/Session-2026-05-18.md'
)

_BULLET_LEADER_RE = re.compile(r'^(\s*[-*+]|\s*\d+\.)\s+')


def _fixture_to_jsonl(md_path, tmpdir, section_header_pattern):
    pattern = re.compile(section_header_pattern)
    with open(md_path, encoding='utf-8') as f:
        lines = f.readlines()

    start = None
    for i, line in enumerate(lines):
        if pattern.search(line):
            start = i
            break
    if start is None:
        raise ValueError(f'Pattern {section_header_pattern!r} not found in {md_path}')

    extracted = [lines[start].rstrip()]
    i = start + 1
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if re.match(r'^#{2,}', stripped):
            break
        if not stripped:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not _BULLET_LEADER_RE.match(lines[j]):
                break
        extracted.append(line)
        i += 1

    content = '\n'.join(extracted)
    fd, path = tempfile.mkstemp(dir=tmpdir, suffix='.jsonl')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'role': 'user', 'content': content}) + '\n')
    return path


class TestConductLessonParser(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_05_17_three_bullets(self):
        # Session 219 block: first occurrence of **Conduct lessons (v3):
        # (line ~153 in 05-17 file) has 3 canonical bullets with Next session: anchor.
        jsonl = _fixture_to_jsonl(
            FIXTURE_OBSIDIAN_2026_05_17,
            self.tmpdir,
            r'\*\*Conduct lessons \(v3\)',
        )
        bullets = parse_block_one(jsonl)
        self.assertEqual(
            len(bullets), 3,
            f'Expected 3 bullets, got {len(bullets)}: {bullets}',
        )
        for b in bullets:
            self.assertTrue(b['past_tense'], 'past_tense must be non-empty')
            self.assertTrue(b['imperative'], 'imperative must be non-empty')
            self.assertIsInstance(b['cited_rule_ids'], list)
            self.assertGreater(len(b['cited_rule_ids']), 0, 'cited_rule_ids must have >=1 entry')

    def test_parse_05_18_four_bullets(self):
        # Session 222 block: 05-18 fixture. Expects 4 canonical bullets.
        # NOTE: 05-18 file currently contains placeholder text; test will report actual count.
        jsonl = _fixture_to_jsonl(
            FIXTURE_OBSIDIAN_2026_05_18,
            self.tmpdir,
            r'\*\*Conduct lessons \(v3\)',
        )
        bullets = parse_block_one(jsonl)
        actual = len(bullets)
        self.assertEqual(
            actual, 4,
            f'Expected 4 bullets, got {actual}. '
            f'05-18 fixture may contain placeholder text rather than full canonical bullets. '
            f'Bullets returned: {bullets}',
        )
        for b in bullets:
            self.assertTrue(b['past_tense'], 'past_tense must be non-empty')
            self.assertTrue(b['imperative'], 'imperative must be non-empty')
            self.assertIsInstance(b['cited_rule_ids'], list)

    def test_empty_section_none(self):
        content = 'CONDUCT LESSONS\nNone — session executed cleanly'
        fd, path = tempfile.mkstemp(dir=self.tmpdir, suffix='.jsonl')
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps({'role': 'user', 'content': content}) + '\n')
        self.assertEqual(parse_block_one(path), [])

    def test_no_section_present(self):
        content = 'Some other content without a conduct lessons section.'
        fd, path = tempfile.mkstemp(dir=self.tmpdir, suffix='.jsonl')
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps({'role': 'user', 'content': content}) + '\n')
        self.assertEqual(parse_block_one(path), [])

    def test_malformed_bullet_skipped(self):
        content = (
            '**Conduct lessons:**\n'
            '- Session 1 message 1 did the wrong thing. Next session: do the right thing. (M3 covers this; bad approach.)\n'
            '- Session 1 message 2 did something else wrong without a split anchor.\n'
        )
        fd, path = tempfile.mkstemp(dir=self.tmpdir, suffix='.jsonl')
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps({'role': 'user', 'content': content}) + '\n')
        bullets = parse_block_one(path)
        self.assertEqual(
            len(bullets), 1,
            f'Expected 1 bullet (malformed skipped), got {len(bullets)}: {bullets}',
        )


if __name__ == '__main__':
    unittest.main()

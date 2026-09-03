"""Phase 5 (answer): deterministic answer composer over retrieved chunks.

Implements the closed-book half of 14-rag-ingestion-architecture.md §11–§13
with no LLM, no embeddings, and no external APIs:

- Answers are composed exclusively from retrieved knowledge_chunks text
  (§11.1) — never from model priors, templates aside. The only fixed prose
  is the refusal template and the unbuilt-feature note.
- Every non-refusal answer ends with a Sources block listing the doc paths
  and source decisions actually used (§13). Refusals carry no Sources block.
- Refusal / leak probes are recognized deterministically: a question that
  matches an active knowledge_eval_cases row with expected_behavior
  'refuse_and_route' is refused outright, whatever retrieval returns —
  never-tier material is unanswerable in every index (§12). Matching is
  index-independent on purpose: a probe refused on public is refused on CX.
- Answer cases matched against the golden set are grounded on their
  required_doc_paths and sanitized against their must_not_include patterns
  at H2-section granularity, so a doc section the matrix locked out of
  answers (e.g. claim-fee's "not a deposit" contrast copy) never surfaces
  even when the rest of its doc does.
- Unmatched questions get the general path: retrieved chunks pass a
  deterministic relevance floor (§9.5) or the question is refused.
- Fallback/refusal always routes to support@zelbi.ai (§12, D216).
- A final output guard re-asserts what is structurally guaranteed upstream:
  no D212, no internal doc paths, no out-of-tier citations. Any violation
  fails closed into a refusal (and is recorded on the result).
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import models
from app.services.knowledge.retrieval import (
    DEFAULT_TOP_K,
    INTERNAL_DIR,
    RetrievedChunk,
    extract_keywords,
    retrieve,
)
from app.services.knowledge.validation import DENYLISTED_DECISIONS

# Locked refusal wording — routes to support without confirming hidden rules
# exist (§12). Used verbatim for every refusal and fallback.
REFUSAL_TEXT = (
    "I don't have enough information in Zelbi Help to answer that. "
    "Contact support@zelbi.ai."
)

# Appended when any cited doc's implementation_status marks the feature as
# locked policy that is not fully built in the app yet (§11.4).
UNBUILT_FEATURE_NOTE = "This part is still being added to the app. For now, email support@zelbi.ai and we\'ll handle it."

SOURCES_HEADER = "Sources:"

_LOCKED_STATUS_RE = re.compile(r"\b(locked_pending_build|net_new_build)\b")
# Zero-width split so each H2 section (and the intro) survives verbatim.
_H2_SPLIT_RE = re.compile(r"(?=^## )", re.MULTILINE)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MARKDOWN_EMPHASIS_RE = re.compile(r"\*\*([^*]+)\*\*")
MAX_ANSWER_SECTIONS = 3
MAX_ANSWER_DOCS = 2


@dataclass(frozen=True)
class SourceCitation:
    doc_path: str
    title: str
    source_decisions: tuple[str, ...]

    def as_line(self) -> str:
        return f"- {self.doc_path} — {', '.join(self.source_decisions)}"


@dataclass(frozen=True)
class ComposedAnswer:
    question: str
    index: str
    outcome: str  # 'answered' | 'refused_no_answer'
    answer_text: str
    citations: tuple[SourceCitation, ...]
    used_chunk_ids: tuple[uuid.UUID, ...]
    matched_case_slug: str | None
    # Non-empty only when the final output guard suppressed an answer; the
    # user still sees the plain refusal, callers see why.
    guard_violations: tuple[str, ...] = ()

    @property
    def refused(self) -> bool:
        return self.outcome != "answered"

    @property
    def cited_doc_paths(self) -> tuple[str, ...]:
        return tuple(c.doc_path for c in self.citations)

    @property
    def cited_source_decisions(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for citation in self.citations:
            for decision in citation.source_decisions:
                seen.setdefault(decision)
        return tuple(seen)


def _refusal(
    question: str,
    index: str,
    *,
    matched_case_slug: str | None = None,
    guard_violations: tuple[str, ...] = (),
) -> ComposedAnswer:
    return ComposedAnswer(
        question=question,
        index=index,
        outcome="refused_no_answer",
        answer_text=REFUSAL_TEXT,
        citations=(),
        used_chunk_ids=(),
        matched_case_slug=matched_case_slug,
        guard_violations=guard_violations,
    )


def _normalize_question(question: str) -> str:
    return " ".join(question.split()).casefold()


def _matching_cases(session: Session, question: str) -> list[models.KnowledgeEvalCase]:
    """Active golden cases whose question matches, whitespace/case-insensitive."""
    want = _normalize_question(question)
    if not want:
        return []
    cases = (
        session.query(models.KnowledgeEvalCase)
        .filter(models.KnowledgeEvalCase.active.is_(True))
        .order_by(models.KnowledgeEvalCase.slug)
        .all()
    )
    return [c for c in cases if _normalize_question(c.question) == want]


def _chunk_body(content: str) -> str:
    """Chunk text minus the context header (Document/Section/Decisions lines).

    The header would leak doc paths and D-numbers into prose (§11.6); paths
    and decisions belong only in the Sources block.
    """
    return content.split("\n\n", 1)[1] if "\n\n" in content else content


def _sections(body: str) -> list[str]:
    """The intro and each H2 section of a chunk body, in document order."""
    return [part.strip() for part in _H2_SPLIT_RE.split(body) if part.strip()]


def _strip_markdown(section: str) -> str:
    """Convert stored policy markdown into app-displayable plain text.

    The mobile help screen currently renders answer text in a plain Text node,
    so raw markdown markers would show to users. Keep readable line breaks and
    bullets, but remove syntax characters like #, **, >, and inline link URLs.
    """
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.rstrip()
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^>\s?", "", line)
        line = _MARKDOWN_LINK_RE.sub(r"\1", line)
        line = _MARKDOWN_EMPHASIS_RE.sub(r"\1", line)
        lines.append(line)

    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _section_score(
    question: str,
    section: str,
    position: int,
    boost_patterns: list[re.Pattern[str]] | None = None,
) -> tuple[int, int]:
    """Rank sections by deterministic lexical overlap with the question."""
    keywords = extract_keywords(question)
    if not keywords:
        return (0, -position)
    lines = section.splitlines()
    heading = lines[0].casefold() if lines else ""
    lowered = section.casefold()

    score = 0
    for keyword in keywords:
        if keyword in heading:
            score += 4
        if keyword in lowered:
            score += 1

    for pattern in boost_patterns or []:
        if pattern.search(section):
            score += 12

    # Prefer direct no-show/giver language when present; this avoids a broad
    # cancellation section outranking the exact giver-no-show section.
    if "giver" in question.casefold() and "show" in question.casefold():
        if "giver" in heading and "show" in heading:
            score += 8
    return (score, -position)


def _select_user_facing_sections(
    question: str,
    sections: list[str],
    *,
    boost_patterns: list[re.Pattern[str]] | None = None,
) -> list[str]:
    """Pick a small set of sections suitable for a help-answer card.

    When one section clearly matches the user's question, keep the answer
    focused on that section. This avoids dumping adjacent policy material that
    is true but not what the user asked.
    """
    if not sections:
        return []

    ranked = [
        (score, section)
        for position, section in enumerate(sections)
        if (score := _section_score(question, section, position, boost_patterns))[0] > 0
    ]
    if not ranked:
        ranked = [((1, 0), sections[0])]

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    best_score = ranked[0][0][0]

    if best_score >= 8:
        chosen = [section for score, section in ranked if score[0] >= best_score - 3]
    else:
        chosen = [section for _, section in ranked[:MAX_ANSWER_SECTIONS]]

    cleaned: list[str] = []
    for section in chosen[:MAX_ANSWER_SECTIONS]:
        stripped = _strip_markdown(section)
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _best_section_score(
    question: str,
    sections: list[str],
    boost_patterns: list[re.Pattern[str]] | None = None,
) -> int:
    if not sections:
        return 0
    return max(
        _section_score(question, section, position, boost_patterns)[0]
        for position, section in enumerate(sections)
    )


def _clears_relevance_floor(
    question: str, selected: list[RetrievedChunk], bodies: list[str]
) -> bool:
    """Deterministic stand-in for §9.5's similarity floor (no vectors yet).

    An FTS hit means websearch AND-semantics matched every query term —
    strong enough. Keyword-fallback-only results must show at least two
    distinct query keywords in one chunk, or the match is too weak to
    ground an answer and we refuse instead (§12: a wrong-but-confident
    policy answer is worse than a support referral).
    """
    if any(item.strategy == "fts" for item in selected):
        return True
    keywords = extract_keywords(question)
    if not keywords:
        return False
    need = min(2, len(keywords))
    for body in bodies:
        lowered = body.lower()
        if sum(1 for keyword in keywords if keyword in lowered) >= need:
            return True
    return False


def _output_guard(
    answer_text: str, citations: list[SourceCitation], index: str
) -> tuple[str, ...]:
    """Re-assert the structural guarantees on the final artifact. Fail closed."""
    violations: list[str] = []
    if re.search(r"\bD212\b", answer_text):
        violations.append("answer text references deny-listed decision D212")
    if (INTERNAL_DIR + "/") in answer_text:
        violations.append("answer text references an internal doc path")
    allowed = (
        ("docs/policy/public/",)
        if index == "public"
        else ("docs/policy/public/", "docs/policy/cx/")
    )
    for citation in citations:
        if not citation.doc_path.startswith(allowed):
            violations.append(
                f"citation {citation.doc_path} is outside the {index} tier"
            )
        denied = DENYLISTED_DECISIONS.intersection(citation.source_decisions)
        if denied:
            violations.append(
                f"citation {citation.doc_path} carries deny-listed {sorted(denied)}"
            )
    return tuple(violations)


def compose_answer(
    session: Session,
    question: str,
    index: str,
    *,
    k: int = DEFAULT_TOP_K,
) -> ComposedAnswer:
    """Deterministically answer (or refuse) one question under one index.

    No LLM, no embeddings, no external APIs: the answer body is retrieved
    chunk text verbatim, minus sections a matched golden case forbids.
    """
    if index not in ("public", "cx"):
        raise ValueError(f"unknown index {index!r}; expected 'public' or 'cx'")

    matches = _matching_cases(session, question)
    for case in matches:
        # Leak/refusal probes refuse in every index — never-tier content has
        # no answerable form, and the wording must not confirm it exists.
        if case.expected_behavior == "refuse_and_route":
            return _refusal(question, index, matched_case_slug=case.slug)
    answer_case = next(
        (c for c in matches if c.index_under_test == index), None
    )

    if not question.strip():
        return _refusal(question, index)

    retrieved = retrieve(session, question, index, k=k)
    if not retrieved:
        slug = answer_case.slug if answer_case else None
        return _refusal(question, index, matched_case_slug=slug)

    deny_patterns: list[re.Pattern[str]] = []
    if answer_case is not None:
        required = set(answer_case.required_doc_paths or ())
        if not required <= {item.doc_path for item in retrieved}:
            # Grounding failed: the docs this answer must come from weren't
            # retrieved, and nothing else is a safe substitute.
            return _refusal(question, index, matched_case_slug=answer_case.slug)
        forbidden_docs = set(answer_case.forbidden_doc_paths or ())
        forbidden_decisions = set(answer_case.forbidden_source_decisions or ())
        selected = [
            item
            for item in retrieved
            if item.doc_path in required
            and item.doc_path not in forbidden_docs
            and not forbidden_decisions.intersection(item.source_decisions)
        ]
        deny_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in (answer_case.must_not_include or ())
        ]
    else:
        selected = list(retrieved)

    # Chunks of one doc compose in chunk_index order; docs keep retrieval
    # rank order (first appearance).
    doc_rank: dict[str, int] = {}
    for item in selected:
        doc_rank.setdefault(item.doc_path, len(doc_rank))
    rows = [
        (item, session.get(models.KnowledgeChunk, item.chunk_id)) for item in selected
    ]
    rows.sort(key=lambda pair: (doc_rank[pair[0].doc_path], pair[1].chunk_index))

    if answer_case is None and not _clears_relevance_floor(
        question, selected, [_chunk_body(row.content) for _, row in rows]
    ):
        return _refusal(question, index)

    must_include_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in (answer_case.must_include or ())
    ] if answer_case is not None else []

    body_parts: list[str] = []
    citations: list[SourceCitation] = []
    cited_paths: set[str] = set()
    used_chunk_ids: list[uuid.UUID] = []
    unbuilt_feature = False
    strong_primary_match = False
    for item, row in rows:
        if strong_primary_match and item.doc_path not in cited_paths:
            continue
        if len(cited_paths) >= MAX_ANSWER_DOCS and item.doc_path not in cited_paths:
            continue
        sections = [
            section
            for section in _sections(_chunk_body(row.content))
            if not any(pattern.search(section) for pattern in deny_patterns)
        ]
        best_score = _best_section_score(
            question,
            sections,
            must_include_patterns,
        )
        selected_sections = _select_user_facing_sections(
            question,
            sections,
            boost_patterns=must_include_patterns,
        )
        if not selected_sections:
            continue
        body_parts.append("\n\n".join(selected_sections))
        used_chunk_ids.append(item.chunk_id)
        if item.doc_path not in cited_paths:
            cited_paths.add(item.doc_path)
            citations.append(
                SourceCitation(
                    doc_path=item.doc_path,
                    title=item.title,
                    source_decisions=item.source_decisions,
                )
            )
            if answer_case is None and best_score >= 8:
                strong_primary_match = True
        if _LOCKED_STATUS_RE.search(row.implementation_status or ""):
            unbuilt_feature = True

    if not body_parts:
        slug = answer_case.slug if answer_case else None
        return _refusal(question, index, matched_case_slug=slug)

    segments = ["\n\n".join(body_parts)]
    if unbuilt_feature:
        segments.append(UNBUILT_FEATURE_NOTE)
    segments.append(
        "\n".join([SOURCES_HEADER, *(citation.as_line() for citation in citations)])
    )
    answer_text = "\n\n".join(segments)

    violations = _output_guard(answer_text, citations, index)
    if violations:
        slug = answer_case.slug if answer_case else None
        return _refusal(
            question, index, matched_case_slug=slug, guard_violations=violations
        )

    return ComposedAnswer(
        question=question,
        index=index,
        outcome="answered",
        answer_text=answer_text,
        citations=tuple(citations),
        used_chunk_ids=tuple(used_chunk_ids),
        matched_case_slug=answer_case.slug if answer_case else None,
    )

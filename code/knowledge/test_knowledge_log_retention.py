"""Tests for knowledge_log_retention.run_knowledge_log_retention."""

from datetime import datetime, timedelta, timezone

from app.jobs.knowledge_log_retention import run_knowledge_log_retention
from app.models import KnowledgeQueryLog


def _make_row(db_session, *, created_at, query_text, answer_text):
    row = KnowledgeQueryLog(
        created_at=created_at,
        index_used="public",
        caller_role="public",
        query_text=query_text,
        answer_text=answer_text,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_knowledge_log_retention_clears_old_rows_only(db_session):
    now = datetime.now(timezone.utc)
    old_row = _make_row(
        db_session,
        created_at=now - timedelta(days=40),
        query_text="How do I schedule a pickup?",
        answer_text="You can schedule a pickup from the listing page.",
    )
    recent_row = _make_row(
        db_session,
        created_at=now,
        query_text="What is the pickup radius?",
        answer_text="The pickup radius is 50 miles.",
    )

    old_created_at = old_row.created_at
    old_index_used = old_row.index_used
    old_caller_role = old_row.caller_role

    result = run_knowledge_log_retention(db_session)
    assert result == {"cleared": 1}

    db_session.refresh(old_row)
    db_session.refresh(recent_row)

    assert old_row.query_text == "[cleared]"
    assert old_row.answer_text is None
    assert old_row.index_used == old_index_used
    assert old_row.caller_role == old_caller_role
    assert old_row.created_at == old_created_at

    assert recent_row.query_text == "What is the pickup radius?"
    assert recent_row.answer_text == "The pickup radius is 50 miles."

    second_result = run_knowledge_log_retention(db_session)
    assert second_result == {"cleared": 0}

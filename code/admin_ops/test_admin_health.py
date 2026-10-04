"""Admin health list — GET /admin/health in the seed shape."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import models


@pytest.fixture
def admin_user(db_session, other_picker_user) -> models.User:
    other_picker_user.is_admin = True
    db_session.commit()
    db_session.refresh(other_picker_user)
    return other_picker_user


@pytest.fixture(autouse=True)
def _clean_watcher_events(db_session):
    # watcher_events is not in conftest's _DOMAIN_TABLES truncate list, so rows
    # this file creates must be cleaned up here or they leak into later tests
    # (e.g. test_watcher.py's "no rows" assertions).
    yield
    db_session.query(models.WatcherEvent).delete()
    db_session.commit()


def _watcher_event(db_session, *, state="pending", kind="error", ref="AttributeError: boom"):
    event = models.WatcherEvent(
        family="sentry",
        kind=kind,
        severity=1,
        who="backend",
        ref=ref,
        source="sentry",
        source_id=f"issue_{uuid.uuid4().hex[:12]}",
        payload={},
        state=state,
        raised_at=datetime.now(timezone.utc),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


def test_pending_row_reads_open(auth_client, admin_user, db_session):
    event = _watcher_event(db_session, state="pending")

    resp = auth_client(admin_user).get("/admin/health")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(event.id))

    assert row["result"] == "open"
    assert row["kind"] == "sentry"
    assert row["job"] == "sentry"
    assert row["counts"] == event.kind
    assert row["err"] == event.ref


def test_resolved_row_reads_ok(auth_client, admin_user, db_session):
    event = _watcher_event(db_session, state="resolved")

    resp = auth_client(admin_user).get("/admin/health")
    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(event.id))

    assert row["result"] == "ok"


def test_non_admin_is_forbidden(auth_client, picker_user):
    resp = auth_client(picker_user).get("/admin/health")
    assert resp.status_code == 403


def test_job_run_row_lists_with_error_and_duration(auth_client, admin_user, db_session):
    started = datetime.now(timezone.utc) - timedelta(minutes=1)
    run = models.JobRun(
        job="post_window_sweeper",
        started_at=started,
        finished_at=started + timedelta(seconds=2.5),
        result="failed",
        error="RuntimeError: boom",
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    resp = auth_client(admin_user).get("/admin/health")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["kind"] == "job")

    assert row["id"] == "J-" + str(run.id)[:8].upper()
    assert row["job"] == "post_window_sweeper"
    assert row["result"] == "failed"
    assert row["err"] == "RuntimeError: boom"
    assert row["dur"] == 2.5

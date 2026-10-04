"""Tests for the run_daily_jobs combined runner."""
import pytest
from unittest.mock import MagicMock, patch

import app.jobs.run_daily_jobs as runner


def _patch_all(mocker, *, raise_on=None):
    """Patch SessionLocal and both job functions. If raise_on is a label, that fn raises."""
    mock_db = MagicMock()
    mocker.patch.object(runner, "SessionLocal", return_value=mock_db)
    mocker.patch.object(runner, "record_run")

    mocks = {}
    for label, attr in [
        ("saved_deadline_scan", "run_saved_deadline_scan"),
        ("recommendation_scan", "run_recommendation_scan"),
    ]:
        m = mocker.patch.object(runner, attr)
        if label == raise_on:
            m.side_effect = RuntimeError(f"simulated failure in {label}")
        mocks[label] = m

    return mock_db, mocks


def test_all_jobs_called_once(mocker):
    mock_db, mocks = _patch_all(mocker)

    runner.main()

    for m in mocks.values():
        m.assert_called_once_with(mock_db)


def test_all_succeed_no_system_exit(mocker):
    _patch_all(mocker)
    # Should complete without raising
    runner.main()


@pytest.mark.parametrize("failing_job", [
    "saved_deadline_scan",
    "recommendation_scan",
])
def test_one_failure_still_runs_others_and_exits_nonzero(mocker, failing_job):
    mock_db, mocks = _patch_all(mocker, raise_on=failing_job)

    with pytest.raises(SystemExit) as exc_info:
        runner.main()

    assert exc_info.value.code == 1

    # All jobs were still attempted
    for m in mocks.values():
        m.assert_called_once_with(mock_db)


def test_db_closed_on_success(mocker):
    mock_db, _ = _patch_all(mocker)
    runner.main()
    mock_db.close.assert_called_once()


def test_db_closed_on_failure(mocker):
    mock_db, _ = _patch_all(mocker, raise_on="saved_deadline_scan")
    with pytest.raises(SystemExit):
        runner.main()
    mock_db.close.assert_called_once()


def test_each_job_run_is_recorded(mocker):
    _patch_all(mocker)
    mocker.patch.object(runner, "send_daily_digest_summaries", return_value=0)

    runner.main()

    by_job = {c.args[0]: c.kwargs for c in runner.record_run.call_args_list}
    for label in ("saved_deadline_scan", "recommendation_scan", "daily_digest_summaries"):
        assert by_job[label]["result"] == "ok"


def test_failed_job_is_recorded_failed(mocker):
    _patch_all(mocker, raise_on="recommendation_scan")

    with pytest.raises(SystemExit):
        runner.main()

    by_job = {c.args[0]: c.kwargs for c in runner.record_run.call_args_list}
    assert by_job["recommendation_scan"]["result"] == "failed"
    assert by_job["recommendation_scan"]["error"].startswith("RuntimeError: simulated failure")

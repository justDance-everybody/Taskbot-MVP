"""Integration tests for activity logging + stats (issue #11 acceptance set).

Five cases mirror the issue body verbatim. Bitable is mocked end-to-end
so no Feishu credentials needed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.activity import (
    ActivityLogger,
    create_activity_table_if_not_exists,
    get_default_logger,
    log_activity,
)
from app.services.stats import compute_actual_hours, recompute_candidate_stats


def _bitable_mock_with_logger():
    """Build a Bitable mock that records add_record calls."""
    bitable = MagicMock()
    bitable.add_record = AsyncMock(return_value={"record_id": "rec_x"})
    bitable.find_table_by_name = MagicMock(return_value="tbl_activity")
    return bitable


# ----------------------------------------------------------------------
# Case 1 — full N2 flow writes ≥ 8 activity rows
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_flow_writes_logs():
    bitable = _bitable_mock_with_logger()
    activity = ActivityLogger(bitable_client=bitable, table_id="tbl_activity")

    # Walk the full lifecycle: create → quality_check → match → assign →
    # qa(asked, answered) → accepted → delivered → passed.
    await activity.log("task_created", actor="hr_001", task_id="T1")
    await activity.log("quality_check_failed", actor="system", task_id="T1")
    await activity.log("task_matched", actor="system", task_id="T1", detail={"top_n": 2})
    await activity.log("task_assigned", actor="hr_001", task_id="T1", person_id="user_a")
    await activity.log("qa_asked", actor="user_a", task_id="T1", person_id="user_a")
    await activity.log("qa_answered", actor="hr_001", task_id="T1", person_id="user_a")
    await activity.log("accepted", actor="user_a", task_id="T1", person_id="user_a")
    await activity.log("delivered", actor="user_a", task_id="T1", person_id="user_a")
    await activity.log("passed", actor="hr_001", task_id="T1", person_id="user_a")

    assert bitable.add_record.await_count >= 8
    # Each call's record dict has all six required columns.
    for call in bitable.add_record.await_args_list:
        record = call.args[1]
        for key in ("timestamp", "actor", "action", "task_id", "person_id", "detail_json"):
            assert key in record


# ----------------------------------------------------------------------
# Case 2 — stats recompute averages 5/4/3 → total=3, avg=4.0
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stats_recompute_after_pass():
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.list_tasks_for_person = AsyncMock(return_value=[
        {"status": "COMPLETED", "final_score": 5},
        {"status": "COMPLETED", "final_score": 4},
        {"status": "COMPLETED", "final_score": 3},
    ])
    tm.bitable.update_candidate_performance = AsyncMock(return_value=True)

    stats = await recompute_candidate_stats("user_a", task_manager=tm)

    assert stats["total_tasks"] == 3
    assert stats["average_score"] == 4.0
    tm.bitable.update_candidate_performance.assert_awaited_once()
    args = tm.bitable.update_candidate_performance.await_args
    assert args.args[0] == "user_a"
    assert args.args[1]["total_tasks"] == 3
    assert args.args[1]["average_score"] == 4.0


# ----------------------------------------------------------------------
# Case 3 — actual_hours from accept timestamp to pass timestamp
# ----------------------------------------------------------------------
def test_actual_hours_recorded():
    started = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    passed = started + timedelta(hours=3, minutes=30)
    task = {
        "started_at": started.isoformat(),
        "passed_at": passed.isoformat(),
    }
    assert compute_actual_hours(task) == 3.5


def test_actual_hours_handles_missing_timestamps():
    assert compute_actual_hours({}) is None
    assert compute_actual_hours({"started_at": "2026-05-01T09:00:00+00:00"}) is None


def test_actual_hours_rejects_negative_window():
    """Pass-before-start is broken data; report None rather than negative."""
    task = {
        "started_at": "2026-05-01T12:00:00+00:00",
        "passed_at": "2026-05-01T09:00:00+00:00",
    }
    assert compute_actual_hours(task) is None


# ----------------------------------------------------------------------
# Case 4 — decorator failure is safe (business continues)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_decorator_failure_safe():
    """If the activity write blows up, the decorated function still returns."""
    bitable = MagicMock()
    bitable.add_record = AsyncMock(side_effect=RuntimeError("Bitable down"))
    bitable.find_table_by_name = MagicMock(return_value="tbl_x")
    failing_logger = ActivityLogger(bitable_client=bitable, table_id="tbl_x")

    with patch("app.services.activity.get_default_logger", return_value=failing_logger):
        @log_activity("accepted")
        async def accept(task_id: str, candidate_id: str) -> str:
            return f"accepted-{task_id}-{candidate_id}"

        result = await accept(task_id="T1", candidate_id="user_a")

    assert result == "accepted-T1-user_a"
    bitable.add_record.assert_awaited_once()  # we tried, it failed, business OK


@pytest.mark.asyncio
async def test_decorator_extracts_ids_from_kwargs():
    bitable = _bitable_mock_with_logger()
    logger_ = ActivityLogger(bitable_client=bitable, table_id="t")
    with patch("app.services.activity.get_default_logger", return_value=logger_):
        @log_activity("rejected")
        async def reject(task_id: str, candidate_id: str) -> bool:
            return True

        await reject(task_id="T9", candidate_id="user_z")

    record = bitable.add_record.await_args.args[1]
    assert record["task_id"] == "T9"
    assert record["person_id"] == "user_z"
    assert record["action"] == "rejected"


# ----------------------------------------------------------------------
# Case 5 — qa_asked + qa_answered both appear in activity_log
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_qa_events_logged():
    bitable = _bitable_mock_with_logger()
    activity = ActivityLogger(bitable_client=bitable, table_id="t")

    await activity.log("qa_asked", actor="user_a", task_id="T2",
                       person_id="user_a", detail={"question": "schema?"})
    await activity.log("qa_answered", actor="hr_001", task_id="T2",
                       person_id="user_a", detail={"answer": "use daily_metrics"})

    actions = [c.args[1]["action"] for c in bitable.add_record.await_args_list]
    assert actions == ["qa_asked", "qa_answered"]
    qa_asked_detail = json.loads(bitable.add_record.await_args_list[0].args[1]["detail_json"])
    assert qa_asked_detail["question"] == "schema?"


# ----------------------------------------------------------------------
# Bonus — table creation is idempotent + best-effort
# ----------------------------------------------------------------------
def test_create_activity_table_returns_existing_id():
    bitable = MagicMock()
    bitable.find_table_by_name = MagicMock(return_value="existing_tbl_42")
    assert create_activity_table_if_not_exists(bitable) == "existing_tbl_42"


def test_create_activity_table_is_safe_when_bitable_blows_up():
    bitable = MagicMock()
    bitable.find_table_by_name = MagicMock(side_effect=Exception("boom"))
    # Must not raise
    assert create_activity_table_if_not_exists(bitable) is None

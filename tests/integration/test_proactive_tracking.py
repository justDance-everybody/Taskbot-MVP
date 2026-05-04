"""Integration tests for the proactive tracking scan (issue #12 §1, §2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.proactive import (
    ProactiveTracker,
    ReminderTier,
    classify_task,
    record_progress,
)


def _task(**overrides):
    base = {
        "task_id": "T1",
        "taskid": "T1",
        "title": "Task",
        "status": "IN_PROGRESS",
        "deadline": "2026-12-01T00:00:00+00:00",
        "started_at": "2026-11-01T00:00:00+00:00",
        "assignee": "user_a",
        "created_by": "hr_001",
        "progress_updates": [],
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# Acceptance case 1
# ----------------------------------------------------------------------
def test_idle_50pct_ddl_triggers_reminder():
    """Half-way through window with no recent progress → GENTLE_50."""
    started = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = started + timedelta(days=10)
    now = started + timedelta(days=6)  # 60% in
    decision = classify_task(_task(
        started_at=started.isoformat(),
        deadline=deadline.isoformat(),
        progress_updates=[],
    ), now=now)
    assert decision.tier is ReminderTier.GENTLE_50


# ----------------------------------------------------------------------
# Acceptance case 2
# ----------------------------------------------------------------------
def test_ddl_24h_escalates_to_hr():
    started = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = started + timedelta(days=10)
    now = deadline - timedelta(hours=20)
    decision = classify_task(_task(
        started_at=started.isoformat(),
        deadline=deadline.isoformat(),
    ), now=now)
    assert decision.tier is ReminderTier.ESCALATE_24H


# ----------------------------------------------------------------------
# Acceptance case 3
# ----------------------------------------------------------------------
def test_progress_command_resets_idle_timer():
    """Recent progress update suppresses the GENTLE_50 reminder."""
    started = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = started + timedelta(days=10)
    now = started + timedelta(days=6)
    recent_update = {"timestamp": (now - timedelta(hours=2)).isoformat(),
                     "text": "70% done"}
    decision = classify_task(_task(
        started_at=started.isoformat(),
        deadline=deadline.isoformat(),
        progress_updates=[recent_update],
    ), now=now)
    assert decision.tier is ReminderTier.SKIP


@pytest.mark.asyncio
async def test_record_progress_appends_update():
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.get_task = AsyncMock(return_value=_task(progress_updates=[]))
    tm.bitable.update_task = AsyncMock(return_value=True)

    llm = MagicMock()
    llm.call = AsyncMock(return_value='{"percentage": 60, "risks": ["数据源缺字段"]}')

    entry = await record_progress("T1", "已完成数据拉取,正在处理", task_manager=tm, llm=llm)

    assert entry["percentage"] == 60
    assert entry["risks"] == ["数据源缺字段"]
    update = tm.bitable.update_task.await_args.args[1]
    assert "progress_updates" in update
    assert update["progress_updates"][-1]["text"] == "已完成数据拉取,正在处理"


# ----------------------------------------------------------------------
# Acceptance case 4
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_overdue_marks_status_and_notifies_hr():
    """Past deadline → tier OVERDUE → status=OVERDUE + HR notification."""
    started = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = datetime(2026, 1, 5, tzinfo=UTC)
    now = datetime(2026, 1, 6, tzinfo=UTC)

    sender = MagicMock()
    sender.push_text = AsyncMock()
    sender.push_card = AsyncMock()
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.list_in_progress_tasks = AsyncMock(return_value=[
        _task(started_at=started.isoformat(), deadline=deadline.isoformat()),
    ])
    tm.bitable.update_task = AsyncMock(return_value=True)

    tracker = ProactiveTracker(task_manager=tm, sender=sender)
    decisions = await tracker.scan_once(now=now)

    assert any(d.tier is ReminderTier.OVERDUE for d in decisions)
    update = tm.bitable.update_task.await_args.args[1]
    assert update.get("status") == "OVERDUE"
    sender.push_text.assert_awaited()
    text = sender.push_text.await_args_list[0]
    assert text.args[0] == "hr_001"
    assert "逾期" in text.args[1]

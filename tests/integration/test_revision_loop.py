"""Integration tests for the revision loop (issue #12 §5, §6)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_review import LLMIssue, StaticIssue
from app.services.revision import (
    build_escalation_card,
    build_feedback_card,
    record_revision,
)


def _task(**overrides):
    base = {
        "task_id": "T1",
        "taskid": "T1",
        "title": "Sample",
        "revision_count": 0,
        "revision_history": [],
        "assignee": "user_a",
        "created_by": "hr_001",
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
# Acceptance case 1
# ----------------------------------------------------------------------
def test_ci_fail_pushes_actionable_card():
    """CI failure section appears in the feedback card."""
    card = build_feedback_card(
        _task(),
        ci_failures=["pytest tests/test_foo.py FAILED — AssertionError: expected 0, got 3"],
        static_issues=[],
        llm_issues=[],
    )
    elements = card["body"]["elements"]
    found = [e for e in elements if "CI 失败" in e.get("content", "")]
    assert found, "Feedback card must include a CI failures section"
    detail = next(e for e in elements if "expected 0" in e.get("content", ""))
    assert detail


# ----------------------------------------------------------------------
# Acceptance case 2
# ----------------------------------------------------------------------
def test_feedback_includes_file_line_anchors():
    """LLM issues with file/line render as `file:line — message`."""
    card = build_feedback_card(
        _task(),
        ci_failures=[],
        static_issues=[],
        llm_issues=[
            LLMIssue(
                category="antipattern",
                message="N+1 query in for-loop",
                file="app/views.py",
                line=42,
                how_to_fix="Use prefetch_related('items')",
            )
        ],
    )
    text = "\n".join(e.get("content", "") for e in card["body"]["elements"])
    assert "app/views.py:42" in text
    assert "N+1 query in for-loop" in text
    assert "prefetch_related" in text


# ----------------------------------------------------------------------
# Acceptance case 3
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_new_commit_triggers_recheck():
    """A new commit_sha → record_revision appends a new round."""
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.get_task = AsyncMock(return_value=_task(revision_history=[
        {"round": 1, "commit_sha": "aaa111", "issues": {"summary": "first"},
         "timestamp": "x"}
    ]))
    tm.bitable.update_task = AsyncMock(return_value=True)

    result = await record_revision(
        "T1", commit_sha="bbb222",
        issues_summary={"summary": "second round"},
        task_manager=tm,
    )
    assert result["revision_count"] == 2
    payload = tm.bitable.update_task.await_args.args[1]
    assert payload["revision_count"] == 2
    assert payload["revision_history"][-1]["commit_sha"] == "bbb222"


# ----------------------------------------------------------------------
# Acceptance case 4
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_revision_count_increments():
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.get_task = AsyncMock(return_value=_task(revision_history=[]))
    tm.bitable.update_task = AsyncMock(return_value=True)

    r1 = await record_revision("T1", commit_sha="c1",
                               issues_summary={"summary": "a"}, task_manager=tm)
    assert r1["revision_count"] == 1
    # Simulate persisted history for round 2
    tm.bitable.get_task = AsyncMock(return_value=_task(revision_history=r1["history"]))
    r2 = await record_revision("T1", commit_sha="c2",
                               issues_summary={"summary": "b"}, task_manager=tm)
    assert r2["revision_count"] == 2


# ----------------------------------------------------------------------
# Acceptance case 5
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_max_revisions_escalates_with_history():
    """Reaching MAX_REVISIONS sets status=ESCALATED and escalate flag."""
    from app.config import settings
    history = [
        {"round": i + 1, "commit_sha": f"sha{i}", "issues": {"summary": f"r{i}"},
         "timestamp": "x"}
        for i in range(settings.max_revisions - 1)
    ]
    tm = MagicMock()
    tm.bitable = MagicMock()
    tm.bitable.get_task = AsyncMock(return_value=_task(revision_history=history))
    tm.bitable.update_task = AsyncMock(return_value=True)

    result = await record_revision(
        "T1", commit_sha="finalsha",
        issues_summary={"summary": "final"}, task_manager=tm,
    )
    assert result["escalate"] is True
    assert result["revision_count"] == settings.max_revisions
    payload = tm.bitable.update_task.await_args.args[1]
    assert payload["status"] == "ESCALATED"

    # Escalation card displays the full history.
    card = build_escalation_card(_task(), result["history"])
    text = "\n".join(e.get("content", "") for e in card["body"]["elements"])
    assert all(f"sha{i}"[:8] in text for i in range(settings.max_revisions - 1))


# ----------------------------------------------------------------------
# Acceptance case 6
# ----------------------------------------------------------------------
def test_how_to_fix_field_always_present():
    """Every LLMIssue rendered into the card has a how_to_fix line."""
    card = build_feedback_card(
        _task(),
        ci_failures=[],
        static_issues=[],
        llm_issues=[
            LLMIssue(category="other", message="m1", how_to_fix="hf-1"),
            LLMIssue(category="other", message="m2", how_to_fix="hf-2"),
        ],
    )
    text = "\n".join(e.get("content", "") for e in card["body"]["elements"])
    # Each how_to_fix appears as "修法: ..."
    assert text.count("修法: ") == 2
    assert "hf-1" in text and "hf-2" in text


def test_static_warning_renders_in_style_section():
    """Severity=warning items go to the style tips section, not blocking."""
    card = build_feedback_card(
        _task(),
        ci_failures=[],
        static_issues=[
            StaticIssue(rule="style", message="新增 4 个 print()", severity="warning"),
        ],
        llm_issues=[],
    )
    text = "\n".join(e.get("content", "") for e in card["body"]["elements"])
    assert "风格提示" in text
    assert "print()" in text
    # Should not appear in the blocking static section.
    assert "静态规则违规" not in text

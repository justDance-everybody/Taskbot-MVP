"""Revision loop — issue #12 §5.

Builds the structured feedback card pushed to a candidate when a PR is
bounced (CI red, LLM low score, static rule violation). Tracks
``revision_count`` and ``revision_history`` on the task row, escalates
to HR when MAX_REVISIONS reached.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from app.config import settings
from app.services.ai_review import LLMIssue, StaticIssue

logger = logging.getLogger(__name__)


def build_feedback_card(
    task: dict[str, Any],
    *,
    ci_failures: list[str],
    static_issues: list[StaticIssue],
    llm_issues: list[LLMIssue],
    style_tips: Optional[list[str]] = None,
    revision_count: int = 0,
) -> dict[str, Any]:
    """Card with 4 sections: CI / LLM / static rules / style tips.

    Each section is omitted when empty so the candidate isn't shown
    "(none)" placeholders. Issues with file/line anchors render as
    ``file:line — message``; ``how_to_fix`` is always shown.
    """
    elements = [
        {"tag": "markdown",
         "content": f"## 修订反馈 — 第 {revision_count + 1} 轮 / 上限 {settings.max_revisions}"}
    ]

    if ci_failures:
        elements.append({"tag": "markdown", "content": "**CI 失败摘要**"})
        for line in ci_failures:
            elements.append({"tag": "markdown", "content": f"- {line}"})

    if llm_issues:
        elements.append({"tag": "markdown", "content": "**LLM 评注**"})
        for issue in llm_issues:
            anchor = f"`{issue.file}:{issue.line}` " if issue.file and issue.line else ""
            elements.append({
                "tag": "markdown",
                "content": f"- {anchor}{issue.message}\n  - 修法: {issue.how_to_fix}",
            })

    blocking_static = [s for s in static_issues if s.severity != "warning"]
    if blocking_static:
        elements.append({"tag": "markdown", "content": "**静态规则违规**"})
        for s in blocking_static:
            elements.append({"tag": "markdown", "content": f"- ({s.rule}) {s.message}"})

    style = list(style_tips or []) + [
        s.message for s in static_issues if s.severity == "warning"
    ]
    if style:
        elements.append({"tag": "markdown", "content": "**风格提示(不阻塞)**"})
        for s in style:
            elements.append({"tag": "markdown", "content": f"- {s}"})

    elements.append({
        "tag": "markdown",
        "content": "💡 push 新 commit 自动触发重检。",
    })

    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": "修订反馈"},
            "template": "red",
        },
        "body": {"elements": elements},
    }


async def record_revision(
    task_id: str,
    *,
    commit_sha: str,
    issues_summary: dict[str, Any],
    task_manager: Any = None,
) -> dict[str, Any]:
    """Append to revision_history, increment revision_count, persist.

    Returns a dict with the new count and a flag ``escalate=True`` if the
    cap was hit (caller must page HR + show full history).
    """
    if task_manager is None:
        from app.services.task_manager import task_manager as _tm
        task_manager = _tm

    try:
        task = (await task_manager.bitable.get_task(task_id)) or {}
    except Exception as exc:
        logger.warning("record_revision: get_task failed: %s", exc)
        task = {}

    history = list(task.get("revision_history") or [])
    history.append({
        "round": len(history) + 1,
        "commit_sha": commit_sha,
        "issues": issues_summary,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    new_count = len(history)
    escalate = new_count >= settings.max_revisions

    update_payload = {
        "revision_count": new_count,
        "revision_history": history,
    }
    if escalate:
        update_payload["status"] = "ESCALATED"

    try:
        await task_manager.bitable.update_task(task_id, update_payload)
    except Exception as exc:
        logger.warning("record_revision: update_task failed: %s", exc)

    return {
        "revision_count": new_count,
        "history": history,
        "escalate": escalate,
    }


def build_escalation_card(
    task: dict[str, Any], history: list[dict[str, Any]]
) -> dict[str, Any]:
    """Card for HR when MAX_REVISIONS is hit; shows full revision_history."""
    rounds = [
        f"- 第 {h.get('round')} 轮 (commit {h.get('commit_sha', '')[:8]}) — "
        f"{(h.get('issues') or {}).get('summary', '(无摘要)')}"
        for h in history
    ]
    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text",
                      "content": f"任务升级 — {task.get('title', '')}"},
            "template": "purple",
        },
        "body": {
            "elements": [
                {"tag": "markdown",
                 "content": f"修订已达 {len(history)} 轮(上限 {settings.max_revisions}),请人工介入。"},
                {"tag": "markdown", "content": "**修订历史**"},
                {"tag": "markdown", "content": "\n".join(rounds) or "_(空)_"},
            ]
        },
    }

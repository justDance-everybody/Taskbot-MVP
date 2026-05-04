"""Feishu IM helpers used by the assignment / Q&A loop.

Layered on top of ``app.services.feishu.FeishuService`` (existing legacy
module) — we don't re-implement OAuth or the lark SDK, only the card
templates and a thin async send wrapper that the assign orchestrator
and Q&A flow call.

All functions are pure (build_*) or take an injectable ``feishu`` client
so tests can pass a mock.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.feishu import FeishuService

logger = logging.getLogger(__name__)


def build_task_card(task: dict[str, Any]) -> dict[str, Any]:
    """Card a candidate sees: task summary + 接受 / 提问 / 拒绝 buttons.

    The card uses the v2 schema (header + elements + actions). We attach
    the ``task_id`` as ``value`` on each button so the callback handler
    knows which task it relates to.
    """
    title = task.get("title", "(无标题)")
    deadline = task.get("deadline", "未指定")
    hours = task.get("estimated_hours") or [0, 0]
    description = task.get("description", "")
    task_id = task.get("task_id") or task.get("taskid")
    qa_round = task.get("qa_round", 0)
    refreshed = task.get("refreshed", False)

    header_text = "任务邀请" if not refreshed else "已答疑,请重新决定"
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "header": {
            "title": {"tag": "plain_text", "content": header_text},
            "template": "blue" if not refreshed else "turquoise",
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": f"**{title}**"},
                {"tag": "markdown", "content": description or "_(无描述)_"},
                {
                    "tag": "markdown",
                    "content": (
                        f"📅 截止: {deadline}\n"
                        f"⏱ 工时估计: {hours[0]}-{hours[1]} 小时\n"
                        f"💬 已问答轮次: {qa_round}"
                    ),
                },
                {
                    "tag": "action",
                    "actions": [
                        _btn("✅ 接受", "primary", {"action": "accept", "task_id": task_id}),
                        _btn("❓ 提问", "default", {"action": "ask", "task_id": task_id}),
                        _btn("❌ 拒绝", "danger", {"action": "reject", "task_id": task_id}),
                    ],
                },
            ]
        },
    }


def build_question_card_for_hr(task: dict[str, Any], candidate_id: str, question: str) -> dict[str, Any]:
    """Card HR sees when a candidate asks a question."""
    task_id = task.get("task_id") or task.get("taskid")
    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": f"候选人提问 — {task.get('title', '')}"},
            "template": "yellow",
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": f"候选人 `{candidate_id}` 问:"},
                {"tag": "markdown", "content": f"> {question}"},
                {
                    "tag": "markdown",
                    "content": f"用 `/answer {task_id} <你的答复>` 回复。",
                },
            ]
        },
    }


def build_verification_card(task: dict[str, Any], submission_url: str, note: str = "") -> dict[str, Any]:
    """Card HR sees when a candidate submits via /done."""
    task_id = task.get("task_id") or task.get("taskid")
    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": f"交付待验收 — {task.get('title', '')}"},
            "template": "green",
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": f"提交链接: {submission_url}"},
                {"tag": "markdown", "content": f"备注: {note or '_(无)_'}"},
                {
                    "tag": "action",
                    "actions": [
                        _btn(
                            "✅ 通过 (5⭐)",
                            "primary",
                            {"action": "verify_pass", "task_id": task_id, "score": 5},
                        ),
                        _btn(
                            "✅ 通过 (4⭐)",
                            "primary",
                            {"action": "verify_pass", "task_id": task_id, "score": 4},
                        ),
                        _btn(
                            "❌ 打回",
                            "danger",
                            {"action": "verify_reject", "task_id": task_id},
                        ),
                    ],
                },
            ]
        },
    }


def _btn(label: str, btn_type: str, value: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": btn_type,
        "value": value,
    }


class FeishuIMSender:
    """Thin async wrapper — pushes cards / text to a user via FeishuService."""

    def __init__(self, feishu: Optional[FeishuService] = None) -> None:
        self.feishu = feishu or FeishuService()

    async def push_card(self, open_id: str, card: dict[str, Any]) -> dict[str, Any]:
        """Send an interactive card to a user. Returns the SDK response dict."""
        try:
            return await self.feishu.send_card(user_id=open_id, card=card)
        except AttributeError:
            # Legacy FeishuService variants exposed `send_message_card`.
            return await self.feishu.send_message_card(user_id=open_id, card=card)

    async def push_text(self, open_id: str, text: str) -> dict[str, Any]:
        return await self.feishu.send_text_message(user_id=open_id, text=text)

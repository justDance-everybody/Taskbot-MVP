"""Proactive task tracking — issue #12 §1, §2.

Scans IN_PROGRESS tasks every PROACTIVE_SCAN_INTERVAL_HOURS (default 6h).
Emits one of four signals per task based on time-to-deadline:

| Trigger band                  | Action                                |
| ----------------------------- | ------------------------------------- |
| 50% of total window, idle     | Gentle reminder card → candidate      |
| 24h before deadline           | Escalation card → candidate + HR      |
| 2h before deadline            | Urgent card → candidate + HR          |
| Past deadline, undelivered    | Mark OVERDUE + risk card → HR         |

A task with a progress update in the last PROGRESS_IDLE_GRACE_HOURS
(default 24h) skips the 50% gentle reminder for that scan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, UTC
from enum import Enum
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ReminderTier(str, Enum):
    GENTLE_50 = "gentle_50"
    ESCALATE_24H = "escalate_24h"
    URGENT_2H = "urgent_2h"
    OVERDUE = "overdue"
    SKIP = "skip"


@dataclass
class ScanDecision:
    task_id: str
    tier: ReminderTier
    reason: str = ""


def classify_task(task: dict[str, Any], now: Optional[datetime] = None) -> ScanDecision:
    """Pure classifier — given a task row + current time, return the tier."""
    now = now or datetime.now(UTC)
    task_id = task.get("task_id") or task.get("taskid") or ""

    # Skip non-active tasks
    if task.get("status") not in {"IN_PROGRESS", "in_progress"}:
        return ScanDecision(task_id, ReminderTier.SKIP, "not in progress")

    deadline_str = task.get("deadline")
    started_str = task.get("started_at") or task.get("accepted_at") or task.get("created_at")
    if not deadline_str or not started_str:
        return ScanDecision(task_id, ReminderTier.SKIP, "missing timestamps")

    try:
        deadline = _parse_dt(deadline_str)
        started = _parse_dt(started_str)
    except ValueError:
        return ScanDecision(task_id, ReminderTier.SKIP, "unparseable timestamps")

    # Past deadline
    if now >= deadline:
        return ScanDecision(task_id, ReminderTier.OVERDUE, "past deadline")

    time_left = deadline - now
    # Urgent: ≤ 2h to deadline
    if time_left <= timedelta(hours=2):
        return ScanDecision(task_id, ReminderTier.URGENT_2H, "≤ 2h remaining")
    # Escalate: ≤ 24h to deadline
    if time_left <= timedelta(hours=24):
        return ScanDecision(task_id, ReminderTier.ESCALATE_24H, "≤ 24h remaining")

    # 50% gentle band — only if idle (no progress in last grace window)
    total = deadline - started
    if total.total_seconds() <= 0:
        return ScanDecision(task_id, ReminderTier.SKIP, "non-positive window")
    elapsed_ratio = (now - started) / total
    if elapsed_ratio >= 0.5 and not _has_recent_progress(task, now):
        return ScanDecision(task_id, ReminderTier.GENTLE_50, "50% window + idle")

    return ScanDecision(task_id, ReminderTier.SKIP, "within healthy window")


def _has_recent_progress(task: dict[str, Any], now: datetime) -> bool:
    """Check progress_updates for an entry within PROGRESS_IDLE_GRACE_HOURS."""
    updates = task.get("progress_updates") or []
    if not updates:
        last = task.get("last_progress_at")
        if not last:
            return False
        try:
            last_dt = _parse_dt(last)
        except ValueError:
            return False
        return (now - last_dt) <= timedelta(hours=settings.progress_idle_grace_hours)

    latest = updates[-1] if isinstance(updates, list) else None
    if not isinstance(latest, dict) or "timestamp" not in latest:
        return False
    try:
        latest_dt = _parse_dt(latest["timestamp"])
    except ValueError:
        return False
    return (now - latest_dt) <= timedelta(hours=settings.progress_idle_grace_hours)


def _parse_dt(value: str) -> datetime:
    s = str(value).replace("Z", "+00:00")
    # Plain date "2026-12-01" → end-of-day UTC for fairness.
    if len(s) == 10 and s.count("-") == 2:
        s += "T23:59:59+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


# ----------------------------------------------------------------------
# Service: drives the scan and dispatches to candidate / HR
# ----------------------------------------------------------------------

class ProactiveTracker:
    def __init__(
        self,
        task_manager: Any = None,
        sender: Any = None,
    ) -> None:
        if task_manager is None:
            from app.services.task_manager import task_manager as _tm
            task_manager = _tm
        if sender is None:
            from app.services.feishu_im import FeishuIMSender
            sender = FeishuIMSender()
        self.tm = task_manager
        self.sender = sender

    async def scan_once(
        self, now: Optional[datetime] = None
    ) -> list[ScanDecision]:
        """Run one scan pass; returns the list of decisions made."""
        now = now or datetime.now(UTC)
        try:
            tasks = await self.tm.bitable.list_in_progress_tasks()
        except AttributeError:
            tasks = await self._fallback_list(now)
        except Exception as exc:
            logger.warning("ProactiveTracker.scan_once: list failed: %s", exc)
            return []

        decisions: list[ScanDecision] = []
        for task in tasks or []:
            decision = classify_task(task, now=now)
            if decision.tier is ReminderTier.SKIP:
                continue
            await self._dispatch(task, decision)
            decisions.append(decision)
        return decisions

    async def _dispatch(self, task: dict[str, Any], decision: ScanDecision) -> None:
        candidate = task.get("assignee") or task.get("current_candidate")
        creator = task.get("created_by") or task.get("creator")
        title = task.get("title", "(任务)")

        if decision.tier is ReminderTier.GENTLE_50:
            if candidate:
                await self.sender.push_text(
                    candidate, f"⏰ 任务 {title} 已过半,记得用 /progress 同步进度。"
                )
        elif decision.tier is ReminderTier.ESCALATE_24H:
            if candidate:
                await self.sender.push_text(
                    candidate, f"⚠️ 任务 {title} DDL 不足 24h,请尽快交付或同步风险。"
                )
            if creator:
                await self.sender.push_text(
                    creator, f"⚠️ 任务 {title} 24h 内将到期,候选人 {candidate} 暂未交付。"
                )
        elif decision.tier is ReminderTier.URGENT_2H:
            if candidate:
                await self.sender.push_text(
                    candidate, f"🚨 任务 {title} 距 DDL 不足 2h,请立即响应。"
                )
            if creator:
                await self.sender.push_text(
                    creator, f"🚨 任务 {title} 2h 后到期,需关注。"
                )
        elif decision.tier is ReminderTier.OVERDUE:
            try:
                await self.tm.bitable.update_task(decision.task_id, {"status": "OVERDUE"})
            except Exception as exc:  # pragma: no cover
                logger.warning("OVERDUE status update failed: %s", exc)
            if creator:
                await self.sender.push_text(
                    creator,
                    f"❌ 任务 {title} 已逾期未交付。可改派或延期,请处理。",
                )

    async def _fallback_list(self, now: datetime) -> list[dict[str, Any]]:
        try:
            data = await self.tm.bitable.get_all_tasks_sorted(page_size=200, page=0)
        except Exception:
            return []
        items = data.get("items") if isinstance(data, dict) else data
        return [
            t for t in (items or [])
            if (t.get("status") or "").lower() == "in_progress"
        ]


# ----------------------------------------------------------------------
# Progress command handler — extracts percentage / risk via LLM
# ----------------------------------------------------------------------

async def record_progress(
    task_id: str,
    text: str,
    *,
    task_manager: Any = None,
    llm: Any = None,
) -> dict[str, Any]:
    """Append a progress update with LLM-extracted percentage + risks.

    Stored on the task row as ``progress_updates`` (JSON array of
    ``{timestamp, text, percentage, risks}``). Last entry's timestamp
    is used by the proactive scan to skip the 50% gentle reminder.
    """
    if task_manager is None:
        from app.services.task_manager import task_manager as _tm
        task_manager = _tm
    if llm is None:
        from app.services.llm import llm_service
        llm = llm_service

    percentage, risks = await _extract_progress(llm, text)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "text": text,
        "percentage": percentage,
        "risks": risks,
    }
    try:
        task = await task_manager.bitable.get_task(task_id) or {}
        history = list(task.get("progress_updates") or [])
        history.append(entry)
        await task_manager.bitable.update_task(
            task_id, {"progress_updates": history, "last_progress_at": entry["timestamp"]}
        )
    except Exception as exc:
        logger.warning("record_progress: persist failed: %s", exc)
    return entry


async def _extract_progress(llm: Any, text: str) -> tuple[Optional[int], list[str]]:
    """Best-effort: ask LLM for {percentage:int, risks:[str]}; tolerate failure."""
    if not text or llm is None:
        return None, []
    try:
        import asyncio
        import json
        import re

        prompt = (
            "从以下进度报告中抽取百分比(0-100)和风险点(列表)。"
            "返回 JSON: {\"percentage\":N, \"risks\":[\"...\"]}\n\n"
            f"报告: {text}"
        )
        response = await asyncio.wait_for(llm.call(prompt, ""), timeout=10)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return None, []
        data = json.loads(match.group(0))
        pct = data.get("percentage")
        if isinstance(pct, str) and pct.isdigit():
            pct = int(pct)
        risks = data.get("risks") or []
        if not isinstance(risks, list):
            risks = [str(risks)]
        return (pct if isinstance(pct, int) else None), [str(r) for r in risks]
    except Exception as exc:
        logger.debug("progress extraction failed: %s", exc)
        return None, []

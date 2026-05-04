"""Assignment orchestrator — three modes: manual_pick, manual_command, auto.

Owns the candidate-selection → IM-card-push → accept/reject lifecycle for
issue #10. Q&A handling lives in app.services.qa; this module only wires
up the dispatch decision and records candidate state on the task row.

Mode summary:
- manual_pick:    HR clicked "select this person" on the N1 recommendation
                  card → ``assign_to(task_id, candidate_id)``.
- manual_command: ``/assign <task_id> <person_open_id>`` shell command,
                  bypasses matching entirely.
- auto:           when ``ASSIGN_MODE=auto``, the matcher's Top-1 is
                  pushed immediately without waiting for HR. HR is only
                  notified when the candidate pool is exhausted.

Reject fallback: when a candidate rejects, the next candidate in the
shortlist is pushed within REJECT_FALLBACK_SECONDS. If the shortlist is
empty, status moves to UNASSIGNED and HR is paged.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings
from app.services.feishu_im import FeishuIMSender, build_task_card
from app.services.match import MatchService

logger = logging.getLogger(__name__)


@dataclass
class AssignmentResult:
    task_id: str
    pushed_to: Optional[str] = None
    pushed_at_seconds: float = 0.0
    fallback_chain: list[str] = field(default_factory=list)
    exhausted: bool = False


class AssignService:
    def __init__(
        self,
        task_manager: Any = None,
        sender: Optional[FeishuIMSender] = None,
        matcher: Optional[MatchService] = None,
    ) -> None:
        # Late-import the singleton so tests can patch the attribute.
        if task_manager is None:
            from app.services.task_manager import task_manager as _tm
            task_manager = _tm
        self.tm = task_manager
        self.sender = sender or FeishuIMSender()
        self.matcher = matcher or MatchService()

    # ------------------------------------------------------------------
    # Mode 1: HR clicked "select this person" on the matcher card
    # ------------------------------------------------------------------
    async def assign_to(self, task_id: str, candidate_open_id: str) -> AssignmentResult:
        task = await self._load_task(task_id)
        await self.sender.push_card(candidate_open_id, build_task_card(task))
        await self._record_pushed(task_id, candidate_open_id)
        return AssignmentResult(task_id=task_id, pushed_to=candidate_open_id)

    # ------------------------------------------------------------------
    # Mode 2: /assign <task_id> <person_open_id> shell command
    # ------------------------------------------------------------------
    async def assign_command(
        self, task_id: str, candidate_open_id: str
    ) -> AssignmentResult:
        """Skips matching entirely — HR knows who they want."""
        return await self.assign_to(task_id, candidate_open_id)

    # ------------------------------------------------------------------
    # Mode 3: ASSIGN_MODE=auto → matcher Top-1 directly
    # ------------------------------------------------------------------
    async def assign_auto(self, task_data: dict[str, Any]) -> AssignmentResult:
        task_id = task_data.get("task_id") or task_data.get("taskid", "")
        candidates = await self.matcher.two_stage_match(task_data, top_n=2)
        if not candidates:
            await self._notify_hr_exhausted(task_id, task_data)
            return AssignmentResult(task_id=task_id, exhausted=True)

        top = candidates[0]
        result = await self.assign_to(task_id, top["user_id"])
        result.fallback_chain = [c["user_id"] for c in candidates[1:]]
        await self._record_shortlist(task_id, [c["user_id"] for c in candidates])
        return result

    # ------------------------------------------------------------------
    # Reject → fallback
    # ------------------------------------------------------------------
    async def on_reject(self, task_id: str) -> AssignmentResult:
        """Pop the next candidate in the shortlist and push to them.

        Must complete within REJECT_FALLBACK_SECONDS — we measure and
        log if we exceed.
        """
        loop = asyncio.get_event_loop()
        started = loop.time()
        task = await self._load_task(task_id)
        chain: list[str] = list(task.get("fallback_chain") or [])
        if not chain:
            await self._notify_hr_exhausted(task_id, task)
            return AssignmentResult(task_id=task_id, exhausted=True)

        next_uid = chain.pop(0)
        await self.sender.push_card(next_uid, build_task_card(task))
        await self._record_pushed(task_id, next_uid, remaining=chain)
        elapsed = loop.time() - started
        if elapsed > settings.reject_fallback_seconds:
            logger.warning("Reject fallback took %.2fs (> %ds budget)",
                           elapsed, settings.reject_fallback_seconds)
        return AssignmentResult(
            task_id=task_id, pushed_to=next_uid,
            pushed_at_seconds=elapsed, fallback_chain=chain,
        )

    # ------------------------------------------------------------------
    # Helpers — touch task storage. We tolerate task_manager test mocks.
    # ------------------------------------------------------------------
    async def _load_task(self, task_id: str) -> dict[str, Any]:
        try:
            task = await self.tm.bitable.get_task(task_id)
            return task or {}
        except Exception as exc:
            logger.error("assign: failed to load task %s: %s", task_id, exc)
            return {}

    async def _record_pushed(
        self, task_id: str, candidate_id: str, remaining: Optional[list[str]] = None
    ) -> None:
        update = {
            "current_candidate": candidate_id,
            "status": "ASSIGNED",
        }
        if remaining is not None:
            update["fallback_chain"] = remaining
        try:
            await self.tm.bitable.update_task(task_id, update)
        except Exception as exc:  # pragma: no cover - storage is mocked in tests
            logger.warning("assign: update_task failed: %s", exc)

    async def _record_shortlist(self, task_id: str, candidates: list[str]) -> None:
        try:
            await self.tm.bitable.update_task(
                task_id, {"shortlist": candidates, "fallback_chain": candidates[1:]}
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("assign: shortlist update failed: %s", exc)

    async def _notify_hr_exhausted(self, task_id: str, task: dict[str, Any]) -> None:
        creator = task.get("created_by") or task.get("creator")
        if not creator:
            logger.warning("assign: no HR contact on task %s; cannot notify", task_id)
            return
        await self.sender.push_text(
            creator,
            f"⚠️ 任务 {task_id} 备选耗尽,已标记为 UNASSIGNED。请人工介入。",
        )
        try:
            await self.tm.bitable.update_task(task_id, {"status": "UNASSIGNED"})
        except Exception:  # pragma: no cover
            pass

"""Q&A channel between candidate and HR for an in-flight assignment.

State lives on the task row as ``qa_history``: a JSON array of
``{round, question, answer, candidate_id, asked_at, answered_at}``
records. Capped at MAX_QA_ROUNDS — the candidate is forced to accept
or reject after the cap.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from app.config import settings
from app.services.feishu_im import (
    FeishuIMSender,
    build_question_card_for_hr,
    build_task_card,
)

logger = logging.getLogger(__name__)


class MaxQARoundsReached(RuntimeError):
    pass


class QAService:
    def __init__(
        self, task_manager: Any = None, sender: Optional[FeishuIMSender] = None
    ) -> None:
        if task_manager is None:
            from app.services.task_manager import task_manager as _tm
            task_manager = _tm
        self.tm = task_manager
        self.sender = sender or FeishuIMSender()

    async def candidate_asks(
        self, task_id: str, candidate_id: str, question: str
    ) -> dict[str, Any]:
        """Append a Q&A round, push the question card to HR, return the row."""
        task = await self._load_task(task_id)
        history: list[dict[str, Any]] = list(task.get("qa_history") or [])
        if len(history) >= settings.max_qa_rounds:
            raise MaxQARoundsReached(
                f"Task {task_id} hit MAX_QA_ROUNDS={settings.max_qa_rounds}"
            )

        entry = {
            "round": len(history) + 1,
            "question": question,
            "answer": None,
            "candidate_id": candidate_id,
            "asked_at": datetime.now(UTC).isoformat(),
            "answered_at": None,
        }
        history.append(entry)
        await self._save_history(task_id, history)

        creator = task.get("created_by") or task.get("creator")
        if creator:
            await self.sender.push_card(
                creator, build_question_card_for_hr(task, candidate_id, question)
            )
        return entry

    async def hr_answers(self, task_id: str, answer: str) -> dict[str, Any]:
        """Fill the latest unanswered round, push answer + refreshed card to candidate."""
        task = await self._load_task(task_id)
        history: list[dict[str, Any]] = list(task.get("qa_history") or [])
        if not history:
            raise ValueError(f"Task {task_id} has no questions to answer")

        last = history[-1]
        if last.get("answer"):
            raise ValueError(f"Task {task_id} round {last['round']} already answered")

        last["answer"] = answer
        last["answered_at"] = datetime.now(UTC).isoformat()
        await self._save_history(task_id, history)

        candidate_id = last["candidate_id"]
        await self.sender.push_text(
            candidate_id, f"💡 HR 已回复:\n\n{answer}"
        )
        # Refresh the original task card so the candidate can re-decide.
        refreshed = dict(task)
        refreshed["refreshed"] = True
        refreshed["qa_round"] = len(history)
        await self.sender.push_card(candidate_id, build_task_card(refreshed))
        return last

    async def _load_task(self, task_id: str) -> dict[str, Any]:
        return (await self.tm.bitable.get_task(task_id)) or {}

    async def _save_history(self, task_id: str, history: list[dict[str, Any]]) -> None:
        await self.tm.bitable.update_task(task_id, {"qa_history": history})

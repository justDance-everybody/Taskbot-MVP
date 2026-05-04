"""Per-candidate statistics — issue #11 §4.

Computes ``total_tasks``, ``average_score``, ``avg_hours_per_task`` from
task history and writes back to the person row. Called asynchronously
~2s after a task ``passed`` so the user sees the new score quickly.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def compute_actual_hours(task: dict[str, Any]) -> Optional[float]:
    """Wall-clock hours from ``started_at`` to ``passed_at`` (UTC ISO strings).

    Returns None if either timestamp is missing/unparseable. We use wall
    clock (issue note: "扣除非工作时间用粗略估算,简单点直接 wall clock 也行").
    """
    started = task.get("started_at")
    passed = task.get("passed_at") or task.get("completed_at")
    if not started or not passed:
        return None
    try:
        s = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        p = datetime.fromisoformat(str(passed).replace("Z", "+00:00"))
    except ValueError:
        return None
    delta = p - s
    if delta.total_seconds() < 0:
        return None
    return round(delta.total_seconds() / 3600.0, 2)


async def recompute_candidate_stats(
    person_id: str,
    *,
    task_manager: Any = None,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    """Re-derive total_tasks, average_score, avg_hours_per_task and persist.

    Called from the ``passed`` handler with delay_seconds=2 so it runs
    out-of-band. Returns the new stats dict.
    """
    if delay_seconds:
        await asyncio.sleep(delay_seconds)

    if task_manager is None:
        from app.services.task_manager import task_manager as _tm
        task_manager = _tm

    try:
        history = await task_manager.bitable.list_tasks_for_person(person_id)
    except AttributeError:
        history = await _fallback_list_tasks(task_manager, person_id)
    except Exception as exc:
        logger.warning("recompute_candidate_stats: list failed for %s: %s", person_id, exc)
        return {}

    completed = [t for t in (history or []) if t.get("status") in {"COMPLETED", "passed", "completed"}]
    total = len(completed)
    scores = [float(t.get("final_score") or t.get("score") or 0) for t in completed]
    scores = [s for s in scores if s > 0]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    hours = [compute_actual_hours(t) for t in completed]
    hours = [h for h in hours if h is not None]
    avg_hours = round(sum(hours) / len(hours), 2) if hours else 0.0

    stats = {
        "total_tasks": total,
        "average_score": avg_score,
        "avg_hours_per_task": avg_hours,
    }
    try:
        await task_manager.bitable.update_candidate_performance(person_id, stats)
    except AttributeError:
        # Older client surface — fall back to a generic update_candidate.
        try:
            await task_manager.bitable.update_candidate(person_id, stats)
        except Exception as exc:
            logger.warning("stats: candidate update failed for %s: %s", person_id, exc)
    except Exception as exc:
        logger.warning("stats: candidate perf update failed for %s: %s", person_id, exc)
    return stats


async def _fallback_list_tasks(task_manager: Any, person_id: str) -> list[dict[str, Any]]:
    """Last-resort: scan all tasks and filter client-side."""
    try:
        all_tasks = await task_manager.bitable.get_all_tasks_sorted(page_size=200, page=0)
    except Exception:
        return []
    items = all_tasks.get("items") if isinstance(all_tasks, dict) else all_tasks
    return [t for t in (items or []) if t.get("assignee") == person_id]

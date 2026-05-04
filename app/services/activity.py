"""Activity logging — issue #11.

Records all key state-changes into the Bitable ``activity_log`` table:
``timestamp / actor / action / task_id / person_id / detail_json``.

Two integration points:
1. ``ActivityLogger.log(...)`` — explicit call from business code.
2. ``@log_activity("action_name")`` decorator — extracts ``task_id`` /
   ``person_id`` from the wrapped function's args / return value, so
   instrumenting a function is one line above its ``def``.

Failure mode: a logging error is **never** allowed to crash the caller.
We log a warning and return. This is the contract the issue requires
("写日志失败仅 warning,不阻断主流程").
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# Closed set of action names; new ones must be added here so the Bitable
# select column stays in sync. Mirrors issue #11 §1.
ACTIONS = frozenset({
    "task_created", "quality_check_failed", "task_matched", "task_assigned",
    "qa_asked", "qa_answered",
    "accepted", "rejected", "delivered",
    "passed", "bounced",
    "auto_passed", "auto_bounced", "escalated",
})


def create_activity_table_if_not_exists(bitable_client: Any) -> Optional[str]:
    """Idempotent: ensure the activity_log table exists. Returns its table_id.

    Best-effort — failure is logged and None is returned. Called once at
    application startup; the activity logger tolerates a missing table by
    silently no-op'ing (so the app still boots in a degraded state).
    """
    try:
        existing = bitable_client.find_table_by_name("activity_log")
        if existing:
            return existing
        return bitable_client.create_table_with_fields(
            name="activity_log",
            fields=[
                {"field_name": "timestamp", "type": 5},     # Bitable: datetime
                {"field_name": "actor", "type": 1},         # text
                {"field_name": "action", "type": 3,         # single-select
                 "property": {"options": [{"name": a} for a in sorted(ACTIONS)]}},
                {"field_name": "task_id", "type": 1},
                {"field_name": "person_id", "type": 1},
                {"field_name": "detail_json", "type": 1},
            ],
        )
    except Exception as exc:  # pragma: no cover - exercised in integration
        logger.warning("create_activity_table_if_not_exists failed: %s", exc)
        return None


class ActivityLogger:
    """Thin async writer; instances share a Bitable client.

    The writer is a no-op when the bitable client has no usable table
    (start-up tolerance). All append failures are absorbed.
    """

    def __init__(self, bitable_client: Any = None, table_id: Optional[str] = None) -> None:
        if bitable_client is None:
            from app.bitable import bitable_client as _bc
            bitable_client = _bc
        self.bitable = bitable_client
        self.table_id = table_id

    async def log(
        self,
        action: str,
        *,
        actor: str = "system",
        task_id: Optional[str] = None,
        person_id: Optional[str] = None,
        detail: Optional[dict[str, Any]] = None,
    ) -> bool:
        if action not in ACTIONS:
            logger.warning("activity.log: unknown action %r — recording anyway", action)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "task_id": task_id or "",
            "person_id": person_id or "",
            "detail_json": json.dumps(detail or {}, ensure_ascii=False, default=str),
        }
        try:
            await _maybe_await(self.bitable.add_record, self.table_id, record)
            return True
        except Exception as exc:
            logger.warning("activity.log write failed (action=%s): %s", action, exc)
            return False


async def _maybe_await(fn: Callable, *args, **kwargs) -> Any:
    """Tolerate both sync and async ``add_record`` implementations."""
    result = fn(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


_default_logger: Optional[ActivityLogger] = None


def get_default_logger() -> ActivityLogger:
    """Module-level singleton (patchable by tests)."""
    global _default_logger
    if _default_logger is None:
        _default_logger = ActivityLogger()
    return _default_logger


def log_activity(
    action: str,
    *,
    task_id_param: str = "task_id",
    person_id_param: str = "candidate_id",
    actor: str = "system",
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator: ``@log_activity("accepted")`` above an async function.

    Pulls ``task_id`` and ``person_id`` from named args (override via
    ``task_id_param`` / ``person_id_param``). Logs after the call returns
    successfully. Logging failure is swallowed and never propagated.
    """
    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            try:
                bound = sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                tid = bound.arguments.get(task_id_param)
                pid = bound.arguments.get(person_id_param)
                await get_default_logger().log(
                    action, actor=actor, task_id=tid, person_id=pid,
                    detail={"args": _safe_repr(bound.arguments)},
                )
            except Exception as exc:
                logger.warning("@log_activity wrapper for %s failed: %s", action, exc)
            return result

        return wrapper

    return decorator


def _safe_repr(d: dict[str, Any]) -> dict[str, Any]:
    """Shrink/sanitize argument dict for storage — drop self, str-truncate."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k == "self":
            continue
        try:
            json.dumps(v, default=str)
            out[k] = v
        except Exception:
            out[k] = repr(v)[:200]
    return out

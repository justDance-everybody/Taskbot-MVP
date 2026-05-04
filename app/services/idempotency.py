"""SQLite-backed idempotency store with TTL.

Used to deduplicate Feishu callbacks: each ``card_action_id`` is recorded
on first sight; subsequent attempts within the TTL window are rejected.

Why SQLite (not Redis): zero-dep, survives process restart, cheap enough
for the call volume of a chat-ops bot. Swap to Redis later if multi-instance.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 24 * 3600

_SCHEMA = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    seen_at REAL NOT NULL,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_idempotency_seen_at ON idempotency_keys(seen_at);
"""


class IdempotencyStore:
    """Thread-safe SQLite store. One row per unique key, TTL-pruned on access."""

    def __init__(self, db_path: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
        self.db_path = db_path or settings.idempotency_db_path
        self.ttl_seconds = ttl_seconds or (settings.idempotency_ttl_hours * 3600)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    def seen(self, key: str) -> bool:
        """Return True if ``key`` was already recorded within TTL.

        First call for a key returns False *and* records it atomically.
        """
        if not key:
            return False
        now = time.time()
        cutoff = now - self.ttl_seconds
        with self._lock, self._connect() as conn:
            # Prune expired so the table doesn't grow unbounded.
            conn.execute("DELETE FROM idempotency_keys WHERE seen_at < ?", (cutoff,))
            cur = conn.execute(
                "SELECT seen_at FROM idempotency_keys WHERE key = ?", (key,)
            )
            row = cur.fetchone()
            if row is not None:
                return True
            try:
                conn.execute(
                    "INSERT INTO idempotency_keys (key, seen_at) VALUES (?, ?)",
                    (key, now),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Race: another thread inserted between SELECT and INSERT.
                return True
            return False

    def reset(self) -> None:
        """Test helper: clear all entries."""
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM idempotency_keys")
            conn.commit()


_default_store: Optional[IdempotencyStore] = None
_default_lock = threading.Lock()


def get_default_store() -> IdempotencyStore:
    """Module-level singleton — pytest patches this getter for isolation."""
    global _default_store
    with _default_lock:
        if _default_store is None:
            _default_store = IdempotencyStore()
    return _default_store

"""Unit tests for the SQLite idempotency store."""

from __future__ import annotations

import time
import pytest

from app.services.idempotency import IdempotencyStore


@pytest.fixture
def store(tmp_path):
    return IdempotencyStore(db_path=str(tmp_path / "idem.sqlite3"), ttl_seconds=3600)


def test_first_sighting_records_and_returns_false(store):
    assert store.seen("action_123") is False


def test_duplicate_sighting_returns_true(store):
    store.seen("action_123")
    assert store.seen("action_123") is True


def test_different_keys_isolated(store):
    store.seen("a")
    assert store.seen("b") is False


def test_empty_key_treated_as_miss(store):
    assert store.seen("") is False
    assert store.seen("") is False  # still not deduplicated


def test_expired_keys_pruned(tmp_path):
    s = IdempotencyStore(db_path=str(tmp_path / "i.db"), ttl_seconds=0.05)
    s.seen("k")
    assert s.seen("k") is True
    time.sleep(0.1)
    assert s.seen("k") is False  # expired, treated as new


def test_reset_clears_all(store):
    store.seen("a")
    store.seen("b")
    store.reset()
    assert store.seen("a") is False
    assert store.seen("b") is False

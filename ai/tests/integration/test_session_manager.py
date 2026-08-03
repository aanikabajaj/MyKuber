"""Integration tests for ai/services/session_manager.py.

Tests:
  - Session persists across two calls (save then load).
  - Compression triggers at turn 10 (mock db, messages trimmed to ≤ 3).
  - Redis-down fallback returns session_degraded=True (Redis raises on get).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.services.session_manager import (
    SESSION_TTL,
    SessionState,
    create_or_load_session,
    maybe_compress,
    save_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis(stored: dict | None = None) -> AsyncMock:
    """Return a mock aioredis.Redis with an in-memory store."""
    store: dict = {}

    async def _get(key: str):
        return store.get(key)

    async def _set(key: str, value, ex=None):
        store[key] = value

    async def _delete(key: str):
        store.pop(key, None)

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=_get)
    redis.set = AsyncMock(side_effect=_set)
    redis.delete = AsyncMock(side_effect=_delete)
    return redis


# ---------------------------------------------------------------------------
# Test 1: Session persists across save → load
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_persists_across_save_and_load():
    """A session saved to Redis can be reloaded by its session_id."""
    redis = _make_redis()

    # Create a new session and mutate it
    state, degraded = await create_or_load_session(None, user_id=42, redis=redis)
    assert degraded is False
    original_id = state.session_id

    state.turn_count = 3
    state.conversation_summary = "user asked about stocks"
    state.messages = [{"role": "user", "content": "Hello"}]

    # Save it
    saved = await save_session(state, redis)
    assert saved is True

    # Load it back using the same session_id
    loaded, degraded2 = await create_or_load_session(original_id, user_id=42, redis=redis)
    assert degraded2 is False
    assert loaded.session_id == original_id
    assert loaded.turn_count == 3
    assert loaded.conversation_summary == "user asked about stocks"
    assert loaded.messages == [{"role": "user", "content": "Hello"}]


# ---------------------------------------------------------------------------
# Test 2: Missing key treated as new session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_redis_key_creates_new_session():
    """When session_id is provided but key is absent, a new session is returned."""
    redis = _make_redis()
    # Nothing stored — redis.get returns None for any key
    state, degraded = await create_or_load_session("non-existent-uuid", user_id=7, redis=redis)
    assert degraded is False
    # A brand-new session_id should be generated (different from the supplied one)
    assert state.session_id != "non-existent-uuid"
    assert state.user_id == 7
    assert state.turn_count == 0


# ---------------------------------------------------------------------------
# Test 3: Compression triggers at turn 10
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compression_triggers_at_turn_10():
    """maybe_compress compresses at turn_count == 10, trimming messages to ≤ 3."""
    redis = _make_redis()

    # Build a session at turn 10 with 8 messages
    state = SessionState(
        user_id=1,
        turn_count=10,
        messages=[
            {"role": "user", "content": f"message {i}"}
            for i in range(8)
        ],
    )

    # Mock the DB
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    state, did_compress = await maybe_compress(state, redis, mock_db)

    assert did_compress is True
    # messages trimmed to last 3
    assert len(state.messages) <= 3
    # DB was written
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_compression_does_not_trigger_at_turn_9():
    """maybe_compress does NOT compress at turn_count == 9."""
    redis = _make_redis()
    state = SessionState(
        user_id=1,
        turn_count=9,
        messages=[{"role": "user", "content": f"msg {i}"} for i in range(5)],
    )
    mock_db = AsyncMock()

    state, did_compress = await maybe_compress(state, redis, mock_db)

    assert did_compress is False
    assert len(state.messages) == 5  # untouched
    mock_db.add.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Redis-down fallback sets session_degraded=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_down_fallback_returns_session_degraded():
    """When Redis raises an exception, session_degraded=True is returned."""
    redis = AsyncMock()
    # Make redis.get always raise a connection error
    redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    # Passing a session_id triggers the Redis fetch path
    state, degraded = await create_or_load_session(
        "some-existing-session-id", user_id=99, redis=redis
    )

    assert degraded is True
    # A fresh stateless session is returned
    assert state.user_id == 99
    assert state.turn_count == 0


@pytest.mark.asyncio
async def test_save_session_returns_false_on_redis_error():
    """save_session returns False when Redis raises."""
    redis = AsyncMock()
    redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))

    state = SessionState(user_id=5)
    result = await save_session(state, redis)
    assert result is False


# ---------------------------------------------------------------------------
# Test 5: Compression builds summary from messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compression_builds_summary():
    """compress_session builds a non-empty summary from message content."""
    redis = _make_redis()
    state = SessionState(
        user_id=2,
        turn_count=10,
        messages=[
            {"role": "user", "content": "Tell me about mutual funds"},
            {"role": "assistant", "content": "Mutual funds pool money from many investors"},
        ],
    )
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    state, _ = await maybe_compress(state, redis, mock_db)

    assert "mutual funds" in state.conversation_summary.lower()
    assert len(state.messages) <= 3

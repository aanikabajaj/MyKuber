"""Unit tests for ai/agents/context_manager.py.

All external dependencies (Redis, DB, Memory Service) are mocked.
No real database or Redis connection is required.

Tests:
  1. Empty investment_goals handled gracefully.
  2. PII fields absent from assembled context (raw balance and account number
     must not appear — only masked/bucketed forms).
  3. Redis cache populated (redis.set called) after the cold path.
  4. Cached context returned on second call (redis.get returns a value,
     DB loader not called).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — build lightweight stand-in objects
# ---------------------------------------------------------------------------


def _make_user(
    balance: float = 75_000.0,
    account_number: str = "123456789012",
) -> MagicMock:
    user = MagicMock()
    user.first_name = "Priya"
    user.city = "Amritsar"
    user.state = "Punjab"
    user.balance = balance
    user.account_number = account_number
    user.preferred_language = "en"
    user.face_enabled = True
    user.totp_enabled = False
    user.txn_face_threshold = 10_000
    return user


def _make_profile(investment_goals: list | None = None) -> MagicMock:
    profile = MagicMock()
    profile.risk_profile = "moderate"
    profile.investment_goals = investment_goals if investment_goals is not None else []
    profile.holdings = []
    profile.sip_details = []
    profile.investment_horizon_years = 5
    profile.preferred_asset_classes = []
    return profile


def _make_transaction(amount: float = 500.0) -> MagicMock:
    txn = MagicMock()
    txn.amount = amount
    txn.note = "Grocery run"
    txn.beneficiary_name = "BigBazaar"
    txn.status = "completed"
    txn.created_at = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    return txn


def _make_state(session_id: str = "sess-abc") -> dict[str, Any]:
    return {
        "user_id": 42,
        "session_id": session_id,
        "session_state": {"conversation_summary": "User asked about SIP."},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def redis_mock() -> AsyncMock:
    """Redis client mock with cache miss by default."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)   # cache miss
    r.set = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_investment_goals_handled_gracefully(redis_mock: AsyncMock):
    """Profile with investment_goals=[] must not raise and must include the key."""
    user = _make_user()
    profile = _make_profile(investment_goals=[])
    txn = _make_transaction()
    state = _make_state()

    with (
        patch("ai.agents.context_manager.get_redis", return_value=redis_mock),
        patch(
            "ai.agents.context_manager.asyncio.get_running_loop"
        ) as mock_loop,
        patch("ai.agents.context_manager.get_profile", new_callable=AsyncMock, return_value=profile),
        patch("ai.agents.context_manager.AIAsyncSession") as mock_ai_session,
    ):
        # Simulate run_in_executor returning (user, [txn])
        fake_loop = MagicMock()
        fake_loop.run_in_executor = AsyncMock(return_value=(user, [txn]))
        mock_loop.return_value = fake_loop

        # AIAsyncSession used as async context manager
        mock_ai_db = AsyncMock()
        mock_ai_session.return_value.__aenter__ = AsyncMock(return_value=mock_ai_db)
        mock_ai_session.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai.agents.context_manager import context_manager_node

        result = await context_manager_node(state)

    ctx = result["user_context"]
    assert "financial_profile" in ctx
    assert ctx["financial_profile"]["investment_goals"] == []


@pytest.mark.asyncio
async def test_pii_fields_absent_from_context(redis_mock: AsyncMock):
    """Raw balance and full account number must NOT appear in assembled context."""
    raw_balance = 75_000.0
    raw_account = "123456789012"
    user = _make_user(balance=raw_balance, account_number=raw_account)
    profile = _make_profile()
    txn = _make_transaction()
    state = _make_state()

    with (
        patch("ai.agents.context_manager.get_redis", return_value=redis_mock),
        patch("ai.agents.context_manager.asyncio.get_running_loop") as mock_loop,
        patch("ai.agents.context_manager.get_profile", new_callable=AsyncMock, return_value=profile),
        patch("ai.agents.context_manager.AIAsyncSession") as mock_ai_session,
    ):
        fake_loop = MagicMock()
        fake_loop.run_in_executor = AsyncMock(return_value=(user, [txn]))
        mock_loop.return_value = fake_loop

        mock_ai_db = AsyncMock()
        mock_ai_session.return_value.__aenter__ = AsyncMock(return_value=mock_ai_db)
        mock_ai_session.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai.agents.context_manager import context_manager_node

        result = await context_manager_node(state)

    ctx = result["user_context"]
    user_ctx = ctx["user"]

    # Raw balance must not be present
    assert "balance" not in user_ctx, "Raw balance must not appear in user context"
    # Raw account number must not be present
    assert "account_number" not in user_ctx, "Raw account number must not appear in user context"

    # Masked / bucketed forms MUST be present
    assert "balance_bucket" in user_ctx
    assert "account_number_masked" in user_ctx

    # The masked account should start with ****
    assert user_ctx["account_number_masked"].startswith("****")

    # Serialise to JSON and verify raw values don't leak
    serialised = json.dumps(ctx)
    assert raw_account not in serialised, "Full account number leaked into serialised context"
    # Raw balance as a bare number string should not appear
    assert str(int(raw_balance)) not in serialised, "Raw balance leaked into serialised context"


@pytest.mark.asyncio
async def test_redis_cache_populated_after_cold_path(redis_mock: AsyncMock):
    """After a cold-path assembly, redis.set must be called to cache the context."""
    user = _make_user()
    profile = _make_profile()
    txn = _make_transaction()
    state = _make_state()

    with (
        patch("ai.agents.context_manager.get_redis", return_value=redis_mock),
        patch("ai.agents.context_manager.asyncio.get_running_loop") as mock_loop,
        patch("ai.agents.context_manager.get_profile", new_callable=AsyncMock, return_value=profile),
        patch("ai.agents.context_manager.AIAsyncSession") as mock_ai_session,
    ):
        fake_loop = MagicMock()
        fake_loop.run_in_executor = AsyncMock(return_value=(user, [txn]))
        mock_loop.return_value = fake_loop

        mock_ai_db = AsyncMock()
        mock_ai_session.return_value.__aenter__ = AsyncMock(return_value=mock_ai_db)
        mock_ai_session.return_value.__aexit__ = AsyncMock(return_value=False)

        from ai.agents.context_manager import context_manager_node

        await context_manager_node(state)

    # redis.set must have been called once with the cache key and ex=30
    redis_mock.set.assert_called_once()
    call_args = redis_mock.set.call_args
    positional = call_args[0]
    kwargs = call_args[1]

    assert positional[0] == "ctx:42:sess-abc", "Wrong cache key"
    assert kwargs.get("ex") == 30 or (len(call_args[0]) >= 3 and call_args[0][2] == 30), (
        "Cache TTL must be 30 seconds"
    )


@pytest.mark.asyncio
async def test_cached_context_returned_on_hit(redis_mock: AsyncMock):
    """When redis.get returns a value, the DB loader must NOT be called."""
    cached_ctx: dict[str, Any] = {
        "user": {"first_name": "Cached"},
        "financial_profile": {"risk_profile": "low", "investment_goals": []},
        "transactions": [],
        "conversation_summary": "Prior summary.",
    }
    redis_mock.get = AsyncMock(return_value=json.dumps(cached_ctx).encode())

    state = _make_state()

    with (
        patch("ai.agents.context_manager.get_redis", return_value=redis_mock),
        patch(
            "ai.agents.context_manager.asyncio.get_running_loop"
        ) as mock_loop,
        patch("ai.agents.context_manager.get_profile", new_callable=AsyncMock) as mock_get_profile,
        patch("ai.agents.context_manager.AIAsyncSession") as mock_ai_session,
    ):
        fake_loop = MagicMock()
        # run_in_executor should NOT be called on a cache hit
        fake_loop.run_in_executor = AsyncMock(side_effect=AssertionError("DB must not be called on cache hit"))
        mock_loop.return_value = fake_loop

        from ai.agents.context_manager import context_manager_node

        result = await context_manager_node(state)

    # DB and profile service must not have been invoked
    mock_get_profile.assert_not_called()
    mock_ai_session.assert_not_called()

    # Returned context must match the cached value
    assert result["user_context"]["user"]["first_name"] == "Cached"
    assert result["user_context"]["conversation_summary"] == "Prior summary."

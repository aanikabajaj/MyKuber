"""Unit tests for ai/services/memory_service.py.

Tests:
  - Profile created on first access with default values (mock DB returns no row).
  - Cache invalidated on update (redis.delete called after commit).
  - 20-summary cap enforced (add 25 summaries, check len ≤ 20).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from ai.models.ai_tables import AIFinancialProfile
from ai.services.memory_service import (
    MEM_TTL,
    _mem_key,
    append_conversation_summary,
    get_profile,
    update_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis(cached_json: str | None = None) -> AsyncMock:
    """Return a mock aioredis.Redis instance."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=cached_json)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


def _make_db(profile: AIFinancialProfile | None = None) -> AsyncMock:
    """Return a mock AsyncSession that returns the given profile on query."""
    db = AsyncMock()

    # Build mock execute result
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = profile
    db.execute = AsyncMock(return_value=scalar_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Test 1: Profile created on first access with default values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_created_with_defaults_when_not_found():
    """When no Redis cache and no DB row, a default profile is created and saved."""
    redis = _make_redis(cached_json=None)  # no cache
    db = _make_db(profile=None)  # no existing row

    profile = await get_profile(user_id=1, redis=redis, db=db)

    # DB.add must have been called (to persist the new profile)
    db.add.assert_called_once()
    db.commit.assert_awaited_once()

    # Returned profile has expected defaults
    assert profile.user_id == 1
    assert profile.risk_profile == "moderate"
    assert profile.investment_horizon_years == 5
    assert profile.investment_goals == []
    assert profile.holdings == []
    assert profile.sip_details == []
    assert profile.preferred_asset_classes == []
    assert profile.conversation_summaries == []


@pytest.mark.asyncio
async def test_profile_returned_from_db_when_exists():
    """When a DB row exists, it is returned and cached in Redis."""
    redis = _make_redis(cached_json=None)
    existing = AIFinancialProfile(
        user_id=2,
        risk_profile="aggressive",
        investment_goals=["retirement"],
        holdings=[],
        sip_details=[],
        investment_horizon_years=10,
        preferred_asset_classes=["equity"],
        conversation_summaries=[],
    )
    db = _make_db(profile=existing)

    profile = await get_profile(user_id=2, redis=redis, db=db)

    assert profile.risk_profile == "aggressive"
    assert profile.investment_horizon_years == 10
    # Redis.set should have been called to populate the cache
    redis.set.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2: Cache invalidated on update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_invalidated_on_update():
    """After updating a profile, redis.delete is called to invalidate the cache."""
    redis = _make_redis(cached_json=None)
    existing = AIFinancialProfile(
        user_id=3,
        risk_profile="moderate",
        investment_goals=[],
        holdings=[],
        sip_details=[],
        investment_horizon_years=5,
        preferred_asset_classes=[],
        conversation_summaries=[],
    )
    db = _make_db(profile=existing)

    await update_profile(
        user_id=3,
        updates={"risk_profile": "low", "investment_horizon_years": 3},
        redis=redis,
        db=db,
    )

    # redis.delete must be called with the correct key
    redis.delete.assert_awaited_with(_mem_key(3))


@pytest.mark.asyncio
async def test_update_applies_only_allowed_fields():
    """update_profile ignores fields not in the allowed set."""
    redis = _make_redis(cached_json=None)
    existing = AIFinancialProfile(
        user_id=4,
        risk_profile="moderate",
        investment_goals=[],
        holdings=[],
        sip_details=[],
        investment_horizon_years=5,
        preferred_asset_classes=[],
        conversation_summaries=[],
    )
    db = _make_db(profile=existing)

    await update_profile(
        user_id=4,
        updates={"risk_profile": "high", "user_id": 9999},  # user_id should be ignored
        redis=redis,
        db=db,
    )

    # risk_profile updated
    assert existing.risk_profile == "high"
    # user_id NOT changed (not in allowed_fields)
    assert existing.user_id == 4


# ---------------------------------------------------------------------------
# Test 3: 20-summary cap enforced
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_twenty_summary_cap_enforced():
    """After appending 25 summaries, conversation_summaries has at most 20 entries."""
    profile = AIFinancialProfile(
        user_id=5,
        risk_profile="moderate",
        investment_goals=[],
        holdings=[],
        sip_details=[],
        investment_horizon_years=5,
        preferred_asset_classes=[],
        conversation_summaries=[],
    )
    db = _make_db(profile=profile)
    redis = _make_redis(cached_json=None)

    # Append 25 summaries one by one
    for i in range(25):
        # Each time get_profile is called it returns the same object (already mutated)
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = profile
        db.execute = AsyncMock(return_value=scalar_result)

        await append_conversation_summary(
            user_id=5,
            summary=f"summary {i}",
            redis=redis,
            db=db,
        )

    assert len(profile.conversation_summaries) <= 20


@pytest.mark.asyncio
async def test_twenty_summary_cap_keeps_most_recent():
    """The cap keeps the 20 MOST RECENT summaries, dropping the oldest."""
    profile = AIFinancialProfile(
        user_id=6,
        risk_profile="moderate",
        investment_goals=[],
        holdings=[],
        sip_details=[],
        investment_horizon_years=5,
        preferred_asset_classes=[],
        conversation_summaries=[f"old-{i}" for i in range(19)],  # start with 19
    )
    db = _make_db(profile=profile)
    redis = _make_redis(cached_json=None)

    # Append 3 more (total 22 → trimmed to 20)
    for i in range(3):
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = profile
        db.execute = AsyncMock(return_value=scalar_result)
        await append_conversation_summary(
            user_id=6, summary=f"new-{i}", redis=redis, db=db
        )

    assert len(profile.conversation_summaries) == 20
    # Most recent entries should include the newly added ones
    assert "new-2" in profile.conversation_summaries
    # The very first "old-0" should have been dropped
    assert "old-0" not in profile.conversation_summaries

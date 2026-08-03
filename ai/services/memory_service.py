"""Memory Service — per-user financial profiles backed by AI_PostgreSQL + Redis cache.

Redis key: mem:{user_id} → JSON AIFinancialProfile, TTL 300s (5 min).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ai.models.ai_tables import AIFinancialProfile, AISessionArchive, AIDocumentMetadata

MEM_TTL = 300  # 5 minutes


def _mem_key(user_id: int) -> str:
    return f"mem:{user_id}"


def _profile_to_dict(profile: AIFinancialProfile) -> dict:
    return {
        "user_id": profile.user_id,
        "risk_profile": profile.risk_profile,
        "investment_goals": profile.investment_goals or [],
        "holdings": profile.holdings or [],
        "sip_details": profile.sip_details or [],
        "investment_horizon_years": profile.investment_horizon_years,
        "preferred_asset_classes": profile.preferred_asset_classes or [],
        "conversation_summaries": profile.conversation_summaries or [],
        "last_updated_at": profile.last_updated_at.isoformat() if profile.last_updated_at else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


async def get_profile(
    user_id: int,
    redis: aioredis.Redis,
    db: AsyncSession,
) -> AIFinancialProfile:
    """Get profile from Redis cache; fall back to DB; create default if not found."""
    # Try Redis
    try:
        raw = await redis.get(_mem_key(user_id))
        if raw:
            data = json.loads(raw)
            profile = AIFinancialProfile(
                **{k: v for k, v in data.items() if k not in ("last_updated_at", "created_at")}
            )
            return profile
    except Exception:
        pass

    # Try DB
    result = await db.execute(
        select(AIFinancialProfile).where(AIFinancialProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        # Create default empty profile
        profile = AIFinancialProfile(
            user_id=user_id,
            risk_profile="moderate",
            investment_goals=[],
            holdings=[],
            sip_details=[],
            investment_horizon_years=5,
            preferred_asset_classes=[],
            conversation_summaries=[],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    # Cache it
    try:
        await redis.set(_mem_key(user_id), json.dumps(_profile_to_dict(profile)), ex=MEM_TTL)
    except Exception:
        pass

    return profile


async def update_profile(
    user_id: int,
    updates: dict,
    redis: aioredis.Redis,
    db: AsyncSession,
) -> AIFinancialProfile:
    """Apply partial updates to profile, commit to DB, invalidate Redis."""
    profile = await get_profile(user_id, redis, db)

    allowed_fields = {
        "risk_profile", "investment_goals", "holdings", "sip_details",
        "investment_horizon_years", "preferred_asset_classes",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(profile, field, value)

    profile.last_updated_at = datetime.now(timezone.utc)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # Invalidate cache immediately
    try:
        await redis.delete(_mem_key(user_id))
    except Exception:
        pass

    return profile


async def append_conversation_summary(
    user_id: int,
    summary: str,
    redis: aioredis.Redis,
    db: AsyncSession,
) -> None:
    """Append summary to conversation_summaries, keep at most 20."""
    profile = await get_profile(user_id, redis, db)
    summaries = list(profile.conversation_summaries or [])
    summaries.append(summary)
    summaries = summaries[-20:]  # keep most recent 20
    profile.conversation_summaries = summaries
    profile.last_updated_at = datetime.now(timezone.utc)
    db.add(profile)
    await db.commit()
    try:
        await redis.delete(_mem_key(user_id))
    except Exception:
        pass


async def delete_profile(
    user_id: int,
    redis: aioredis.Redis,
    db: AsyncSession,
) -> None:
    """Delete all user data from DB and Redis (data erasure)."""
    await db.execute(
        delete(AIFinancialProfile).where(AIFinancialProfile.user_id == user_id)
    )
    await db.execute(
        delete(AISessionArchive).where(AISessionArchive.user_id == user_id)
    )
    await db.execute(
        delete(AIDocumentMetadata).where(AIDocumentMetadata.id == user_id)
    )  # metadata only
    await db.commit()
    try:
        await redis.delete(_mem_key(user_id))
        # Scan and delete session keys for this user
        async for key in redis.scan_iter("session:*"):
            try:
                raw = await redis.get(key)
                if raw:
                    data = json.loads(raw)
                    if data.get("user_id") == user_id:
                        await redis.delete(key)
            except Exception:
                pass
    except Exception:
        pass

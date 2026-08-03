"""Session Manager — per-conversation state stored in Redis.

Redis key: session:{session_id} → JSON SessionState, TTL 1800s (30 min).
On Redis unavailability, falls back to stateless operation with session_degraded=True.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

import redis.asyncio as aioredis


class SessionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int
    active_workflow: str | None = None
    conversation_summary: str = ""
    auth_context: dict[str, Any] = Field(default_factory=dict)
    turn_count: int = 0
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: list[dict] = Field(default_factory=list)

    @field_serializer("last_activity_at")
    def _serialize_dt(self, v: datetime) -> str:
        return v.isoformat()


SESSION_TTL = 1800  # 30 minutes


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def create_or_load_session(
    session_id: str | None,
    user_id: int,
    redis: aioredis.Redis,
) -> tuple[SessionState, bool]:
    """Return (SessionState, session_degraded).

    Generates a new UUID v4 session_id when session_id is None.
    Loads from Redis when session_id provided; treats missing key as new.
    Falls back to new session if Redis is unavailable.
    """
    degraded = False
    if session_id is not None:
        try:
            raw = await redis.get(_session_key(session_id))
            if raw:
                data = json.loads(raw)
                state = SessionState.model_validate(data)
                state.last_activity_at = datetime.now(timezone.utc)
                return state, degraded
        except Exception:
            degraded = True
    # New session
    return SessionState(user_id=user_id), degraded


async def save_session(state: SessionState, redis: aioredis.Redis) -> bool:
    """Serialise and save session to Redis. Returns True on success."""
    try:
        key = _session_key(state.session_id)
        payload = state.model_dump_json()
        await redis.set(key, payload, ex=SESSION_TTL)
        return True
    except Exception:
        return False


async def compress_session(
    state: SessionState,
    redis: aioredis.Redis,
    db,  # AsyncSession for AI_PostgreSQL
) -> SessionState:
    """Compress session: summarise messages, archive to DB, trim to last 3 turns."""
    from ai.models.ai_tables import AISessionArchive

    # Extractive summary: join last turn messages as plain text
    summary_parts = []
    for msg in state.messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if content:
            summary_parts.append(f"{role}: {content[:200]}")
    summary = "\n".join(summary_parts[:10])
    if state.conversation_summary:
        summary = state.conversation_summary + "\n\n" + summary
    state.conversation_summary = summary[:2000]  # truncate

    # Persist to ai_session_archive
    archive = AISessionArchive(
        session_id=state.session_id,
        user_id=state.user_id,
        conversation_summary=state.conversation_summary,
        turn_count=state.turn_count,
    )
    db.add(archive)
    await db.commit()

    # Keep only last 3 messages in Redis
    state.messages = state.messages[-3:]
    return state


async def maybe_compress(
    state: SessionState,
    redis: aioredis.Redis,
    db,
) -> tuple[SessionState, bool]:
    """Compress if turn_count is a multiple of 10. Returns (state, did_compress)."""
    if state.turn_count > 0 and state.turn_count % 10 == 0:
        state = await compress_session(state, redis, db)
        return state, True
    return state, False

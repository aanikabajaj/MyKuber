from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
import httpx
from ai.core.config import settings
from ai.database.ai_db import ai_async_engine, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    status = {}

    # Redis
    try:
        redis = get_redis()
        await asyncio.wait_for(redis.ping(), timeout=1.0)
        status["redis"] = "connected"
    except Exception:
        status["redis"] = "unavailable"

    # Qdrant
    try:
        headers = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
        async with httpx.AsyncClient() as client:
            r = await asyncio.wait_for(
                client.get(f"{settings.QDRANT_URL}/healthz", headers=headers), timeout=3.0
            )
            status["qdrant"] = "connected" if r.status_code == 200 else "unavailable"
    except Exception:
        status["qdrant"] = "unavailable"

    # LLM (self-hosted vLLM or any hosted OpenAI-compatible provider)
    try:
        async with httpx.AsyncClient() as client:
            r = await asyncio.wait_for(
                client.get(
                    f"{settings.VLLM_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {settings.VLLM_API_KEY}"},
                ),
                timeout=1.0,
            )
            status["vllm"] = "connected" if r.status_code == 200 else "unavailable"
    except Exception:
        status["vllm"] = "unavailable"

    # AI DB
    try:
        import sqlalchemy
        async with ai_async_engine.connect() as conn:
            await asyncio.wait_for(
                conn.execute(sqlalchemy.text("SELECT 1")), timeout=1.0
            )
        status["ai_db"] = "connected"
    except Exception:
        status["ai_db"] = "unavailable"

    overall = "healthy" if all(v == "connected" for v in status.values()) else "degraded"
    return {
        "status": overall,
        **status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

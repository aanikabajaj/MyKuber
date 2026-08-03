"""Database session factories and connection helpers for the AI module.

Three session providers:
  - get_readonly_db()  — sync read-only session bound to the IAARE backend database
  - get_ai_db()        — async session for the dedicated AI PostgreSQL database
  - get_redis()        — Redis connection from a shared async connection pool
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

# Re-use the IAARE backend engine (same process, read-only usage only)
from app.core.database import engine as iaare_engine

from ai.core.config import settings

# ---------------------------------------------------------------------------
# Task 2.1 — Read-only session for the IAARE backend database
# ---------------------------------------------------------------------------

ReadOnlySessionLocal = sessionmaker(
    bind=iaare_engine,
    autoflush=False,
    autocommit=False,
)


def get_readonly_db():
    """FastAPI dependency: yields a read-only SQLAlchemy session for the IAARE DB.

    The session is never committed.  A DB-level read-only flag is also set
    depending on the underlying engine dialect:
      • SQLite  → ``PRAGMA query_only = ON``
      • Any other (PostgreSQL, …) → ``SET TRANSACTION READ ONLY``
    """
    db = ReadOnlySessionLocal()
    try:
        if settings.IAARE_DATABASE_URL.startswith("sqlite"):
            db.execute(text("PRAGMA query_only = ON"))
        else:
            db.execute(text("SET TRANSACTION READ ONLY"))
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task 2.2 — Async session for the AI-specific PostgreSQL database
# ---------------------------------------------------------------------------

ai_async_engine = create_async_engine(
    settings.async_ai_database_url,
    pool_pre_ping=True,
)

AIAsyncSession = async_sessionmaker(
    ai_async_engine,
    expire_on_commit=False,
)


async def get_ai_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async SQLAlchemy session for AI_PostgreSQL."""
    async with AIAsyncSession() as session:
        yield session


# ---------------------------------------------------------------------------
# Task 2.3 — Redis async connection pool
# ---------------------------------------------------------------------------

redis_pool = redis.asyncio.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
)


def get_redis() -> redis.asyncio.Redis:
    """Return an async Redis client backed by the shared connection pool."""
    return redis.asyncio.Redis(connection_pool=redis_pool)

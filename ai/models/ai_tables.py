"""SQLAlchemy 2.0 mapped classes for the AI module's dedicated PostgreSQL database.

All four tables use a separate ``AIBase`` so they are never mixed with the IAARE
backend's ``Base`` and are always created/migrated independently.

Tables
------
- ai_financial_profiles   — per-user financial profile + conversation summaries
- ai_execution_traces     — LangGraph request traces for observability
- ai_session_archive      — compressed conversation archives
- ai_document_metadata    — RAG document ingestion records
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ai.database.ai_db import ai_async_engine


# ---------------------------------------------------------------------------
# Declarative base (separate from IAARE's Base)
# ---------------------------------------------------------------------------


class AIBase(DeclarativeBase):
    """Declarative base for all AI-module ORM models."""


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Table: ai_financial_profiles
# ---------------------------------------------------------------------------


class AIFinancialProfile(AIBase):
    """Per-user financial profile stored in AI_PostgreSQL.

    ``user_id`` is a logical FK to the IAARE backend's ``users.id``; no
    database-level FK constraint is created because the two databases are
    separate.
    """

    __tablename__ = "ai_financial_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    risk_profile: Mapped[str] = mapped_column(String(20), default="moderate")
    investment_goals: Mapped[list] = mapped_column(JSON, default=list)
    holdings: Mapped[list] = mapped_column(JSON, default=list)
    sip_details: Mapped[list] = mapped_column(JSON, default=list)
    investment_horizon_years: Mapped[int] = mapped_column(Integer, default=5)
    preferred_asset_classes: Mapped[list] = mapped_column(JSON, default=list)
    conversation_summaries: Mapped[list] = mapped_column(JSON, default=list)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )


# ---------------------------------------------------------------------------
# Table: ai_execution_traces
# ---------------------------------------------------------------------------


class AIExecutionTrace(AIBase):
    """LangGraph pipeline execution trace (one row per API request)."""

    __tablename__ = "ai_execution_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 of user_id
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    endpoint: Mapped[str] = mapped_column(String(50))
    intent: Mapped[str] = mapped_column(String(50))
    services_invoked: Mapped[list] = mapped_column(JSON)
    node_traces: Mapped[list] = mapped_column(JSON)  # [{node, start_ms, end_ms, error}]
    total_latency_ms: Mapped[int] = mapped_column(Integer)
    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    http_status: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        index=True,
    )


# ---------------------------------------------------------------------------
# Table: ai_session_archive
# ---------------------------------------------------------------------------


class AISessionArchive(AIBase):
    """Compressed conversation archives written on session compression events."""

    __tablename__ = "ai_session_archive"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    conversation_summary: Mapped[str] = mapped_column(Text)
    turn_count: Mapped[int] = mapped_column(Integer)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )


# ---------------------------------------------------------------------------
# Table: ai_document_metadata
# ---------------------------------------------------------------------------


class AIDocumentMetadata(AIBase):
    """Metadata record for each document ingested into the RAG vector store."""

    __tablename__ = "ai_document_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    collection: Mapped[str] = mapped_column(String(50), index=True)
    chunk_count: Mapped[int] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )
    minio_key: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="pending")


# ---------------------------------------------------------------------------
# Startup helper
# ---------------------------------------------------------------------------


async def create_ai_tables() -> None:
    """Create all AI-module tables in AI_PostgreSQL (idempotent).

    Call this once at application startup, e.g. from ``ai/main.py``'s
    ``lifespan`` handler.
    """
    async with ai_async_engine.begin() as conn:
        await conn.run_sync(AIBase.metadata.create_all)

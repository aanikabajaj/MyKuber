"""Context Manager node — assembles the full execution context before any LLM call.

Cache key: ``ctx:{user_id}:{session_id}`` → JSON user_context, TTL 30s.
Cold-path data sources:
  1. User record from IAARE backend (read-only sync session).
  2. AIFinancialProfile from Memory Service (Redis → AI_PostgreSQL).
  3. 90 most recent Transaction records from IAARE backend.
  4. Session summary from orchestrator state.

PII masking is applied before the context is cached or returned.

Node signature: ``async def context_manager_node(state: OrchestratorState) -> dict``
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import select

from ai.database.ai_db import ReadOnlySessionLocal, get_redis, AIAsyncSession
from ai.services.memory_service import get_profile
from ai.security.pii_masker import mask_account_number, bucket_balance
from ai.orchestrator.state import OrchestratorState

# Lazy imports to avoid circular dependencies at module load time
# app.models are imported inside functions

CTX_TTL = 30  # seconds


def _ctx_key(user_id: int, session_id: str | None) -> str:
    return f"ctx:{user_id}:{session_id or 'none'}"


# ---------------------------------------------------------------------------
# Synchronous helper — runs in a thread executor to avoid blocking the event loop
# ---------------------------------------------------------------------------

def _sync_load(user_id: int) -> tuple[Any, list[Any]]:
    """Load User and Transactions synchronously using ReadOnlySessionLocal.

    Returns
    -------
    tuple[User | None, list[Transaction]]
    """
    from app.models.user import User
    from app.models.transaction import Transaction

    db = ReadOnlySessionLocal()
    try:
        user = db.get(User, user_id)

        txn_rows = db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(90)
        ).scalars().all()

        # Detach objects from the session so they're safe to use after db.close()
        transactions = list(txn_rows)
        return user, transactions
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public node
# ---------------------------------------------------------------------------

async def context_manager_node(state: OrchestratorState) -> dict:
    """Assemble and cache the user execution context.

    Returns
    -------
    dict
        ``{"user_context": {...}}`` — merged back into OrchestratorState by LangGraph.
    """
    user_id: int = state["user_id"]
    session_id: str | None = state.get("session_id")
    cache_key = _ctx_key(user_id, session_id)

    redis = get_redis()

    # ------------------------------------------------------------------
    # 1. Cache hit path (TTL 30s)
    # ------------------------------------------------------------------
    try:
        cached = await redis.get(cache_key)
        if cached:
            user_context: dict[str, Any] = json.loads(cached)
            return {"user_context": user_context}
    except Exception:
        pass  # Redis unavailable — continue to cold path

    # ------------------------------------------------------------------
    # 2. Cold path — assemble from all sources
    # ------------------------------------------------------------------

    # 2a & 2c — Load User + Transactions from IAARE backend (sync → executor)
    loop = asyncio.get_running_loop()
    user, transactions = await loop.run_in_executor(None, _sync_load, user_id)

    # 2b — Load financial profile from Memory Service (async AI DB)
    async with AIAsyncSession() as ai_db:
        profile = await get_profile(user_id, redis, ai_db)

    # 2d — Load session summary from orchestrator state
    conversation_summary: str = (
        state.get("session_state", {}).get("conversation_summary", "")
    )

    # ------------------------------------------------------------------
    # 3. Apply PII masking and build context dict
    # ------------------------------------------------------------------
    account_masked = mask_account_number(getattr(user, "account_number", None) if user else None)
    balance_bucket = bucket_balance(getattr(user, "balance", 0.0) if user else 0.0)

    user_sub: dict[str, Any] = {}
    if user is not None:
        user_sub = {
            "first_name": user.first_name,
            "city": user.city or "",
            "state": user.state or "",
            "balance_bucket": balance_bucket,          # never raw balance
            "preferred_language": user.preferred_language,
            "risk_band": profile.risk_profile,
            "face_enabled": user.face_enabled,
            "totp_enabled": user.totp_enabled,
            "txn_face_threshold": user.txn_face_threshold,
            "account_number_masked": account_masked,   # never raw account number
        }

    financial_profile_sub: dict[str, Any] = {
        "risk_profile": profile.risk_profile,
        "investment_goals": profile.investment_goals or [],
        "holdings": profile.holdings or [],
        "sip_details": profile.sip_details or [],
        "investment_horizon_years": profile.investment_horizon_years,
        "preferred_asset_classes": profile.preferred_asset_classes or [],
    }

    transactions_list = [
        {
            "amount": t.amount,
            "note": t.note,
            "beneficiary_name": t.beneficiary_name,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in transactions
    ]

    user_context = {
        "user": user_sub,
        "financial_profile": financial_profile_sub,
        "transactions": transactions_list,
        "conversation_summary": conversation_summary,
    }

    # ------------------------------------------------------------------
    # 4. Write to Redis cache (TTL 30s)
    # ------------------------------------------------------------------
    try:
        await redis.set(cache_key, json.dumps(user_context), ex=CTX_TTL)
    except Exception:
        pass  # non-fatal — continue without caching

    return {"user_context": user_context}

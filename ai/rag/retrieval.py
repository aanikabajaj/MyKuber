"""Personalised RAG retrieval.

Retrieval flow
--------------
1. Embed query with BGE-M3 (1024-dim).
2. Determine which collections to search — either caller-specified or
   auto-selected from all COLLECTIONS.
3. Fan-out async Qdrant searches (score_threshold=0.55 — slightly looser than
   the generic 0.6 to compensate for priority boosting).
4. Apply personalised score boosting:
      final_score = raw_score * collection_priority_weight
                              * user_relevance_multiplier(user_context, collection)
5. Re-rank by final_score, return global top_k.

User relevance multipliers
--------------------------
The user's account data (from the backend via context_manager) drives
collection weights at query time:

  - balance_bucket / investment_goals → boosts SEBI_Regulations, AMFI_MutualFunds
  - face_enabled / totp_enabled       → boosts RBI_Guidelines (KYC/security)
  - holdings containing "NPS"         → boosts PFRDA_NPS
  - holdings containing "insurance"   → boosts IRDAI_Insurance
  - risk_profile == "high"            → boosts NSE_BSE_Market
  - any UPI / payment goal            → boosts RBI_Guidelines (UPI)
  - preferred_language != "en"        → no change (LLM handles translation)
"""
from __future__ import annotations

import asyncio
from typing import Any

from ai.core.config import settings
from ai.models.rag import RagChunk
from ai.rag.collections import COLLECTIONS, COLLECTION_PRIORITY
from ai.rag.embeddings import embed_query

_qdrant_client = None


def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import AsyncQdrantClient  # type: ignore
        _qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
    return _qdrant_client


# ---------------------------------------------------------------------------
# User-context → collection relevance multiplier
# ---------------------------------------------------------------------------

def _user_relevance_multiplier(user_context: dict[str, Any], collection: str) -> float:
    """Return a multiplier [0.8, 1.5] that boosts/dampens collection score
    based on what we know about this specific user."""
    user     = user_context.get("user", {})
    profile  = user_context.get("financial_profile", {})
    holdings = [str(h).lower() for h in (profile.get("holdings") or [])]
    goals    = [str(g).lower() for g in (profile.get("investment_goals") or [])]
    risk     = (profile.get("risk_profile") or "moderate").lower()
    assets   = [str(a).lower() for a in (profile.get("preferred_asset_classes") or [])]

    boost = 1.0

    if collection == "SEBI_Regulations":
        # Boost for anyone with investment goals or holdings
        if goals or holdings or any("mutual" in a or "equity" in a for a in assets):
            boost = 1.30
        elif risk in ("high", "medium"):
            boost = 1.15

    elif collection == "AMFI_MutualFunds":
        if any("mutual" in g or "sip" in g or "fund" in g for g in goals + holdings + assets):
            boost = 1.30
        elif risk != "low":
            boost = 1.10

    elif collection == "RBI_Guidelines":
        # Face-enabled / TOTP users care more about KYC/security docs
        if user.get("face_enabled") or user.get("totp_enabled"):
            boost = 1.10
        # Anyone with a UPI/payment goal
        if any("upi" in g or "payment" in g or "wallet" in g for g in goals):
            boost = 1.20

    elif collection == "CBDT_Tax":
        # Users with high balance / investments care about tax
        bucket = user.get("balance_bucket", "")
        if "₹1L" in bucket or "₹5L" in bucket or "> ₹10L" in bucket:
            boost = 1.20
        if any("tax" in g or "80c" in g for g in goals):
            boost = 1.30

    elif collection == "PFRDA_NPS":
        if any("nps" in h or "pension" in h or "pfrda" in h for h in holdings + goals):
            boost = 1.40
        elif any("retirement" in g for g in goals):
            boost = 1.20

    elif collection == "IRDAI_Insurance":
        if any("insurance" in h or "irdai" in h or "life" in h or "health" in h
               for h in holdings + goals):
            boost = 1.40

    elif collection == "NSE_BSE_Market":
        if risk == "high":
            boost = 1.20
        if any("equity" in a or "stock" in a for a in assets):
            boost = 1.15

    elif collection == "AA_Framework":
        # Account aggregator docs relevant to connected-bank users
        boost = 1.10

    return boost


# ---------------------------------------------------------------------------
# Public retrieval function
# ---------------------------------------------------------------------------

async def retrieve(
    query: str,
    collections: list[str] | None = None,
    top_k: int = 5,
    user_context: dict[str, Any] | None = None,
) -> list[RagChunk]:
    """Embed query, search collections, apply personalised boosting, return top_k.

    Parameters
    ----------
    query:
        User query string.
    collections:
        Subset of COLLECTIONS to search. Defaults to all.
    top_k:
        Number of results to return.
    user_context:
        The assembled user context from the Context Manager. Used to boost
        collection scores based on the user's profile.
    """
    if collections is None:
        valid = COLLECTIONS
    else:
        valid = [c for c in collections if c in COLLECTIONS]

    if not valid:
        return []

    embedding = await embed_query(query)
    client    = get_qdrant_client()

    # Search each collection with a slightly relaxed threshold
    search_tasks = [
        client.search(
            collection_name=col,
            query_vector=embedding,
            limit=top_k * 2,      # fetch extra; boosting may reorder significantly
            score_threshold=0.55,
        )
        for col in valid
    ]
    responses = await asyncio.gather(*search_tasks, return_exceptions=True)

    all_results: list[RagChunk] = []
    for col, resp in zip(valid, responses):
        if isinstance(resp, Exception):
            continue

        # Collection-level priority weight (from spec)
        priority_weight = COLLECTION_PRIORITY.get(col, 1.0)

        # User-context personalisation boost
        user_boost = 1.0
        if user_context:
            user_boost = _user_relevance_multiplier(user_context, col)

        for hit in resp:
            # Document-level priority boost (higher priority doc → higher weight)
            doc_priority   = hit.payload.get("priority", 5)
            doc_weight     = 1.0 + (5 - min(doc_priority, 5)) * 0.04  # max +0.16

            final_score = hit.score * priority_weight * user_boost * doc_weight

            chunk = RagChunk.from_qdrant_payload(hit.payload, score=final_score)
            all_results.append(chunk)

    # Deduplicate by chunk_id (same chunk can appear from multiple searches
    # if collections overlap) — keep highest score
    seen: dict[str, RagChunk] = {}
    for c in all_results:
        if c.chunk_id not in seen or c.score > seen[c.chunk_id].score:
            seen[c.chunk_id] = c

    ranked = sorted(seen.values(), key=lambda c: c.score, reverse=True)
    return ranked[:top_k]


async def retrieve_for_user(
    query: str,
    user_context: dict[str, Any],
    top_k: int = 5,
) -> list[RagChunk]:
    """Convenience wrapper that always passes user_context."""
    return await retrieve(query=query, top_k=top_k, user_context=user_context)

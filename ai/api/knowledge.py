from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ai.api.deps import get_ai_current_user
from ai.rag.retrieval import retrieve
from ai.rag.collections import COLLECTIONS

router = APIRouter(tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    query: str
    collections: Optional[list[str]] = None


@router.post("/knowledge/query")
async def query_endpoint(
    req: KnowledgeQueryRequest,
    current_user=Depends(get_ai_current_user),
):
    cols = req.collections
    if cols:
        cols = [c for c in cols if c in COLLECTIONS]
    chunks = await retrieve(req.query, collections=cols)
    return {"citations": [c.model_dump() for c in chunks]}

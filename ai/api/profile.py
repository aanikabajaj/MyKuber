from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ai.api.deps import get_ai_current_user
from ai.database.ai_db import get_ai_db, get_redis
from ai.services.memory_service import get_profile, update_profile, _profile_to_dict
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["profile"])


class MemoryUpdateRequest(BaseModel):
    risk_profile: Optional[str] = None
    investment_goals: Optional[list] = None
    holdings: Optional[list] = None
    sip_details: Optional[list] = None
    investment_horizon_years: Optional[int] = None
    preferred_asset_classes: Optional[list] = None


@router.get("/profile")
async def get_profile_endpoint(
    current_user=Depends(get_ai_current_user),
    db: AsyncSession = Depends(get_ai_db),
):
    redis = get_redis()
    profile = await get_profile(current_user.id, redis, db)
    return _profile_to_dict(profile)


@router.post("/memory/update")
async def update_memory_endpoint(
    req: MemoryUpdateRequest,
    current_user=Depends(get_ai_current_user),
    db: AsyncSession = Depends(get_ai_db),
):
    redis = get_redis()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    profile = await update_profile(current_user.id, updates, redis, db)
    return _profile_to_dict(profile)

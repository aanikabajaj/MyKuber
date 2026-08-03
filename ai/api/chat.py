from __future__ import annotations
import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from ai.api.deps import get_ai_current_user
from ai.orchestrator.state import initial_state
from ai.orchestrator.graph import graph

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: Optional[str] = None

    @field_validator("session_id")
    @classmethod
    def validate_uuid(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError("session_id must be a valid UUID")
        return v


@router.post("/chat")
async def chat_endpoint(req: ChatRequest, current_user=Depends(get_ai_current_user)):
    request_id = str(uuid.uuid4())
    state = initial_state(
        user_id=current_user.id,
        raw_query=req.message,
        request_id=request_id,
        session_id=req.session_id,
    )
    try:
        result = await asyncio.wait_for(graph.ainvoke(state), timeout=30.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error_code": "PIPELINE_TIMEOUT",
                "message": "Pipeline did not complete within 30 seconds.",
            },
        )
    result_data = result.get("formatted_response", {})
    # Add `response` alias so mobile clients can use either res.response or res.message
    if result_data and "message" in result_data and "response" not in result_data:
        result_data = {**result_data, "response": result_data["message"]}
    return result_data

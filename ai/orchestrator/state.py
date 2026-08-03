from __future__ import annotations
from typing import Any, TypedDict


class OrchestratorState(TypedDict, total=False):
    # Input
    user_id: int
    session_id: str | None
    raw_query: str
    request_id: str
    # Intent routing
    intent: str
    confidence: float
    services: list[str]
    # Context
    user_context: dict[str, Any]
    session_state: dict[str, Any]
    # Service outputs
    portfolio_result: dict | None
    analytics_result: dict | None
    rag_result: dict | None
    llm_response: str | None
    llm_confidence: float
    # Final
    composed_response: dict | None
    safe_response: dict | None
    formatted_response: dict | None
    # Observability
    execution_trace: list[dict]
    session_degraded: bool
    errors: list[str]


def initial_state(
    user_id: int,
    raw_query: str,
    request_id: str,
    session_id: str | None = None,
) -> OrchestratorState:
    return OrchestratorState(
        user_id=user_id,
        session_id=session_id,
        raw_query=raw_query,
        request_id=request_id,
        intent="",
        confidence=0.0,
        services=[],
        user_context={},
        session_state={},
        portfolio_result=None,
        analytics_result=None,
        rag_result=None,
        llm_response=None,
        llm_confidence=0.0,
        composed_response=None,
        safe_response=None,
        formatted_response=None,
        execution_trace=[],
        session_degraded=False,
        errors=[],
    )

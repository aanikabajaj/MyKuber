from __future__ import annotations
import structlog
from ai.orchestrator.state import OrchestratorState

logger = structlog.get_logger()

LATENCY_BUDGETS_MS: dict[str, int] = {
    "intent_router": 2000,
    "context_manager": 1000,
    "rag": 2000,
    "financial_advisor": 15000,
    "portfolio": 10000,
    "safety_layer": 1000,
}


def record_execution_trace(
    state: OrchestratorState,
    node_name: str,
    start_ms: int,
    end_ms: int,
    error: str | None = None,
) -> list[dict]:
    elapsed = end_ms - start_ms
    budget = LATENCY_BUDGETS_MS.get(node_name)
    if budget and elapsed > budget:
        logger.warning(
            "latency_budget_exceeded",
            node=node_name,
            elapsed_ms=elapsed,
            budget_ms=budget,
        )
    entry = {"node": node_name, "start_ms": start_ms, "end_ms": end_ms, "error": error}
    return list(state.get("execution_trace", [])) + [entry]

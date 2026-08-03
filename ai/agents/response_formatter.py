"""Response Formatter — enforces the final JSON schema for all /ai/* endpoints."""
from __future__ import annotations
from ai.orchestrator.state import OrchestratorState

REQUIRED_KEYS = (
    "session_id",
    "message",
    "charts",
    "recommendations",
    "portfolio",
    "confidence",
    "citations",
    "metadata",
)

def response_formatter_node(state: OrchestratorState) -> dict:
    safe = state.get("safe_response") or {}
    message = safe.get("message") or state.get("llm_response") or ""
    safe_meta = safe.get("metadata") or {}
    citations = safe.get("citations") or []

    # Confidence — default to 0.0
    confidence = state.get("llm_confidence")
    if confidence is None:
        confidence = 0.0

    # Derive latency_ms from execution trace
    trace = state.get("execution_trace") or []
    if trace:
        latency_ms = max(
            (t.get("end_ms", 0) - t.get("start_ms", 0))
            for t in trace
            if t.get("end_ms")
        ) if any(t.get("end_ms") for t in trace) else 0
    else:
        latency_ms = 0

    # Portfolio data
    portfolio_result = state.get("portfolio_result")
    portfolio = []
    if portfolio_result and isinstance(portfolio_result, dict) and "weights" in portfolio_result:
        portfolio = [
            {"asset": k, "weight": v} for k, v in portfolio_result["weights"].items()
        ]

    # Charts from analytics
    analytics = state.get("analytics_result")
    charts = []
    if analytics and isinstance(analytics, dict):
        if "category_breakdown" in analytics:
            charts.append({
                "type": "pie",
                "title": "Spending by Category",
                "data": [
                    {"label": k, "value": v.get("total", 0)}
                    for k, v in analytics["category_breakdown"].items()
                ],
            })
        if "monthly_cashflow" in analytics:
            charts.append({
                "type": "bar",
                "title": "Monthly Cashflow",
                "data": [
                    {"label": m, "value": v.get("net", 0)}
                    for m, v in analytics["monthly_cashflow"].items()
                ],
            })

    metadata = {
        "intent": state.get("intent", ""),
        "services_invoked": state.get("services", []),
        "latency_ms": latency_ms,
        "session_degraded": state.get("session_degraded", False),
        "errors": state.get("errors", []),
        **safe_meta,
    }

    formatted = {
        "session_id": state.get("session_id") or "",
        "message": message,
        "charts": charts,            # always a list, never None
        "recommendations": [],       # placeholder — extended in future
        "portfolio": portfolio,      # always a list, never None
        "confidence": float(confidence),
        "citations": citations,      # always a list, never None
        "metadata": metadata,
    }

    return {"formatted_response": formatted}

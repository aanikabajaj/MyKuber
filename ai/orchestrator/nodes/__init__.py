"""Orchestrator node registry.

Each name here is what LangGraph sees. The real implementations live in
their own modules; we import and re-export them here so the graph builder
has a single, stable import surface.

Stub nodes (decision_planning, portfolio, transaction_analytics,
response_composer) are inline until their dedicated modules are wired in.
"""
from __future__ import annotations

from ai.orchestrator.state import OrchestratorState

# ── Real implementations ──────────────────────────────────────────────────────

from ai.agents.intent_router     import intent_router_node       # noqa: F401
from ai.agents.context_manager   import context_manager_node     # noqa: F401
from ai.agents.financial_advisor import financial_advisor_node   # noqa: F401
from ai.security.safety_layer    import safety_layer_node        # noqa: F401
from ai.agents.response_formatter import response_formatter_node # noqa: F401

# ── Inline stubs (will be replaced when dedicated modules are ready) ──────────

async def decision_planning_node(state: OrchestratorState) -> dict:
    """Route services based on the classified intent."""
    intent   = state.get("intent", "Banking")
    services = state.get("services", [])
    # Ensure financial_advisor is always included
    if "financial_advisor" not in services:
        services = list(services) + ["financial_advisor"]
    return {"services": services}


async def portfolio_node(state: OrchestratorState) -> dict:
    """Run portfolio optimisation when requested."""
    try:
        from ai.portfolio.optimizer import optimise_portfolio  # noqa: PLC0415
        import pandas as pd                                     # noqa: PLC0415

        req = state.get("portfolio_request") or {}
        assets = req.get("assets", [])
        if len(assets) < 2:
            return {"portfolio_result": {"error_code": "INSUFFICIENT_ASSETS",
                                         "message": "Need ≥2 assets."}}

        returns_data = {a["symbol"]: a["returns"] for a in assets}
        df           = pd.DataFrame(returns_data)
        risk_band    = (state.get("user_context", {})
                            .get("user", {})
                            .get("risk_band", "medium"))
        opt_type     = req.get("optimization_type", "max_sharpe")
        result       = optimise_portfolio(df, risk_band, opt_type)
        from ai.models.portfolio import PortfolioError  # noqa: PLC0415
        if isinstance(result, PortfolioError):
            return {"portfolio_result": result.model_dump()}
        return {"portfolio_result": result.model_dump()}
    except Exception as exc:
        return {"portfolio_result": None, "errors": (state.get("errors") or []) + [str(exc)]}


async def transaction_analytics_node(state: OrchestratorState) -> dict:
    """Run transaction analytics on the user's recent transactions."""
    try:
        from ai.services.transaction_analytics import (  # noqa: PLC0415
            categorise_transaction,
            compute_monthly_cashflow,
            compute_category_breakdown,
            detect_recurring_transactions,
            detect_anomaly_spikes,
            compute_income_trend,
        )
        txns = (state.get("user_context") or {}).get("transactions", [])
        for t in txns:
            t["category"] = categorise_transaction(
                t.get("beneficiary_name", ""), t.get("note", "")
            )
        result = {
            "monthly_cashflow":         compute_monthly_cashflow(txns, None, None),
            "category_breakdown":       compute_category_breakdown(txns),
            "recurring_transactions":   detect_recurring_transactions(txns),
            "anomaly_spikes":           detect_anomaly_spikes(txns),
            "income_trend":             compute_income_trend(txns),
        }
        return {"analytics_result": result}
    except Exception as exc:
        return {"analytics_result": None, "errors": (state.get("errors") or []) + [str(exc)]}


async def response_composer_node(state: OrchestratorState) -> dict:
    """Merge outputs from all service nodes into composed_response."""
    composed = {
        "message":          state.get("llm_response") or "",
        "portfolio_result": state.get("portfolio_result"),
        "analytics_result": state.get("analytics_result"),
        "rag_result":       state.get("rag_result"),
        "citations": [
            chunk if isinstance(chunk, dict) else chunk.model_dump()
            for chunk in (state.get("rag_result") or [])
            if chunk
        ],
    }
    return {"composed_response": composed}

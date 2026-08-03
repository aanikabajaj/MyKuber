from __future__ import annotations
from ai.orchestrator.state import OrchestratorState

SERVICE_NODE_MAP: dict[str, str] = {
    "portfolio": "portfolio",
    "transaction_analytics": "transaction_analytics",
    "financial_advisor": "financial_advisor",
    "rag": "financial_advisor",
}


def route_services(state: OrchestratorState) -> list[str]:
    services = state.get("services", [])
    seen: set[str] = set()
    targets: list[str] = []
    for svc in services:
        node = SERVICE_NODE_MAP.get(svc)
        if node and node not in seen:
            seen.add(node)
            targets.append(node)
    if "financial_advisor" not in seen:
        targets.append("financial_advisor")
    return targets if targets else ["financial_advisor"]

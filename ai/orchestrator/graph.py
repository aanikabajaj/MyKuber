from langgraph.graph import StateGraph, END
from ai.orchestrator.state import OrchestratorState
from ai.orchestrator.nodes import (
    intent_router_node,
    context_manager_node,
    decision_planning_node,
    portfolio_node,
    transaction_analytics_node,
    financial_advisor_node,
    response_composer_node,
    safety_layer_node,
    response_formatter_node,
)
from ai.orchestrator.router import route_services


def build_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("intent_router", intent_router_node)
    g.add_node("context_manager", context_manager_node)
    g.add_node("decision_planner", decision_planning_node)
    g.add_node("portfolio", portfolio_node)
    g.add_node("transaction_analytics", transaction_analytics_node)
    g.add_node("financial_advisor", financial_advisor_node)
    g.add_node("response_composer", response_composer_node)
    g.add_node("safety_layer", safety_layer_node)
    g.add_node("response_formatter", response_formatter_node)

    g.set_entry_point("intent_router")
    g.add_edge("intent_router", "context_manager")
    g.add_edge("context_manager", "decision_planner")
    g.add_conditional_edges("decision_planner", route_services)
    g.add_edge("portfolio", "response_composer")
    g.add_edge("transaction_analytics", "response_composer")
    g.add_edge("financial_advisor", "response_composer")
    g.add_edge("response_composer", "safety_layer")
    g.add_edge("safety_layer", "response_formatter")
    g.add_edge("response_formatter", END)
    return g.compile()


graph = build_graph()

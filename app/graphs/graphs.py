# app/graphs/main_graph.py (예시)
from typing import Literal
from langgraph.graph import StateGraph, START, END
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.classification_node import read_email, classify_intent
from app.graphs.nodes.plan_node import plan_action
from app.graphs.nodes.approval_node import approval_node


def route_after_classification(
    state: EmailAgentState,
) -> Literal[END, "plan_node", "approval_node"]:
    classification = state["classification"]
    if classification is None:
        return END
    if classification["category"] == "spam":
        return END
    if classification["urgency"] == "high":
        return "approval_node"
    return "plan_node"


graph = StateGraph(EmailAgentState)

graph.add_node("read_email", read_email)
graph.add_node("classification_node", classify_intent)
graph.add_node("plan_node", plan_action)
graph.add_node("approval_node", approval_node)

graph.add_edge(START, "read_email")
graph.add_edge("read_email", "classification_node")

# spam → 종료, urgency high → 승인 노드, 그 외 → plan
graph.add_conditional_edges(
    "classification_node",
    route_after_classification,
)

# 승인 후 흐름은 제품 정책에 맞게 조정 (예: plan_node 또는 END)
graph.add_edge("approval_node", END)

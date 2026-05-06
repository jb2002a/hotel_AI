# app/graphs/main_graph.py (예시)
from typing import Literal
from langgraph.graph import StateGraph, START, END
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.classification_node import read_email, classify_node
from app.graphs.nodes.approval_node import approval_node
from app.graphs.nodes.plan_node import plan_action
from app.graphs.nodes.retrieve_node import retrieve_from_vector_store
from app.graphs.nodes.draft_node import draft_node


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

def route_after_plan(
    state: EmailAgentState,
) -> Literal["retrieve_node", "draft_node"]:
    plan = state.get("plan")
    actions = plan.get("actions", []) if plan else []
    if "retrieve" in actions:
        return "retrieve_node"
    return "draft_node"

graph = StateGraph(EmailAgentState)

graph.add_node("read_email_node", read_email)
graph.add_node("classification_node", classify_node)
graph.add_node("approval_node", approval_node)
graph.add_node("plan_node", plan_action)
graph.add_node("retrieve_node", retrieve_from_vector_store)
graph.add_node("draft_node", draft_node)

graph.add_edge(START, "read_email_node")
graph.add_edge("read_email_node", "classification_node")

# spam → 종료, urgency high → 승인 노드, 그 외 → plan
graph.add_conditional_edges(
    "classification_node",
    route_after_classification,
)

graph.add_conditional_edges(
    "plan_node",
    route_after_plan,
)

graph.add_edge("retrieve_node", "draft_node")
graph.add_edge("draft_node", END)


if __name__ == "__main__":
    # python -m app.graphs.graphs
    compiled_graph = graph.compile()
    result = compiled_graph.invoke(
        {
            "email_data": None,
            "classification": None,
            "plan": None,
            "search_results": None,
            "draft_response": None,
        }
    )
    print(result)
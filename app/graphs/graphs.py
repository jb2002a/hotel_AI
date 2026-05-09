# app/graphs/main_graph.py (예시)
from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.control import approval_node
from app.graphs.nodes.intake import classify_node, read_email
from app.graphs.nodes.planning import booking_plan_node, plan_action
from app.graphs.nodes.response import draft_node, send_email_node
from app.graphs.nodes.retrieval import db_retrieve, vector_retrieve

# 자식 클래스에서 던진 except를 그래프를 깨지않고 처리하기 위해 래핑
def _guard_business_error(node_fn: Callable[[EmailAgentState], dict]) -> Callable[[EmailAgentState], dict]:
    def _wrapped(state: EmailAgentState) -> dict:
        try:
            return node_fn(state)
        except BusinessError as exc:
            return {
                "business_error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            }

    return _wrapped

def route_after_classification(
    state: EmailAgentState,
) -> Literal[END, "plan_node", "approval_node"]:
    if state.get("business_error"):
        return "approval_node"

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
) -> list[Send] | Literal["booking_plan_node", "draft_node", "approval_node"]:
    if state.get("business_error"):
        return "approval_node"

    plan = state.get("plan")
    actions = plan.get("actions", []) if plan else []
    sends: list[Send] = []
    if "vector_retrieve" in actions:
        sends.append(Send("vector_retrieve_node", state))
    if "db_retrieve" in actions:
        sends.append(Send("db_retrieve_node", state))
    if sends:
        return sends

    return route_after_retrieve(state)


def route_after_retrieve(
    state: EmailAgentState,
) -> Literal["booking_plan_node", "draft_node", "approval_node"]:
    if state.get("business_error"):
        return "approval_node"

    plan = state.get("plan")
    actions = set(plan.get("actions", []) if plan else [])
    booking_actions = {
        "reservation_create",
        "reservation_update",
        "reservation_delete",
    }
    return "booking_plan_node" if actions & booking_actions else "draft_node"

graph = StateGraph(EmailAgentState)

graph.add_node("read_email_node", _guard_business_error(read_email))
graph.add_node("classification_node", _guard_business_error(classify_node))
graph.add_node("approval_node", approval_node)
graph.add_node("plan_node", _guard_business_error(plan_action))
graph.add_node("vector_retrieve_node", _guard_business_error(vector_retrieve))
graph.add_node("db_retrieve_node", _guard_business_error(db_retrieve))
graph.add_node("booking_plan_node", _guard_business_error(booking_plan_node))
graph.add_node("draft_node", _guard_business_error(draft_node))
graph.add_node("send_email_node", _guard_business_error(send_email_node))

graph.add_edge(START, "read_email_node")
graph.add_conditional_edges(
    "read_email_node",
    lambda state: "approval_node" if state.get("business_error") else "classification_node",
)

# spam → 종료, urgency high → 승인 노드, 그 외 → plan
graph.add_conditional_edges(
    "classification_node",
    route_after_classification,
)

graph.add_conditional_edges(
    "plan_node",
    route_after_plan,
)

graph.add_conditional_edges(
    "vector_retrieve_node",
    route_after_retrieve,
)
graph.add_conditional_edges(
    "db_retrieve_node",
    route_after_retrieve,
)
graph.add_edge("booking_plan_node", "draft_node")
graph.add_conditional_edges(
    "booking_plan_node",
    lambda state: "approval_node" if state.get("business_error") else "draft_node",
)
graph.add_conditional_edges(
    "draft_node",
    lambda state: "approval_node" if state.get("business_error") else "send_email_node",
)
graph.add_edge("send_email_node", END)
graph.add_edge("approval_node", END)


if __name__ == "__main__":
    # python -m app.graphs.graphs
    compiled_graph = graph.compile()
    result = compiled_graph.invoke(
        {
            "email_data": {
                "email_subject": "",
                "email_content": "",
                "sender_email": "",
            },
            "classification": None,
            "plan": None,
            "vector_retrieve_results": None,
            "db_retrieve_results": None,
            "action_sqlite": None,
            "draft_response": None,
            "business_error": None,
        }
    )

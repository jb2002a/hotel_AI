# app/graphs/main_graph.py (예시)
from collections.abc import Callable
from typing import Literal

from langgraph.graph import StateGraph, START, END
from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.control import manager_approval_node
from app.graphs.nodes.intake import email_ingest, intent_classifier_node
from app.graphs.nodes.planning import reservation_sql_node
from app.graphs.nodes.response import reply_draft_node
from app.graphs.nodes.retrieval import (
    member_booking_retrieve,
    vacancy_retrieve,
    policy_retrieve,
)

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


def route_after_intent_classification(
    state: EmailAgentState,
) -> (
    Literal[END, "manager_approval_node"]
    | list[
        Literal[
            "policy_retrieve_node",
            "member_booking_retrieve_node",
            "vacancy_retrieve_node",
        ]
    ]
    | Literal["reservation_sql_node", "reply_draft_node"]
):
    if state.get("business_error"):
        return "manager_approval_node"

    classification = state["classification"]
    if classification is None:
        return END
    if classification["category"] == "spam":
        return "manager_approval_node"

    actions = state.get("actions")
    normalized = actions if isinstance(actions, list) else []
    retrieve_nodes: list[
        Literal[
            "policy_retrieve_node",
            "member_booking_retrieve_node",
            "vacancy_retrieve_node",
        ]
    ] = []
    if "vector_retrieve" in normalized:
        retrieve_nodes.append("policy_retrieve_node")
    if "db_retrieve" in normalized:
        retrieve_nodes.append("member_booking_retrieve_node")
    if "retrieve_rest_rooms" in normalized:
        retrieve_nodes.append("vacancy_retrieve_node")

    if (
        "reservation_create" in normalized
        and "vacancy_retrieve_node" not in retrieve_nodes
    ):
        retrieve_nodes.append("vacancy_retrieve_node")
    if (
        ("reservation_update" in normalized or "reservation_delete" in normalized)
        and "member_booking_retrieve_node" not in retrieve_nodes
    ):
        retrieve_nodes.append("member_booking_retrieve_node")
    if retrieve_nodes:
        return retrieve_nodes

    return route_after_retrieve(state)


def route_after_email_ingest(
    state: EmailAgentState,
) -> Literal["intent_classifier_node", "manager_approval_node"]:
    # 이메일 읽기 실패 시 승인 프로세스로 전달
    return "manager_approval_node" if state.get("business_error") else "intent_classifier_node"


def route_after_retrieve(
    state: EmailAgentState,
) -> Literal["reservation_sql_node", "reply_draft_node", "manager_approval_node"]:
    if state.get("business_error"):
        return "manager_approval_node"

    actions_raw = state.get("actions")
    actions = actions_raw if isinstance(actions_raw, list) else []
    has_booking_action = any(
        action in actions
        for action in ("reservation_create", "reservation_update", "reservation_delete")
    )
    return "reservation_sql_node" if has_booking_action else "reply_draft_node"


def route_after_reservation_sql(
    state: EmailAgentState,
) -> Literal["manager_approval_node", "reply_draft_node"]:
    # 예약 처리 중 업무 예외 발생 시 승인으로 분기
    return "manager_approval_node" if state.get("business_error") else "reply_draft_node"


graph = StateGraph(EmailAgentState)
graph.add_node("email_ingest_node", _guard_business_error(email_ingest))
graph.add_node("intent_classifier_node", _guard_business_error(intent_classifier_node))
graph.add_node("manager_approval_node", manager_approval_node)
graph.add_node("policy_retrieve_node", _guard_business_error(policy_retrieve))
graph.add_node("member_booking_retrieve_node", _guard_business_error(member_booking_retrieve))
graph.add_node("vacancy_retrieve_node", _guard_business_error(vacancy_retrieve))
graph.add_node("reservation_sql_node", _guard_business_error(reservation_sql_node))
graph.add_node("reply_draft_node", _guard_business_error(reply_draft_node))


# ===== Entry =====
graph.add_edge(START, "email_ingest_node")

# ===== Intake =====
graph.add_conditional_edges(
    "email_ingest_node",
    route_after_email_ingest,
)

graph.add_conditional_edges(
    "intent_classifier_node",
    route_after_intent_classification,
)

# ===== Retrieval =====
graph.add_conditional_edges(
    "policy_retrieve_node",
    route_after_retrieve,
)
graph.add_conditional_edges(
    "member_booking_retrieve_node",
    route_after_retrieve,
)
graph.add_conditional_edges(
    "vacancy_retrieve_node",
    route_after_retrieve,
)

# ===== Booking / Draft =====
graph.add_conditional_edges(
    "reservation_sql_node",
    route_after_reservation_sql,
)
graph.add_edge("reply_draft_node", "manager_approval_node")

# ===== Exit =====
graph.add_edge("manager_approval_node", END)


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
            "actions": None,
            "vector_retrieve_results": None,
            "db_retrieve_results": None,
            "rest_room_retrieve_results": None,
            "action_sqlite": None,
            "draft_response": None,
            "approval_packet": None,
            "manager_comment": None,
            "business_error": None,
        }
    )

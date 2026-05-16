# app/graphs/main_graph.py (예시)
from collections.abc import Callable
from typing import Literal

from langgraph.graph import StateGraph, START, END
from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.control import approval_node
from app.graphs.nodes.intake import classify_node, read_email
from app.graphs.nodes.planning import booking_plan_node
from app.graphs.nodes.response import draft_node
from app.graphs.nodes.retrieval import db_retrieve, retrieve_rest_rooms, vector_retrieve

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
) -> (
    Literal[END, "approval_node"]
    | list[Literal["vector_retrieve_node", "db_retrieve_node", "retrieve_rest_rooms_node"]]
    | Literal["booking_plan_node", "draft_node"]
):
    if state.get("business_error"):
        return "approval_node"

    classification = state["classification"]
    if classification is None:
        return END
    if classification["category"] == "spam":
        return "approval_node"

    actions = state.get("actions")
    normalized = actions if isinstance(actions, list) else []
    retrieve_nodes: list[
        Literal["vector_retrieve_node", "db_retrieve_node", "retrieve_rest_rooms_node"]
    ] = []
    if "vector_retrieve" in normalized:
        retrieve_nodes.append("vector_retrieve_node")
    if "db_retrieve" in normalized:
        retrieve_nodes.append("db_retrieve_node")
    if "retrieve_rest_rooms" in normalized:
        retrieve_nodes.append("retrieve_rest_rooms_node")

    if (
        "reservation_create" in normalized
        and "retrieve_rest_rooms_node" not in retrieve_nodes
    ):
        retrieve_nodes.append("retrieve_rest_rooms_node")
    if (
        ("reservation_update" in normalized or "reservation_delete" in normalized)
        and "db_retrieve_node" not in retrieve_nodes
    ):
        retrieve_nodes.append("db_retrieve_node")
    if retrieve_nodes:
        return retrieve_nodes

    return route_after_retrieve(state)


def route_after_read_email(
    state: EmailAgentState,
) -> Literal["classification_node", "approval_node"]:
    # 이메일 읽기 실패 시 승인 프로세스로 전달
    return "approval_node" if state.get("business_error") else "classification_node"


def route_after_retrieve(
    state: EmailAgentState,
) -> Literal["booking_plan_node", "draft_node", "approval_node"]:
    if state.get("business_error"):
        return "approval_node"

    actions_raw = state.get("actions")
    actions = actions_raw if isinstance(actions_raw, list) else []
    has_booking_action = any(
        action in actions
        for action in ("reservation_create", "reservation_update", "reservation_delete")
    )
    return "booking_plan_node" if has_booking_action else "draft_node"


def route_after_booking_plan(
    state: EmailAgentState,
) -> Literal["approval_node", "draft_node"]:
    # 예약 처리 중 업무 예외 발생 시 승인으로 분기
    return "approval_node" if state.get("business_error") else "draft_node"


graph = StateGraph(EmailAgentState)
graph.add_node("read_email_node", _guard_business_error(read_email))
graph.add_node("classification_node", _guard_business_error(classify_node))
graph.add_node("approval_node", approval_node)
graph.add_node("vector_retrieve_node", _guard_business_error(vector_retrieve))
graph.add_node("db_retrieve_node", _guard_business_error(db_retrieve))
graph.add_node("retrieve_rest_rooms_node", _guard_business_error(retrieve_rest_rooms))
graph.add_node("booking_plan_node", _guard_business_error(booking_plan_node))
graph.add_node("draft_node", _guard_business_error(draft_node))


# ===== Entry =====
graph.add_edge(START, "read_email_node")

# ===== Intake =====
graph.add_conditional_edges(
    "read_email_node",
    # 이메일 읽기 실패 -> 승인, 그 외 -> 분류 노드
    route_after_read_email,
)

graph.add_conditional_edges(
    "classification_node",
    # 분류 후 intent 기반 actions로 검색 또는 draft/booking 분기
    route_after_classification,
)

# ===== Retrieval (classification에서 결정된 actions 기준) =====

# retrieval 완료 후 예약 실행 필요 여부로 분기
graph.add_conditional_edges(
    "vector_retrieve_node",
    route_after_retrieve,
)
graph.add_conditional_edges(
    "db_retrieve_node",
    route_after_retrieve,
)
graph.add_conditional_edges(
    "retrieve_rest_rooms_node",
    route_after_retrieve,
)

# ===== Booking / Draft =====
graph.add_conditional_edges(
    "booking_plan_node",
    route_after_booking_plan,
)
graph.add_edge("draft_node", "approval_node")

# ===== Exit =====
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

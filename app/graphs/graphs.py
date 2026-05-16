# app/graphs/main_graph.py (예시)
from collections.abc import Callable
from typing import Literal

from langgraph.graph import StateGraph, START, END
from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.control import manager_approval_node
from app.graphs.nodes.intake import email_ingest, intent_classifier_node
from app.graphs.nodes.prepare import prepare_node
from app.graphs.nodes.response import reply_draft_node

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


def route_after_email_ingest(
    state: EmailAgentState,
) -> Literal["intent_classifier_node", "manager_approval_node"]:
    # 이메일 읽기 실패 시 승인 프로세스로 전달
    return "manager_approval_node" if state.get("business_error") else "intent_classifier_node"


graph = StateGraph(EmailAgentState)
graph.add_node("email_ingest_node", _guard_business_error(email_ingest))
graph.add_node("intent_classifier_node", _guard_business_error(intent_classifier_node))
graph.add_node("prepare_node", _guard_business_error(prepare_node))
graph.add_node("reply_draft_node", _guard_business_error(reply_draft_node))
graph.add_node("manager_approval_node", manager_approval_node)


# ===== Entry =====
graph.add_edge(START, "email_ingest_node")

# ===== Intake =====
graph.add_conditional_edges(
    "email_ingest_node",
    route_after_email_ingest,
)

graph.add_edge("intent_classifier_node", "prepare_node")
graph.add_edge("prepare_node", "reply_draft_node")
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


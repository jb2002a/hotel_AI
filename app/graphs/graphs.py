"""호텔 이메일 에이전트 LangGraph (V1).

플로우
------
START
  → email_ingest
       ├─ (정상) Command → intent_classifier
       └─ (BusinessError) Command → manager_approval
  → intent_classifier     분류 + intent → actions 고정 매핑
  → prepare               actions 기반 retrieve 병렬 + 예약 SQL 생성
  → reply_draft           답변 초안 (business_error 시 no-op)
  → manager_approval      approval_packet 스냅샷 (+ interrupt, UI)
  → END

prepare 내부 retrieve (별도 그래프 노드 아님):
  policy_retrieve | member_booking_retrieve | vacancy_retrieve
"""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.errors import BusinessError
from app.graphs.nodes.control import manager_approval_node
from app.graphs.nodes.intake import email_ingest, intent_classifier_node
from app.graphs.nodes.prepare import prepare_node
from app.graphs.nodes.response import reply_draft_node
from app.schemas.graph_state import EmailAgentState

# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

# 자식 노드에서 던진 BusinessError를 그래프 중단 없이 state에 기록
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


graph = StateGraph(EmailAgentState)

# Intake
graph.add_node("email_ingest_node", email_ingest)  # Command goto로 분기
graph.add_node("intent_classifier_node", _guard_business_error(intent_classifier_node))

# Prepare (retrieve + SQL은 prepare_node 내부에서 actions 기준 실행)
graph.add_node("prepare_node", _guard_business_error(prepare_node))

# Response
graph.add_node("reply_draft_node", _guard_business_error(reply_draft_node))

# Control
graph.add_node("manager_approval_node", manager_approval_node)

# ---------------------------------------------------------------------------
# 엣지
# ---------------------------------------------------------------------------

# Entry: email_ingest → intent_classifier | manager_approval 은 Command(goto)로 연결
graph.add_edge(START, "email_ingest_node")

graph.add_edge("intent_classifier_node", "prepare_node")
graph.add_edge("prepare_node", "reply_draft_node")
graph.add_edge("reply_draft_node", "manager_approval_node")

graph.add_edge("manager_approval_node", END)


def _default_initial_state() -> dict:
    return {
        "email_data": {
            "email_subject": "",
            "email_content": "",
            "sender_email": "",
        },
        "extract_data": None,
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


if __name__ == "__main__":
    # python -m app.graphs.graphs
    compiled_graph = graph.compile()
    result = compiled_graph.invoke(_default_initial_state())
    print(result.get("approval_packet"))

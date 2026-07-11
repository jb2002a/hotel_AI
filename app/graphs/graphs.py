"""호텔 이메일 에이전트 LangGraph (V1).

플로우
------
START
  → email_classification  분류 + actions·policy_queries 추출
  → email_ingest          normal만 extract (spam/high는 바로 manager)
  → prepare               actions 기반 retrieve 병렬
  → sql_build             예약 SQL 생성
  → reply_draft           답변 초안 (business_error 시 no-op)
  → manager_approval      interrupt/UI용 payload (+ interrupt, UI)
  → END
"""

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.errors import BusinessError
from app.graphs.nodes.control import manager_approval_node
from app.graphs.nodes.intake import email_classification, email_ingest
from app.graphs.nodes.prepare import prepare_node, sql_build_node
from app.graphs.nodes.response import reply_draft_node
from app.schemas.graph_state import EmailAgentState, build_approval_payload

# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

def _business_error_update(exc: BusinessError) -> dict[str, Any]:
    return {
        "business_error": {
            "code": exc.code,
            "message": exc.message,
        },
        "manager_errors": [
            {
                "type": "business_error",
                "code": exc.code,
                "message": exc.message,
            }
        ],
    }


def _system_error_update(exc: Exception) -> dict[str, Any]:
    code = exc.__class__.__name__
    message = str(exc) or "예상하지 못한 시스템 오류가 발생했습니다."
    return {
        "business_error": {
            "code": "SYSTEM_ERROR",
            "message": message,
        },
        "manager_errors": [
            {
                "type": "system_error",
                "code": code,
                "message": message,
            }
        ],
    }


# 자식 노드 예외를 그래프 중단 없이 state에 기록하고 매니저 승인으로 라우팅
def _guard_node_error(
    node_fn: Callable[[EmailAgentState], dict[str, Any] | Command[Any]],
) -> Callable[[EmailAgentState], dict[str, Any] | Command[Any]]:
    def _wrapped(state: EmailAgentState) -> dict[str, Any] | Command[Any]:
        try:
            return node_fn(state)
        except BusinessError as exc:
            return Command(
                update=_business_error_update(exc),
                goto="manager_approval_node",
            )
        except Exception as exc:
            return Command(
                update=_system_error_update(exc),
                goto="manager_approval_node",
            )

    return _wrapped


graph = StateGraph(EmailAgentState)

# Intake
graph.add_node("email_ingest_node", _guard_node_error(email_ingest))
graph.add_node("email_classification_node", _guard_node_error(email_classification))

# Prepare
graph.add_node("prepare_node", _guard_node_error(prepare_node))
graph.add_node("sql_build_node", _guard_node_error(sql_build_node))

# Response
graph.add_node("reply_draft_node", _guard_node_error(reply_draft_node))

# Control
graph.add_node("manager_approval_node", manager_approval_node)

# ---------------------------------------------------------------------------
# 엣지
# ---------------------------------------------------------------------------

graph.add_edge(START, "email_classification_node")
graph.add_edge("email_classification_node", "email_ingest_node")
graph.add_edge("email_ingest_node", "prepare_node")
graph.add_edge("prepare_node", "sql_build_node")
graph.add_edge("sql_build_node", "reply_draft_node")
graph.add_edge("reply_draft_node", "manager_approval_node")

graph.add_edge("manager_approval_node", END)

#---------------------------------------------------------------------------#

# For Testing


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
        "policy_queries": None,
        "vector_retrieve_results": None,
        "db_retrieve_results": None,
        "rest_room_retrieve_results": None,
        "action_sqlite": None,
        "draft_response": None,
        "manager_comment": None,
        "business_error": None,
        "manager_errors": None,
    }


if __name__ == "__main__":
    # python -m app.graphs.graphs
    import uuid

    from langgraph.types import Command

    try:
        from langgraph.checkpoint.memory import InMemorySaver as _MemorySaver
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver as _MemorySaver

    compiled_graph = graph.compile(checkpointer=_MemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = compiled_graph.invoke(_default_initial_state(), config=config)
    if result.get("__interrupt__"):
        result = compiled_graph.invoke(Command(resume={}), config=config)
    print(build_approval_payload(result))

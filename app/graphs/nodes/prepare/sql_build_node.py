from langsmith import traceable

from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.prepare.reservation_sql import build_action_sqlite


@traceable(name="sql_build_node")
def sql_build_node(state: EmailAgentState) -> dict:
    """retrieval 결과를 바탕으로 예약 SQL을 생성"""

    if state.get("business_error"):
        return {}

    actions_raw = state.get("actions")
    actions = set(actions_raw) if isinstance(actions_raw, list) else set()

    result = build_action_sqlite(state, actions)
    return result if result else {}

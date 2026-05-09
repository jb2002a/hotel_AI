from app.schemas.graph_state import EmailAgentState
from langgraph.types import interrupt


def approval_node(state: EmailAgentState) -> dict:
    """매니저가 패킷을 수정해 resume하면 state를 반영하고 종료 단계로 이동."""
    approval_packet = {
        "email_data": state.get("email_data"),
        "extract_data": state.get("extract_data"),
        "db_retrieve_results": state.get("db_retrieve_results"),
        "action_sqlite": state.get("action_sqlite"),
        "draft_response": state.get("draft_response"),
        "business_error": state.get("business_error"),
    }

    resume_payload = interrupt(
        {
            "message": "매니저 승인/수정이 필요합니다. 수정 후 resume 해주세요.",
            "payload": approval_packet,
        }
    )
    updated_state: dict = {
        "approval_packet": approval_packet,
        "business_error": None,
    }

    if "draft_response" in resume_payload:
        updated_state["draft_response"] = resume_payload["draft_response"]
    if "action_sqlite" in resume_payload:
        updated_state["action_sqlite"] = resume_payload["action_sqlite"]
    if "manager_comment" in resume_payload:
        updated_state["manager_comment"] = resume_payload["manager_comment"]

    return updated_state

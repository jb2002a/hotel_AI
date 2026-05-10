from app.schemas.graph_state import EmailAgentState
from langgraph.types import interrupt


def approval_node(state: EmailAgentState) -> dict:
    approval_packet = {
        "email_data": state.get("email_data"),
        "extract_data": state.get("extract_data"),
        "plan": state.get("plan"),
        "db_retrieve_results": state.get("db_retrieve_results"),
        "rest_room_retrieve_results": state.get("rest_room_retrieve_results"),
        "action_sqlite": state.get("action_sqlite"),
        "draft_response": state.get("draft_response"),
        "business_error": state.get("business_error"),
    }
    # 평가를 위해 조기 return 처리, 후에 하단 코드 추가
    return {"approval_packet": approval_packet}


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

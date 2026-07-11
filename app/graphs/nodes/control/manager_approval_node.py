from app.schemas.graph_state import EmailAgentState, build_approval_payload
from langgraph.types import interrupt


def manager_approval_node(state: EmailAgentState) -> dict:
    payload = build_approval_payload(state)

    resume_payload = interrupt(
        {
            "message": "매니저 승인/수정이 필요합니다. 수정 후 resume 해주세요.",
            "payload": payload,
        }
    )
    updated_state: dict = {"business_error": None, "manager_errors": []}

    if "draft_response" in resume_payload:
        updated_state["draft_response"] = resume_payload["draft_response"]
    if "action_sqlite" in resume_payload:
        updated_state["action_sqlite"] = resume_payload["action_sqlite"]
    if "manager_comment" in resume_payload:
        updated_state["manager_comment"] = resume_payload["manager_comment"]

    return updated_state

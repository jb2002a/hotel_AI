from app.schemas.graph_state import EmailAgentState


def approval_node(state: EmailAgentState) -> dict:
    """urgency high 건 승인·검토. 추후 interrupt/외부 승인 연동."""
    return {}

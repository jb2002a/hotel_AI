from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, PlanAction
from langsmith import traceable


@traceable(name="plan_action")
def plan_action(state: EmailAgentState) -> dict:
    email_data = state["email_data"]

    subject = email_data["email_subject"]
    content = email_data["email_content"]

    classification = state.get("classification") or {}
    intents: list = classification.get("intents") or []

    structured_llm = LLM.with_structured_output(PlanAction)

    plan_action_prompt = f"""You are a planner that returns execution actions only.

    Intent classification is already done:
    {intents}

    Important distinction:
    - intents are labels for understanding the email
    - actions are executable graph steps
    - DO NOT output intent names (e.g. "booking_lookup")

    Return JSON matching PlanAction with this exact shape:
    {{"actions": [ ... ]}}

    Allowed action names (and only these 6):
    1) "vector_retrieve" - retrieve policy/FAQ/general hotel info from vector store
    2) "db_retrieve" - retrieve sender-related membership/reservation context from SQLite
    3) "retrieve_rest_rooms" - check remaining room inventory
    4) "reservation_create" - create a new reservation
    5) "reservation_update" - update an existing reservation
    6) "reservation_delete" - delete/cancel an existing reservation

    Planning rules:
    - Include only actions required to answer or execute the request.
    - For pure information requests, do not include reservation actions.
    - If creating a reservation, include "retrieve_rest_rooms" before "reservation_create".
    - If updating or deleting a reservation, include "db_retrieve" before the reservation action.
    - Keep retrieval steps before reservation steps.
    - At most one reservation action from ["reservation_create", "reservation_update", "reservation_delete"].
    - If no action is needed, return an empty list.
    - Never return any name outside the 6 allowed actions.

    Valid examples:
    - {{"actions": []}}
    - {{"actions": ["vector_retrieve"]}}
    - {{"actions": ["db_retrieve"]}}
    - {{"actions": ["retrieve_rest_rooms", "reservation_create"]}}
    - {{"actions": ["db_retrieve", "reservation_update"]}}
    - {{"actions": ["db_retrieve", "reservation_delete"]}}
    - {{"actions": ["vector_retrieve", "retrieve_rest_rooms", "reservation_create"]}}

    Email subject: {subject}
    Email body: {content}
    """

    plan = structured_llm.invoke(plan_action_prompt)
    return {"plan": plan}

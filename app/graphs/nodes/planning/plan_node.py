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

    plan_action_prompt = f"""Decide what actions are needed to handle this email.

    The intent has already been classified as: {intents}

    Return actions using only these names:
    - "vector_retrieve": vector DB / RAG search (policies, FAQs, general knowledge base)
    - "db_retrieve": member and room booking lookup for the sender email (SQLite)
    - "retrieve_rest_rooms": check how many vacant rooms remain before creating a reservation
    - "reservation_create": create a reservation when the customer is requesting a new booking
    - "reservation_update": update an existing reservation when customer asks to change dates/details
    - "reservation_delete": cancel/delete an existing reservation when customer asks to cancel

    Rules:
    - Use "vector_retrieve" when policy/FAQ/general hotel info from the knowledge base is needed.
    - Use "db_retrieve" when the reply needs the sender's membership or reservation data.
    - Use exactly one booking action from ["reservation_create", "reservation_update", "reservation_delete"] only when the email clearly asks for booking execution.
    - If intents contains only info-retrieval intents such as "policy_qna", "booking_lookup", "promotion_pricing", do NOT include any of ["reservation_create", "reservation_update", "reservation_delete"].
    - For "reservation_create", include "retrieve_rest_rooms" first to validate room availability.
    - For "reservation_update" or "reservation_delete", include "db_retrieve" first to verify existing member/booking context.
    - For "reservation_create", "db_retrieve" is optional. Do not include "db_retrieve" when it is a plain new booking request and no existing member/booking check is required.
    - Keep retrieval actions before booking actions in execution order.
    - You may return both, one, or neither. Examples:
      [], ["vector_retrieve"], ["db_retrieve"], ["retrieve_rest_rooms", "reservation_create"], ["db_retrieve", "reservation_update"], ["vector_retrieve", "retrieve_rest_rooms", "reservation_create"].
    - Do not return any other action names.

    Subject: {subject}
    Body: {content}
    """

    plan = structured_llm.invoke(plan_action_prompt)
    return {"plan": plan}

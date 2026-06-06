from typing import Any

from langgraph.types import Command
from langsmith import traceable

from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, EmailClassification, GraphActionLiteral


def _dedupe_actions(actions: list[str]) -> list[GraphActionLiteral]:
    result: list[GraphActionLiteral] = []
    seen: set[str] = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        result.append(action)  # type: ignore[arg-type]
    return result


@traceable(name="email_classification")
def email_classification(state: EmailAgentState) -> dict[str, Any] | Command[Any]:
    """이메일 분류(category, urgency) 및 actions·policy_queries 추출 노드"""

    structured_llm = LLM.with_structured_output(EmailClassification)
    email_data = state["email_data"]
    classification_prompt = f"""
    You analyze one customer email for a hotel workflow.

    Return only the structured fields requested by the schema.

    [Email]
    Subject: {email_data['email_subject']}
    Body: {email_data['email_content']}
    Sender: {email_data['sender_email']}

    [Allowed actions — include every action needed to fulfill explicit requests]
    - reservation_create: customer explicitly asks to book or reserve a room.
    - reservation_update: customer explicitly asks to change an existing booking.
    - reservation_delete: customer explicitly asks to cancel an existing booking.
    - reservation_search: customer explicitly asks to confirm or look up their booking/member status.

    [policy_queries]
    List specific questions that must be answered from the hotel knowledge base to handle this email.
    Include:
    - explicit policy/price/amenity/service questions
    - latent lookups required to fulfill the request (e.g. promotion terms when booking at promo price,
      wheelchair rental policy when requesting wheelchair with a date change)
  Leave empty [] if no policy lookup is needed.

    [Action rules — apply strictly]
    1. Include an action only when the customer states that request clearly (direct ask or clear action verb).
    2. Do not add reservation or booking actions from context alone when not explicitly requested.
    3. Use multiple actions when there are multiple explicit requests in the same email.

    category: "spam" for unsolicited ads or clearly irrelevant mail; otherwise "normal".
    urgency: "high" only for same-day emergencies or issues needing immediate action; otherwise "normal".

    Do not invent values outside the allowed action names.
    """
    classification = structured_llm.invoke(classification_prompt)
    actions_raw: list[str] = classification.get("actions") or []
    policy_queries: list[str] = classification.get("policy_queries") or []
    actions = _dedupe_actions(actions_raw)

    base_update: dict[str, Any] = {
        "classification": classification,
        "actions": actions,
        "policy_queries": policy_queries,
    }

    if classification["category"] == "spam":
        return Command(
            update={
                **base_update,
                "actions": [],
                "policy_queries": [],
                "business_error": {
                    "code": "SPAM",
                    "message": "스팸으로 분류된 이메일입니다.",
                },
            },
            goto="manager_approval_node",
        )

    if classification["urgency"] == "high":
        return Command(
            update={
                **base_update,
                "business_error": {
                    "code": "HIGH_URGENCY",
                    "message": "긴급 이메일로 분류되어 매니저 승인으로 바로 이동합니다.",
                },
            },
            goto="manager_approval_node",
        )

    return base_update

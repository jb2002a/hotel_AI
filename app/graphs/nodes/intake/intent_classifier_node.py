from typing import Any, Iterable

from app.config.config import LLM
from app.schemas.graph_state import (
    EmailAgentState,
    EmailClassification,
    GraphActionLiteral,
    INTENT_ACTION_MAP,
)
from langgraph.types import Command
from langsmith import traceable


def intents_to_actions(intents: Iterable[str]) -> list[GraphActionLiteral]:
    """intent 목록을 INTENT_ACTION_MAP에서 조회해 중복 없이 합산한다."""
    actions: set[GraphActionLiteral] = set()
    for intent in intents:
        for action in INTENT_ACTION_MAP.get(intent, []):
            actions.add(action)
    return list(actions)


@traceable(name="intent_classifier_node")
def intent_classifier_node(state: EmailAgentState) -> dict[str, Any] | Command[Any]:
    """이메일 분류(urgency, category, intents) 노드"""

    structured_llm = LLM.with_structured_output(EmailClassification)
    email_data = state["email_data"]
    classification_prompt = f"""
    You classify one customer email for a hotel workflow.
    Return only the structured fields requested by the schema.

    [Email]
    Subject: {email_data['email_subject']}
    Body: {email_data['email_content']}
    Sender: {email_data['sender_email']}

    [Allowed intents]
    - reservation_create: customer explicitly asks to book or reserve.
    - reservation_update: customer explicitly asks to change an existing booking (dates, guests, name, room type).
    - reservation_delete: customer explicitly asks to cancel an existing booking.
    - booking_lookup: customer explicitly asks to confirm, look up, or check booking status or details.
    - policy_qna: customer explicitly asks a question about policy, price, availability, amenities, or services.
    - complaint_or_incident: customer explicitly reports a problem or incident (no other actionable request).
    - out_of_scope: not about hotel service.
    - unclear: hotel-related but no explicit request above.

    [Intent rules — apply strictly]
    1. Assign an intent only when the customer states that request clearly in the email (direct ask or clear action verb).
    2. Do not infer intents from context, side remarks, payment/refund wording, or missing-booking obstacles.
    3. Use multiple intents only when there are multiple explicit, separate requests in the same email.
    4. If nothing is explicitly requested, use "unclear" (or "complaint_or_incident" only when they explicitly report a problem).

    category: "spam" for unsolicited ads or clearly irrelevant mail; otherwise "normal".
    urgency: "high" only for same-day emergencies or issues needing immediate action; otherwise "normal".

    Do not invent labels outside the allowed values.
    """
    classification = structured_llm.invoke(classification_prompt)
    intents_raw: list[str] = classification.get("intents") or []
    actions = intents_to_actions(intents_raw)

    # 스팸 이메일인 경우 매니저 승인으로 바로 이동
    if classification["category"] == "spam":
        return Command(
            update={
                "classification": classification,
                "actions": [],
                "business_error": {
                    "code": "SPAM",
                    "message": "스팸으로 분류된 이메일입니다.",
                },
            },
            goto="manager_approval_node",
        )

    # 긴급 이메일인 경우 매니저 승인으로 바로 이동
    if classification["urgency"] == "high":
        return Command(
            update={
                "classification": classification,
                "actions": actions,
                "business_error": {
                    "code": "HIGH_URGENCY",
                    "message": "긴급 이메일로 분류되어 매니저 승인으로 바로 이동합니다.",
                },
            },
            goto="manager_approval_node",
        )

    return {
        "classification": classification,
        "actions": actions,
    }

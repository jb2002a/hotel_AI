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
    seen: set[GraphActionLiteral] = set()
    result: list[GraphActionLiteral] = []
    for intent in intents:
        for action in INTENT_ACTION_MAP.get(intent, []):
            if action not in seen:
                seen.add(action)
                result.append(action)
    return result


@traceable(name="intent_classifier_node")
def intent_classifier_node(state: EmailAgentState) -> dict[str, Any] | Command[Any]:
    structured_llm = LLM.with_structured_output(EmailClassification)
    email_data = state["email_data"]
    classification_prompt = f"""
    Analyze the hotel customer email and return classification as JSON.

    Subject: {email_data['email_subject']}
    Body: {email_data['email_content']}
    Sender: {email_data['sender_email']}

    Return exactly these fields:
    - intents: non-empty list, each item MUST be chosen only from this set (use multiple intents when clearly applicable):
    ["policy_qna","booking_lookup","reservation_create","reservation_update","reservation_delete",
    "payment_invoice","promotion_pricing","special_request","complaint_or_incident","out_of_scope","unclear","other"]
    - category: exactly one of ["normal", "spam"]
    - urgency: exactly one of ["normal", "high"]

    Do not use any label outside the allowed lists above.
    """
    classification = structured_llm.invoke(classification_prompt)
    intents_raw: list[str] = classification.get("intents") or []
    actions = intents_to_actions(intents_raw)

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

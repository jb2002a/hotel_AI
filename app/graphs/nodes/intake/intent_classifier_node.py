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

    [Allowed output values]
    intents: choose one or more of:
    - reservation_create: customer wants to make a new booking.
    - reservation_update: customer wants to change an existing booking. This includes date changes, guest-count changes, name corrections, or other normal reservation-field changes.
    - reservation_delete: customer wants to cancel an existing booking.
    - booking_lookup: customer asks for the status or details of an existing booking.
    - policy_qna: customer asks about hotel policies such as check-in, check-out, cancellation, pets, or facility rules.
    - payment_invoice: customer asks about payment, charges, invoices, receipts, or refunds.
    - promotion_pricing: customer asks about prices, discounts, packages, or promotions.
    - special_request: customer asks for an extra service or preference, such as early check-in, late check-out, a room view, decorations, baby cot, or dietary needs.
    - complaint_or_incident: customer reports a problem, dissatisfaction, or an incident.
    - out_of_scope: email is not related to hotel service.
    - unclear: email is hotel-related, but there is not enough information to choose a specific intent.

    category: choose exactly one of "normal" or "spam".
    urgency: choose exactly one of "normal" or "high".

    [Decision steps]
    1. If the email is unsolicited advertising, bulk sales, or clearly irrelevant, set category to "spam".
    2. Otherwise set category to "normal".
    3. Pick the intent labels that directly match the customer's actual requests.
    4. Use multiple intents only when the email contains separate requests. Example: changing dates and asking for a room upgrade.
    5. Do not add "special_request" when the email only changes standard reservation fields such as dates, name, or guest count.
    6. Polite or tentative wording such as "if possible" or "please check" does not change the intent.
    7. Use "out_of_scope" only when the email is not about hotel service.
    8. Use "unclear" only when the email is hotel-related but too vague to classify.
    9. Set urgency to "high" only for same-day emergencies, ongoing incidents, or issues requiring immediate hotel action. Otherwise use "normal".

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

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
    - reservation_update: customer wants to change core booking fields on an existing reservation: dates, guest count, guest name, or room category/type (e.g. upgrade to suite). NOT equipment rental, crib, humidifier, allergy bedding, or high-floor/view preferences.
    - reservation_delete: customer wants to cancel an existing booking.
    - booking_lookup: customer asks for the status or details of an existing booking.
    - policy_qna: customer asks about hotel policies, facility rules, pricing, promotions, packages, payments, invoices, receipts, refunds, early/late check-in or check-out, amenities, equipment rental, dietary needs, room preferences, or service availability ("is it possible?", "how much?").
    - complaint_or_incident: customer reports a problem, dissatisfaction, or an incident. This label does not trigger automated retrieval or booking actions by itself.
    - out_of_scope: email is not related to hotel service.
    - unclear: email is hotel-related, but there is not enough information to choose a specific intent.

    category: choose exactly one of "normal" or "spam".
    urgency: choose exactly one of "normal" or "high".

    [Decision steps]
    1. If the email is unsolicited advertising, bulk sales, or clearly irrelevant, set category to "spam".
    2. Otherwise set category to "normal".
    3. Identify each distinct customer request, then map each to one or more intents.
    4. Use multiple intents only when the email contains separate requests. Example: changing dates and asking about pet policy.
    5. ADD "policy_qna" together with reservation_* or "booking_lookup" when there is a DISTINCT second ask about:
       amenities or equipment (wheelchair, crib, humidifier, allergy bedding), room preferences (high floor, view),
       promotion or package price, or policy/availability ("possible?", "how much?", "what is the rule?").
       Room type upgrade and date/name/guest-count changes stay "reservation_update" only; add "policy_qna" for the separate amenity or preference ask.
    6. SUPPRESS "policy_qna" only when payment, refund, penalty, or cancel-policy words support a reservation action but are NOT a separate question. Use reservation intent only. Examples to SUPPRESS:
       cancel with no penalty wording; refund on a past booking; penalty rules while requesting urgent cancel;
       payment failed while asking to fix or change dates; booking not found while trying to change (obstacle, not lookup).
    7. Do not add "booking_lookup" when the customer mentions a missing booking only as a reason to update or cancel. Use "booking_lookup" when confirmation or status is the main request.
    8. Polite or tentative wording such as "if possible" or "please check" does not change the intent.
    9. Use "complaint_or_incident" for complaints or incidents, and add a reservation intent only when the customer also asks to create, update, or cancel a booking. Do not use it for payment glitches when the customer asks to fix or create/update a booking.
    10. Use "out_of_scope" only when the email is not about hotel service.
    11. Use "unclear" only when the email is hotel-related but too vague to classify.
    12. Set urgency to "high" only for same-day emergencies, ongoing incidents, or issues requiring immediate hotel action. Otherwise use "normal".

    [Examples]
    - Cancel with penalty or refund wording only -> ["reservation_delete"] only
    - Change dates while system says booking missing -> ["reservation_update"] only
    - Payment glitch but asks to change or fix booking -> ["reservation_update"] only
    - Early check-in policy question -> ["policy_qna"] only
    - Date change plus wheelchair rental -> ["reservation_update", "policy_qna"]
    - Date change plus high-floor preference -> ["reservation_update", "policy_qna"]
    - Suite upgrade plus allergy bedding request -> ["reservation_update", "policy_qna"]
    - Promotion price question plus new booking -> ["reservation_create", "policy_qna"]
    - Confirm booking plus humidifier rental -> ["booking_lookup", "policy_qna"]
    - Booking lookup plus baby crib availability -> ["booking_lookup", "policy_qna"]
    - Booking lookup plus invoice reissue -> ["booking_lookup", "policy_qna"]
    - Dirty room complaint plus cancel remaining stay -> ["complaint_or_incident", "reservation_delete"]
    - Wi-Fi outage during a meeting -> ["complaint_or_incident"] only

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

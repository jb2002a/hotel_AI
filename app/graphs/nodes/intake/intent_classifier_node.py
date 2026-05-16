from typing import Any, Iterable

from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, EmailClassification, GraphActionLiteral
from langgraph.types import Command
from langsmith import traceable

# 분류 결과 intent 집합 (멀티 intent 우선 규칙용)
_INFO = frozenset(
    {
        "policy_qna",
        "payment_invoice",
        "promotion_pricing",
        "special_request",
        "complaint_or_incident",
    }
)
_AMBIG = frozenset({"out_of_scope", "unclear", "other"})


def intents_to_actions(intents: Iterable[str]) -> list[GraphActionLiteral]:
    """intent → 그래프 액션 고정 매핑. 멀티 intent 시 정보성(_INFO, booking_lookup) 우선으로 예약 실행 액션을 억제."""
    intent_set = set(intents)

    actions: list[GraphActionLiteral] = []

    has_info_tail = bool(intent_set & _INFO)
    # 정보성 intent 또는 booking_lookup이 있으면: 예약 실행 없이 해당 조회만
    if has_info_tail or ("booking_lookup" in intent_set):
        if intent_set & _INFO:
            actions.append("vector_retrieve")
        if "booking_lookup" in intent_set:
            actions.append("db_retrieve")
        return actions

    # 예약 실행 (최대 1종; 우선순위 고정)
    for pref in ("reservation_delete", "reservation_update", "reservation_create"):
        if pref in intent_set:
            if pref == "reservation_create":
                return ["retrieve_rest_rooms", "reservation_create"]
            if pref == "reservation_update":
                return ["db_retrieve", "reservation_update"]
            return ["db_retrieve", "reservation_delete"]

    # booking_lookup 단독은 위 분기 전에 처리됨; 예약 의도 없고 조회만
    if intent_set <= _AMBIG or not intent_set:
        return []

    return []


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

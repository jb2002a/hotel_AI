from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, ExtractData
from langsmith import traceable


def _build_action_extract_rules(actions: list[str]) -> str:
    action_set = set(actions)
    rules: list[str] = []

    if "reservation_create" in action_set:
        rules.append(
            "- reservation_create: extract new booking name, check_in, and check_out. "
            "Use YYYY-MM-DD when clearly stated."
        )
    if "reservation_update" in action_set:
        rules.append(
            "- reservation_update: extract only the NEW target date(s) after the change. "
            "Do NOT extract existing/current booking dates used only for identification."
        )
    if "reservation_delete" in action_set:
        rules.append(
            "- reservation_delete: extract booking-identifying name and/or date range "
            "(check_in, check_out) for the reservation to cancel."
        )
    if "reservation_search" in action_set:
        rules.append(
            "- reservation_search: extract booking-identifying name and/or date range "
            "for the reservation to look up."
        )
    if not action_set:
        rules.append(
            "- no reservation actions: extract name only if clearly stated. "
            "Leave all date fields null unless the email is clearly about a bookable stay request."
        )

    return "\n".join(rules)


@traceable(name="email_ingest")
def email_ingest(state: EmailAgentState) -> dict:
    """이메일 데이터(name, check_in, check_out) 추출 노드"""

    email_data = state["email_data"]
    actions_raw = state.get("actions") or []
    actions = list(actions_raw) if isinstance(actions_raw, list) else []
    action_rules = _build_action_extract_rules(actions)

    extract_llm = LLM.with_structured_output(ExtractData)
    extract_prompt = f"""
    Extract reservation fields from one hotel customer email.
    Return only the structured fields requested by the schema.

    [Email]
    Subject: {email_data["email_subject"]}
    Body: {email_data["email_content"]}

    [Detected actions]
    {actions if actions else "[]"}

    [Action-aware extraction rules]
    {action_rules}

    [Fields to extract]
    - name: the customer's full name, only if the customer states it in the email. If not found, use null.
    - check_in: check-in date in YYYY-MM-DD format, only if clearly stated or directly inferable per the rules above.
    - check_out: check-out date in YYYY-MM-DD format, only if clearly stated or directly inferable per the rules above.

    [General rules]
    1. Do not guess missing values.
    2. Do not use the sender email address as the customer's name.
    3. Never return the string "null"; use JSON null for missing values.
    4. Relative dates without a clear anchor (e.g. "next day", "tomorrow") must be null.
    5. If an ISO date anchor exists with a relative offset, compute the target date in YYYY-MM-DD.
       Example: "tomorrow 2026-05-19 ... move to the day after" -> check_in: 2026-05-20.
    6. Past visit dates, refund inquiries, lost-item context, or policy-only emails: leave dates null.
    7. For update: "booked on 2025-09-05, want a larger room" -> name only, dates null.
    8. For delete: "cancel 2025-10-20 ~ 2025-10-22" -> check_in: 2025-10-20, check_out: 2025-10-22.
    """
    extract_data = extract_llm.invoke(extract_prompt)

    return {"extract_data": extract_data}

from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, ExtractData
from langsmith import traceable


@traceable(name="email_ingest")
def email_ingest(state: EmailAgentState) -> dict:
    """이메일 데이터(name, check_in, check_out) 추출 노드"""

    email_data = state["email_data"]

    extract_llm = LLM.with_structured_output(ExtractData)
    extract_prompt = f"""
    Extract reservation fields from one hotel customer email.
    Return only the structured fields requested by the schema.

    [Email]
    Subject: {email_data["email_subject"]}
    Body: {email_data["email_content"]}

    [Fields to extract]
    - name: the customer's full name, only if the customer states it in the email. If not found, use null.
    - check_in: check-in date in YYYY-MM-DD format, only if the date is clearly stated or directly inferable. If not found, use null.
    - check_out: check-out date in YYYY-MM-DD format, only if the date is clearly stated or directly inferable. If not found, use null.

    [Rules]
    1. Do not guess missing values.
    2. Do not use the sender email address as the customer's name.
    3. If the email mentions only one date, fill only the matching field and set the other date to null.
    4. Keep all unknown fields as null.
    5. For date change requests: extract the NEW target date(s) the customer wants, not the current/old date.
       Example: "move check-in from 2025-06-10 to 2025-06-15" -> check_in: 2025-06-15, check_out: null.
    6. If the customer only mentions an existing booking without stating a new target date, leave date fields null.
    """
    extract_data = extract_llm.invoke(extract_prompt)

    return {"extract_data": extract_data}

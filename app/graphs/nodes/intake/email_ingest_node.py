from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, ExtractData
from langsmith import traceable


@traceable(name="email_ingest")
def email_ingest(state: EmailAgentState) -> dict:
    """이메일 데이터(name, check_in, check_out) 추출 노드"""

    email_data = state["email_data"]

    extract_llm = LLM.with_structured_output(ExtractData)
    extract_prompt = f"""
    Extract reservation-related fields from this customer email context.

    Return JSON with exactly these keys:
    - name: The full name of the person who sent this email, as they identify themselves.
    - check_in (YYYY-MM-DD if inferable, else null)
    - check_out (YYYY-MM-DD if inferable, else null)

    Subject: {email_data["email_subject"]}
    Body: {email_data["email_content"]}
    """
    extract_data = extract_llm.invoke(extract_prompt)

    return {"extract_data": extract_data}

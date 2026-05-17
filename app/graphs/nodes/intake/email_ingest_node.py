from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, ExtractData
from langsmith import traceable


@traceable(name="email_ingest")
def email_ingest(state: EmailAgentState) -> dict:
    email_data = state["email_data"]

    extract_llm = LLM.with_structured_output(ExtractData)
    extract_prompt = f"""
    Extract reservation-related fields from this customer email context.

    Return JSON with exactly these keys:
    - check_in (YYYY-MM-DD if inferable, else null)
    - check_out (YYYY-MM-DD if inferable, else null)

    Subject: {email_data["email_subject"]}
    Body: {email_data["email_content"]}
    """
    extract_data = extract_llm.invoke(extract_prompt)

    return {"extract_data": extract_data}

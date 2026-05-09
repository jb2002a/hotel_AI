from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, EmailClassification
from langsmith import traceable


@traceable(name="classify_node")
def classify_node(state: EmailAgentState) -> dict:
    # 래퍼에 맞춰서 structured_llm 생성
    structured_llm = LLM.with_structured_output(EmailClassification)

    email_data = state["email_data"]

    # 프롬프트 포맷팅
    classification_prompt = f"""
    Analyze this customer email and classify it:
    
    Email: {email_data['email_subject']}
    Email Content: {email_data['email_content']}

    Provide classification including category, urgency.
    """

    # 래퍼에 맞춰서 구조화된 응답 받기
    classification = structured_llm.invoke(classification_prompt)

    return {"classification": classification}

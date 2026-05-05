import json
from app.schemas.graph_state import EmailAgentState, EmailClassification, EmailData
from app.config.config import USER_MOCK_DATA_PATH, LLM
from langsmith import traceable

_TEST_IDX = 20

@traceable(name="read_email")
def read_email(state: EmailAgentState) -> dict:
    # TODO: 현재는 mock 데이터와 임시적으로 연결, 실제 이메일 서비스와 연동 필요

    # json은 emails내에 subject,body,sender_email,category 필드가 있음 (카테고리는 평가용으로 적어둠, 사용x)
    with open(USER_MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    # 테스트용 인덱스 설정
    mock_data = mock_data[_TEST_IDX]

    email_data = EmailData(
        email_subject=mock_data["subject"],
        email_content=mock_data["body"],
        sender_email=mock_data["sender_email"]
    )

    return {"email_data": email_data}

@traceable(name="classify_intent")
def classify_intent(state: EmailAgentState) -> dict:
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
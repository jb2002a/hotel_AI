from typing import Literal, TypedDict


# 고객의 이메일 데이터 래퍼
class EmailData(TypedDict):
    email_subject: str
    email_content: str
    sender_email: str

# 이메일 분류 결과 래퍼
class EmailClassification(TypedDict):
    category: Literal["reservation", "inquiry", "request", "spam"]
    urgency: Literal["low", "medium", "high", "critical"]

class EmailAgentState(TypedDict):
    # 고객의 이메일 데이터
    email_data: EmailData

    # 이메일 분류 결과
    classification: EmailClassification | None

    # 저장소 (RAG, CRM) 검색 결과
    search_results: list[str] | None
    customer_history: dict | None

    # 생성된 내용
    draft_response: str | None
    messages: list[str] | None



# V1 플로우 
# read_email -> classification -> plan -> (retrieve?) -> draft -> (approval?) -> execution -> END

from typing import Literal, TypedDict
from langchain_core.documents import Document

# 고객의 이메일 데이터 래퍼
class EmailData(TypedDict):
    email_subject: str
    email_content: str
    sender_email: str

# 이메일 분류 결과 래퍼
class EmailClassification(TypedDict):
    category: Literal["normal", "spam"]
    urgency: Literal["normal", "high"]

# 계획 수행 결과 (필요한 단계 목록; 순서는 실행 순서)
class PlanAction(TypedDict):
    actions: list[Literal["retrieve"]]

class EmailAgentState(TypedDict):
    # 고객의 이메일 데이터
    email_data: EmailData

    # 이메일 분류 결과
    classification: EmailClassification | None

    # 플랜 노드 출력 (필요 액션 목록)
    plan: PlanAction | None

    # RAG 검색 결과
    search_results: list[Document] | None

    # 생성된 내용
    draft_response: str | None



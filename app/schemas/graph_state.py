# V1 플로우
# read_email -> classification -> plan -> (vector_retrieve? / db_retrieve?) -> draft -> (approval?) -> execution -> END

from typing import Any, Literal, TypedDict
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
    actions: list[
        Literal[
            "vector_retrieve",
            "db_retrieve",
            "reservation_create",
            "reservation_update",
            "reservation_delete",
        ]
    ]

class ActionSQLite(TypedDict):
    create_sql: str
    update_sql: str
    delete_sql: str


# SQLite 회원/예약 조회 최소 래퍼
class ExtractData(TypedDict):
    name: str | None
    check_in: str | None
    check_out: str | None


class BusinessErrorPayload(TypedDict):
    code: str
    message: str


class EmailAgentState(TypedDict):
    # 고객의 이메일 데이터
    email_data: EmailData

    # 예약 액션 추출 데이터
    extract_data: ExtractData | None

    # 이메일 분류 결과
    classification: EmailClassification | None

    # 플랜 노드 출력 (필요 액션 목록)
    plan: PlanAction | None

    # 벡터 스토어 검색 결과
    vector_retrieve_results: list[Document] | None

    # SQLite 회원/예약 조회 결과
    db_retrieve_results: dict[str, Any] | None

    # 예약 액션 SQL 생성 결과
    action_sqlite: ActionSQLite | None

    # 생성된 내용
    draft_response: str | None

    # 업무 예외 상태 (승인/검토 라우팅용)
    business_error: BusinessErrorPayload | None



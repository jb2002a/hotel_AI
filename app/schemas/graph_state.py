# V1 플로우
# email_ingest -> email_classification(actions + policy_queries) -> prepare(retrieve) -> sql_build -> reply_draft -> manager_approval -> END

from typing import Any, Literal, TypedDict

from langchain_core.documents import Document


# 고객의 이메일 데이터 래퍼
class EmailData(TypedDict):
    email_subject: str
    email_content: str
    sender_email: str


# 이메일 분류 결과 (LLM이 actions·policy_queries 직접 출력)
class EmailClassification(TypedDict):
    actions: list["GraphActionLiteral"]
    policy_queries: list[str] | None
    category: Literal["normal", "spam"]
    urgency: Literal["normal", "high"]


# 그래프 실행 액션 리터럴
GraphActionLiteral = Literal[
    "reservation_search",
    "reservation_create",
    "reservation_update",
    "reservation_delete",
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

    # 실행 액션 목록 (email_classification_node에서 설정)
    actions: list[GraphActionLiteral] | None

    # 정책 RAG 검색용 쿼리 (email_classification_node에서 설정)
    policy_queries: list[str] | None

    # 벡터 스토어 검색 결과
    vector_retrieve_results: list[Document] | None

    # SQLite 회원/예약 조회 결과
    db_retrieve_results: dict[str, Any] | None

    # 남은 객실 조회 결과
    rest_room_retrieve_results: dict[str, int] | None

    # 예약 액션 SQL 생성 결과
    action_sqlite: ActionSQLite | None

    # 생성된 내용
    draft_response: str | None

    # 매니저 코멘트 (interrupt resume 시 설정)
    manager_comment: str | None

    # 업무 예외 상태 (승인/검토 라우팅용)
    business_error: BusinessErrorPayload | None


def build_approval_payload(state: EmailAgentState) -> dict[str, Any]:
    """UI/interrupt용 승인 스냅샷. state에 중복 저장하지 않는다."""
    return {
        "email_data": state.get("email_data"),
        "extract_data": state.get("extract_data"),
        "actions": state.get("actions"),
        "policy_queries": state.get("policy_queries"),
        "db_retrieve_results": state.get("db_retrieve_results"),
        "rest_room_retrieve_results": state.get("rest_room_retrieve_results"),
        "action_sqlite": state.get("action_sqlite"),
        "draft_response": state.get("draft_response"),
        "business_error": state.get("business_error"),
    }

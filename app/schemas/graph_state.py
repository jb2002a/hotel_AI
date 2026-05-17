# V1 플로우
# email_ingest -> intent_classifier(actions 고정) -> prepare(retrieve + sql) -> reply_draft -> manager_approval -> END

from typing import Any, Literal, TypedDict

from langchain_core.documents import Document


# 고객의 이메일 데이터 래퍼
class EmailData(TypedDict):
    email_subject: str
    email_content: str
    sender_email: str


# intent 분류 결과
class EmailClassification(TypedDict):
    intents: list[
        Literal[
            "policy_qna",
            "booking_lookup",
            "reservation_create",
            "reservation_update",
            "reservation_delete",
            "payment_invoice",
            "promotion_pricing",
            "special_request",
            "complaint_or_incident",
            "out_of_scope",
            "unclear",
            "other",
        ]
    ]
    category: Literal["normal", "spam"]
    urgency: Literal["normal", "high"]


# 액션 리터럴
GraphActionLiteral = Literal[
    "vector_retrieve",
    "db_retrieve",
    "retrieve_rest_rooms",
    "reservation_create",
    "reservation_update",
    "reservation_delete",
]

# EmailClassification.intents Literal과 1:1 대응
INTENT_ACTION_MAP: dict[str, list[GraphActionLiteral]] = {
    "policy_qna": ["vector_retrieve"],
    "booking_lookup": ["db_retrieve"],
    "reservation_create": ["retrieve_rest_rooms", "reservation_create"],
    "reservation_update": ["db_retrieve", "reservation_update"],
    "reservation_delete": ["db_retrieve", "reservation_delete"],
    "payment_invoice": ["vector_retrieve"],
    "promotion_pricing": ["vector_retrieve"],
    "special_request": ["vector_retrieve"],
    "complaint_or_incident": ["vector_retrieve"],
    "out_of_scope": [],
    "unclear": [],
    "other": [],
}


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

    # intent 기반 고정 액션 목록 (intent_classifier_node에서 설정)
    actions: list[GraphActionLiteral] | None

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
        "db_retrieve_results": state.get("db_retrieve_results"),
        "rest_room_retrieve_results": state.get("rest_room_retrieve_results"),
        "action_sqlite": state.get("action_sqlite"),
        "draft_response": state.get("draft_response"),
        "business_error": state.get("business_error"),
    }

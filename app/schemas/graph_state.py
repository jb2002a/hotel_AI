# V1 플로우
# email_classification(actions + policy_queries) -> email_ingest -> prepare(retrieve) -> sql_build -> reply_draft -> manager_approval -> END

from typing import Any, Literal, TypedDict

from langchain_core.documents import Document


# 고객의 이메일 데이터 래퍼
class EmailData(TypedDict):
    email_subject: str
    email_content: str
    sender_email: str


# 이메일 분류 결과 (LLM이 actions·policy_queries 직접 출력)
class EmailClassification(TypedDict):
    actions: list[str]
    policy_queries: list[str] | None
    category: Literal["normal", "spam"]
    urgency: Literal["normal", "high"]


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


class ManagerClassification(TypedDict):
    category: Literal["normal", "spam"] | None
    urgency: Literal["normal", "high"] | None
    actions: list[str]


class ManagerError(TypedDict):
    type: str
    code: str
    message: str


class ManagerApprovalPayload(TypedDict):
    email_data: EmailData
    classification: ManagerClassification
    extract_data: ExtractData | None
    draft_response: str | None
    action_sqlite: ActionSQLite | None
    errors: list[ManagerError]


class EmailAgentState(TypedDict):
    # 고객의 이메일 데이터
    email_data: EmailData

    # 예약 액션 추출 데이터
    extract_data: ExtractData | None

    # 이메일 분류 결과
    classification: EmailClassification | None

    # 실행 액션 목록 (email_classification_node에서 설정)
    actions: list[str] | None

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

    # 매니저에게 표시할 에러 목록
    manager_errors: list[ManagerError] | None


def _build_manager_errors(state: EmailAgentState) -> list[ManagerError]:
    manager_errors = state.get("manager_errors")
    if manager_errors:
        return list(manager_errors)

    errors: list[ManagerError] = []
    business_error = state.get("business_error")
    if business_error:
        errors.append(
            {
                "type": "business_error",
                "code": business_error["code"],
                "message": business_error["message"],
            }
        )
    return errors


def _build_manager_classification(state: EmailAgentState) -> ManagerClassification:
    classification = state.get("classification") or {}
    actions_raw = state.get("actions")
    actions = list(actions_raw) if isinstance(actions_raw, list) else []
    return {
        "category": classification.get("category"),
        "urgency": classification.get("urgency"),
        "actions": actions,
    }


def _build_manager_email_data(state: EmailAgentState) -> EmailData:
    email_data = state.get("email_data")
    if email_data:
        return email_data
    return {
        "email_subject": "",
        "email_content": "",
        "sender_email": "",
    }


def build_approval_payload(state: EmailAgentState) -> ManagerApprovalPayload:
    """UI/interrupt용 매니저 승인 스냅샷. state에 중복 저장하지 않는다."""
    return {
        "email_data": _build_manager_email_data(state),
        "classification": _build_manager_classification(state),
        "extract_data": state.get("extract_data"),
        "draft_response": state.get("draft_response"),
        "action_sqlite": state.get("action_sqlite"),
        "errors": _build_manager_errors(state),
    }

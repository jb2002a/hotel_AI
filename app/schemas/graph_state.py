# V1 플로우

# email_ingest -> intent_classifier(actions 고정) -> prepare(retrieve + sql) -> reply_draft -> manager_approval -> END



from typing import Any, Literal, NotRequired, TypedDict

from langchain_core.documents import Document



# 고객의 이메일 데이터 래퍼

class EmailData(TypedDict):

    email_subject: str

    email_content: str

    sender_email: str



# 이메일 분류 결과 래퍼

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





GraphActionLiteral = Literal[

    "vector_retrieve",

    "db_retrieve",

    "retrieve_rest_rooms",

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





class ApprovalPacket(TypedDict):

    email_data: EmailData

    extract_data: ExtractData | None

    actions: list[GraphActionLiteral] | None

    db_retrieve_results: dict[str, Any] | None

    rest_room_retrieve_results: dict[str, int] | None

    action_sqlite: ActionSQLite | None

    draft_response: str | None

    business_error: BusinessErrorPayload | None





class EmailAgentState(TypedDict):



    mock_email_idx: NotRequired[int]



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



    # 승인 노드에서 UI에 노출할 패킷 스냅샷

    approval_packet: ApprovalPacket | None



    # 매니저 코멘트

    manager_comment: str | None



    # 업무 예외 상태 (승인/검토 라우팅용)

    business_error: BusinessErrorPayload | None




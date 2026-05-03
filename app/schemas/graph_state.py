from typing import Literal, TypedDict

class AgentState(TypedDict):
    # 입력 데이터
    customer_email: str

    # 분류 정보
    category: Literal["reservation", "inquiry", "simple"]
    entities: dict # 추출된 정보 (예약번호, 날짜 등)
    
    # 검색된 지식/데이터
    retrieved_docs: list # 규정집 검색 결과
    db_data: dict        # DB 조회 결과
    
    # 액션
    draft_email: str     # 작성된 답장 초안
    action_payload: dict # DB 반영용 JSON (예: {"update": "check_in_date", "value": "2026-05-10"})
    
    # 제어 변수
    is_approved: bool    # 승인 여부
    error_log: str       # 에러 발생 시 기록



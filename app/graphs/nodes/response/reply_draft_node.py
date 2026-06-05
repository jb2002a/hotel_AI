# 답변 생성 노드, policy / member_booking / vacancy retrieve 결과가 있으면 참조.

from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState
from langsmith import traceable

_tem_hotel_name = "그랜드 시그니처 호텔 & 리조트"
_tem_manager_name = "김아영"


@traceable(name="reply_draft_node")
def reply_draft_node(state: EmailAgentState) -> dict:
    if state.get("business_error"):
        return {}

    vector_docs = state.get("vector_retrieve_results")
    db_payload = state.get("db_retrieve_results")
    rest_room_payload = state.get("rest_room_retrieve_results")
    classification = state.get("classification")

    vector_block = "\n".join(d.page_content for d in vector_docs) if vector_docs else ""
    db_block = str(db_payload) if db_payload is not None else ""

    context_parts: list[str] = []
    if vector_block:
        context_parts.append(f"[벡터 검색 근거]\n{vector_block}")
    if db_block:
        context_parts.append(f"[DB 조회(회원/예약)]\n{db_block}")
    if rest_room_payload is not None:
        context_parts.append(f"[DB 조회(잔여 객실)]\n{rest_room_payload}")
    search_results = "\n\n".join(context_parts) if context_parts else "(없음)"

    email_data = state["email_data"]

    email_subject = email_data["email_subject"]
    email_content = email_data["email_content"]
    actions = state.get("actions") or []
    policy_queries = state.get("policy_queries") or []
    actions_block = ", ".join(actions) if actions else "(없음)"
    policy_queries_block = (
        "; ".join(policy_queries) if policy_queries else "(없음)"
    )

    draft_prompt = f"""
    당신은 {_tem_hotel_name}의 매니저 {_tem_manager_name}입니다.
    고객에게 보낼 이메일 본문만 작성하세요.
    분석 과정, 제목, JSON, 코드블록, 설명 문장은 출력하지 마세요.

    [고객 이메일]
    제목: {email_subject}
    본문: {email_content}

    [실행 액션]
    {actions_block}

    [정책 조회 질문]
    {policy_queries_block}

    [참고 가능한 근거]
    {search_results}

    [작성 순서]
    1. 고객이 무엇을 요청했는지 파악합니다.
    2. 참고 가능한 근거가 요청과 관련 있으면 그 내용을 우선 사용합니다.
    3. 근거에 없는 내용은 사실처럼 단정하지 말고 "확인이 필요합니다"라고 안내합니다.
    4. 잔여 객실 정보에 vacant_room_count가 있고 값이 0이면, 현재 예약 가능한 객실이 없다고 명확히 안내하고 사과와 대안(대기 또는 다른 일정 문의)을 제시합니다.
    5. 한국어로, 공손하고 전문적인 호텔 비즈니스 톤으로 작성합니다.
    6. 아래 템플릿의 문단 순서를 유지합니다.

    [출력 템플릿]
    안녕하세요, {_tem_hotel_name} 매니저 {_tem_manager_name}입니다.

    문의 주신 내용에 대한 답변은 아래와 같습니다.

    (고객 요청에 대한 핵심 답변을 1~3개 문단으로 작성)

    추가로 궁금하신 점이나 변경 사항이 있으시면 언제든지 이 메일 혹은 고객센터로 연락해 주시기 바랍니다.

    고객님을 뵙게 될 날을 고대하겠습니다.

    {_tem_manager_name} 드림
    """

    draft_response = LLM.invoke(draft_prompt)
    response_text = getattr(draft_response, "content", str(draft_response))

    return {"draft_response": response_text}

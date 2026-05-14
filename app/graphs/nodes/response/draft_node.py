# 답변 생성 노드, vector_retrieve / db_retrieve 결과가 있으면 참조.

from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState
from langsmith import traceable

_tem_hotel_name = "그랜드 시그니처 호텔 & 리조트"
_tem_manager_name = "김아영"


@traceable(name="draft_node")
def draft_node(state: EmailAgentState) -> dict:
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
    intents = classification.get("intents", []) if classification else []
    intents_block = ", ".join(intents) if intents else "(없음)"

    draft_prompt = f"""
    당신은 {_tem_hotel_name}의 매니저 {_tem_manager_name}입니다.
    당신의 업무는 고객의 문의에 대해 정확하고 정중하게 답변하는 것입니다.

    [입력 - 고객 이메일]
    제목: {email_subject}
    본문: {email_content}

    [입력 - 검색 근거]
    {search_results}

    [입력 - 해당 글의 의도]
    해당 글의 의도: {intents_block}

    작성 규칙:
    1) 검색 근거에 있는 정보가 관련 있으면 반드시 우선 반영하세요.
    2) 근거에 없는 사실은 단정하지 말고, 확인이 필요하다고 명시하세요.
    3) 반드시 한국어로 작성하고, 공손하고 전문적인 비즈니스 톤을 유지하세요.
    4) 아래 이메일 템플릿 구조를 반드시 지키세요.
    5) 최종 출력은 고객에게 보낼 이메일 본문만 출력하세요. (머리말/분석 과정/JSON 금지)
    6) [DB 조회(잔여 객실)]의 vacant_room_count가 0이면, 현재 예약 가능한 객실이 없음을 명확히 안내하고 사과 및 대안(대기/다른 일정 문의)을 함께 제시하세요.
    7) "해당 글의 의도"를 참고해 답변 방향을 잡으세요.

    출력 템플릿(형식 고정):
    안녕하세요, {_tem_hotel_name} 매니저 {_tem_manager_name}입니다.

    문의 주신 내용에 대한 답변은 아래와 같습니다.

    (고객 질문에 대한 핵심 답변을 작성)

    추가로 궁금하신 점이나 변경 사항이 있으시면 언제든지 이 메일 혹은 고객센터로 연락해 주시기 바랍니다.

    고객님을 뵙게 될 날을 고대하겠습니다.

    {_tem_manager_name} 드림
    """

    draft_response = LLM.invoke(draft_prompt)
    response_text = getattr(draft_response, "content", str(draft_response))

    return {"draft_response": response_text}

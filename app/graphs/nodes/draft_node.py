# 답변 생성 노드, search_results가 있으면 참조.

from app.schemas.graph_state import EmailAgentState
from langsmith import traceable
from app.config.config import LLM

@traceable(name="draft_node")
def draft_node(state: EmailAgentState) -> dict:
    search_results = state["search_results"] if state["search_results"] else []

    email_data = state["email_data"]

    email_subject = email_data["email_subject"]
    email_content = email_data["email_content"]

    draft_prompt = f"""
    당신은 호텔 고객 응대 이메일 작성 도우미입니다.
    목표: 고객 이메일(제목/본문)에 대해 정중하고 정확한 답변 초안을 작성하세요.
    
    [입력 - 고객 이메일]
    제목: {email_subject}
    본문: {email_content}

    [입력 - 검색 근거(top-k)]
    {search_results}

    작성 규칙:
    1) 검색 근거(top-k)에 있는 정보가 관련 있으면 반드시 우선 반영하세요.
    2) 근거에 없는 사실은 단정하지 말고, 확인이 필요하다고 명시하세요.
    3) 고객 질문의 핵심을 먼저 답하고, 필요한 조건/예외/추가 안내를 짧게 덧붙이세요.
    4) 한국어로 작성하고, 톤은 친절하고 전문적으로 유지하세요.
    5) 불필요한 장문 설명은 피하고 실무적으로 간결하게 작성하세요.
    6) 최종 출력은 고객에게 보낼 이메일 본문만 출력하세요. (머리말/분석 과정/JSON 금지)
    이제 위 정보를 바탕으로 답변 이메일 본문을 작성하세요.
    """

    draft_response = LLM.invoke(draft_prompt)
    response_text = getattr(draft_response, "content", str(draft_response))

    return {"draft_response": response_text}

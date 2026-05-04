from app.schemas.graph_state import EmailAgentState, PlanAction
from app.config.config import LLM



def plan_action(state: EmailAgentState) -> dict:
    email_data = state['email_data']

    subject = email_data['email_subject']
    content = email_data['email_content']

    structured_llm = LLM.with_structured_output(PlanAction)

    plan_action_prompt = f"""From the email subject and body, list every step needed to handle the request.

    Use these actions only:
    - **retriever**: vector DB search (policies, FAQs, unstructured knowledge).
    - **read**, **create**, **update**, **delete**: ORM operations on relational data (load, insert, change, remove records).

    Include all that clearly apply. Put **retriever** (and **read** if needed) before mutating (**create** / **update** / **delete**) when context or current rows are required. Omit steps that are not justified by the email.

    Subject: {subject}
    Body: {content}
    """

    plan = structured_llm.invoke(plan_action_prompt)
    return {"plan": plan}








if __name__ == "__main__":
    # python -m app.graphs.nodes.plan_node
    state: EmailAgentState = {
        "email_data": {
            "email_subject": "Re: 예약 변경 및 레이트 체크아웃 문의",
            "email_content": (
                "안녕하세요.\n"
                "예약번호 HTL-2026-9912 (3/12~3/15) 인데, 체크아웃을 오후 2시로 연장 가능한지와 "
                "레이트 체크아웃 요금이 얼마인지 알려주세요.\n"
                "또한 투숙 인원을 성인 2명에서 3명으로 변경 부탁드립니다.\n"
                "감사합니다.\n"
                "jane@example.com"
            ),
            "sender_email": "jane@example.com",
        },
        "classification": {
            "category": "request",
            "urgency": "medium",
        },
    }
    out = plan_action(state)
    print(out)

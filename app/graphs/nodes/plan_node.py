from app.schemas.graph_state import EmailAgentState, PlanAction
from app.config.config import LLM
from langsmith import traceable

@traceable(name="plan_action")
def plan_action(state: EmailAgentState) -> PlanAction:
    email_data = state['email_data']

    subject = email_data['email_subject']
    content = email_data['email_content']

    structured_llm = LLM.with_structured_output(PlanAction)

    plan_action_prompt = f"""Decide whether retrieval is needed to answer this email.

    Return actions using only this schema:
    - "retrieve": use vector DB search (policies, FAQs)

    Rules:
    - If retrieval is needed, return actions as ["retrieve"].
    - If retrieval is not needed, return actions as [].
    - Do not return any other action names.

    Subject: {subject}
    Body: {content}
    """

    plan = structured_llm.invoke(plan_action_prompt)
    return plan


if __name__ == "__main__":
    # python -m app.graphs.nodes.plan_node
    state: EmailAgentState = {
        "email_data": {
            "email_subject": "레이트 체크아웃 문의",
            "email_content": (
                "안녕하세요.\n"
                "제가 부득이하게 늦게 체크아웃을 해야할것같은데, 3시쯤에 나갈것 같은데요, 혹시 얼마를 더 내야하나요?"
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

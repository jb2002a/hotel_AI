from app.schemas.graph_state import EmailAgentState, PlanAction
from app.config.config import LLM
from langsmith import traceable

@traceable(name="plan_action")
def plan_action(state: EmailAgentState) -> dict:
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
    return {"plan": plan}

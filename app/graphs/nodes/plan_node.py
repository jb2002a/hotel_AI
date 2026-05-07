from app.schemas.graph_state import EmailAgentState, PlanAction
from app.config.config import LLM
from langsmith import traceable

@traceable(name="plan_action")
def plan_action(state: EmailAgentState) -> dict:
    email_data = state['email_data']

    subject = email_data['email_subject']
    content = email_data['email_content']

    structured_llm = LLM.with_structured_output(PlanAction)

    plan_action_prompt = f"""Decide what retrieval is needed to answer this email.

    Return actions using only these names (execution order when both: vector_retrieve, then db_retrieve):
    - "vector_retrieve": vector DB / RAG search (policies, FAQs, general knowledge base)
    - "db_retrieve": member and room booking lookup for the sender email (SQLite)

    Rules:
    - Use "vector_retrieve" when policy/FAQ/general hotel info from the knowledge base is needed.
    - Use "db_retrieve" when the reply needs the sender's membership or reservation data.
    - You may return both, one, or neither. Examples: [], ["vector_retrieve"], ["db_retrieve"], ["vector_retrieve", "db_retrieve"].
    - Do not return any other action names.

    Subject: {subject}
    Body: {content}
    """

    plan = structured_llm.invoke(plan_action_prompt)
    return {"plan": plan}

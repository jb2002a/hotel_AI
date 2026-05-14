from app.config.config import LLM
from app.schemas.graph_state import EmailAgentState, EmailClassification
from langsmith import traceable


@traceable(name="classify_node")
def classify_node(state: EmailAgentState) -> dict:
    structured_llm = LLM.with_structured_output(EmailClassification)
    email_data = state["email_data"]
    classification_prompt = f"""
    Analyze the customer email and return classification as JSON.
    Subject: {email_data['email_subject']}
    Body: {email_data['email_content']}
    Sender: {email_data['sender_email']}
    You must return exactly these fields:
    - intents: list of 1 or more items chosen only from:
      ["policy_qna","booking_lookup","reservation_create","reservation_update","reservation_delete","payment_invoice","promotion_pricing","special_request","complaint_or_incident","out_of_scope","unclear","other"]
      (Use multiple intents if needed.)
    - category: one of ["normal", "spam"]
    - urgency: one of ["normal", "high"]
    Rules:
    - Do not invent labels outside the allowed list.
    - If intent is ambiguous, include "unclear".
    - If request is outside hotel domain, include "out_of_scope".
    """
    classification = structured_llm.invoke(classification_prompt)
    return {"classification": classification}

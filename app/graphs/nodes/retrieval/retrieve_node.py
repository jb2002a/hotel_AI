from langsmith import traceable

from app.schemas.graph_state import EmailAgentState
from app.services.db_service import get_member_and_booking_by_email
from app.services.vector_store_service import get_vector_store_from_chroma


@traceable(name="vector_retrieve")
def vector_retrieve(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    query = f"{email_data['email_subject']}\n{email_data['email_content']}"
    vector_store = get_vector_store_from_chroma()
    search_results = vector_store.similarity_search(query, k=3)
    print("vector_retrieve done")
    return {"vector_retrieve_results": search_results}


@traceable(name="db_retrieve")
def db_retrieve(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    email = email_data["sender_email"]
    member_and_bookings = get_member_and_booking_by_email(email)
    return {"db_retrieve_results": member_and_bookings}

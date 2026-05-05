from langsmith import traceable
from app.services.vector_store_service import get_vector_store_from_chroma
from app.schemas.graph_state import EmailAgentState

@traceable(name="retrieve_from_vector_store")
def retrieve_from_vector_store(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    query = f"{email_data['email_subject']}\n{email_data['email_content']}"
    vector_store = get_vector_store_from_chroma()
    search_results = vector_store.similarity_search(query, k=3)
    print("retrieve done")
    return {"search_results": search_results}

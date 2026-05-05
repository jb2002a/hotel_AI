from langsmith import traceable
from app.services.vector_store_service import get_vector_store_from_chroma
from langchain_core.documents import Document

@traceable(name="retrieve_from_vector_store")
def retrieve_from_vector_store(query: str) -> list[Document]:
    vector_store = get_vector_store_from_chroma()
    return vector_store.similarity_search_with_score(query)

if __name__ == "__main__":
    # python -m app.services.vector_store_service
    print(retrieve_from_vector_store("우리 아이가 초등학생인데 헬스장을 갈 수 있나요?"))




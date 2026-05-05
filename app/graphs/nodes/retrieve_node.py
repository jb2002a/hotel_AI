from langsmith import traceable
from app.services.vector_store_service import get_vector_store_from_chroma
from langchain_core.documents import Document

@traceable(name="retrieve_from_vector_store")
def retrieve_from_vector_store(query: str) -> list[Document]:
    vector_store = get_vector_store_from_chroma()
    search_results = vector_store.similarity_search(query, k=3)
    print("retrieve done")
    return search_results

if __name__ == "__main__":
    # python -m app.graphs.nodes.retrieve_node
    print(retrieve_from_vector_store("우리 아이가 초등학생인데 헬스장을 갈 수 있나요?"))




from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.config.config import EMBEDING_MODEL, CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
from langchain_core.documents import Document
from langsmith import traceable


@traceable(name="get_vector_store_from_chroma")
def get_vector_store_from_chroma() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDING_MODEL)
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )


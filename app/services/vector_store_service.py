from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.config.config import EMBEDING_MODEL, CHROMA_DB_PATH, CHROMA_COLLECTION_NAME


@lru_cache(maxsize=1)
def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDING_MODEL)


@lru_cache(maxsize=1)
def get_vector_store_from_chroma() -> Chroma:
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=_get_embeddings(),
        persist_directory=CHROMA_DB_PATH,
    )


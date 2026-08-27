from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    EMBEDDING_PROVIDER,
    EMBEDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
)


@lru_cache(maxsize=1)
def _get_embeddings():
    provider = EMBEDDING_PROVIDER
    if provider == "openai":
        return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)
    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=EMBEDING_MODEL)
    raise ValueError(
        f"지원하지 않는 EMBEDDING_PROVIDER={provider!r}. "
        "openai 또는 huggingface 를 사용하세요."
    )


def _collection_is_empty(vector_store: Chroma) -> bool:
    try:
        return int(vector_store._collection.count()) == 0
    except Exception:
        return True


def _ensure_policy_index(vector_store: Chroma) -> None:
    if not _collection_is_empty(vector_store):
        return
    from app.rag.policy_bootstrap import load_policy_documents_from_docx

    documents = load_policy_documents_from_docx()
    if not documents:
        raise RuntimeError("정책 문서 청크가 비어 있어 인덱스를 만들 수 없습니다.")
    vector_store.add_documents(documents=documents)


@lru_cache(maxsize=1)
def get_vector_store_from_chroma() -> Chroma:
    Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
    vector_store = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=_get_embeddings(),
        persist_directory=CHROMA_DB_PATH,
    )
    _ensure_policy_index(vector_store)
    return vector_store

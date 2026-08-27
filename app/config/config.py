import os
import pathlib

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

BASE_DIR = pathlib.Path(__file__).parent.parent.parent
USER_MOCK_DATA_PATH = BASE_DIR / "resources" / "happy_mock_dataset.jsonl"
DOCX_DATA_PATH = BASE_DIR / "resources" / "호텔 이용 및 환불 규정집.docx"
DB_PATH = BASE_DIR / "app" / "database" / "mock_hotel.db"

# openai: Railway/데모 기본. huggingface: 로컬 평가용 BGE-M3.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").strip().lower()
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
).strip()
EMBEDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3").strip()

_chroma_env = os.getenv("CHROMA_DB_PATH", "").strip()
CHROMA_DB_PATH = _chroma_env or str(BASE_DIR / "chroma_db")
CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME", "guideline_collection"
).strip()

LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
EM_EVAL_OUT_DIR = BASE_DIR / "artifacts" / "eval"
EM_EVAL_INDICES: list[int] | None = None


def frontend_origins() -> list[str]:
    raw = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

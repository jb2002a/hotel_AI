import pathlib
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = pathlib.Path(__file__).parent.parent.parent

USER_MOCK_DATA_PATH = BASE_DIR / "resoruces" / "happy_mock_dataset.jsonl"
DOCX_DATA_PATH = BASE_DIR / "resoruces" / "호텔 이용 및 환불 규정집.docx"

DB_PATH = BASE_DIR / "app" / "database" / "mock_hotel.db"

EMBEDING_MODEL = "BAAI/bge-m3"
CHROMA_DB_PATH = "./chroma_db"
CHROMA_COLLECTION_NAME = "guideline_collection"

LLM = ChatOpenAI(model="gpt-4o-mini")

EM_EVAL_OUT_DIR = BASE_DIR / "artifacts" / "eval"
EM_EVAL_INDICES: list[int] | None = None

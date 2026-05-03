import pathlib
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = pathlib.Path(__file__).parent.parent.parent

USER_MOCK_DATA_PATH = BASE_DIR / "resoruces" / "mock_data.json"

LLM = ChatOpenAI(model="gpt-4o-mini")
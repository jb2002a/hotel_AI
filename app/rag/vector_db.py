from llama_cloud import AsyncLlamaCloud
from dotenv import load_dotenv
import os
from app.config.config import DOCX_DATA_PATH
import asyncio
from langsmith import traceable

load_dotenv(override=True)

client = AsyncLlamaCloud(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))

@traceable(name="upload_and_parse_document")
async def upload_and_parse_document():
    file_obj = await client.files.create(file=DOCX_DATA_PATH, purpose="parse")
    return file_obj

@traceable(name="parse_document")
async def parse_document(file_obj):
    result = await client.parsing.parse(
    file_id=file_obj.id,
    tier="cost_effective",
    version="latest",
    expand=["items"],

    )
    return result

@traceable(name="main")
async def main():
    file_obj = await upload_and_parse_document()
    result = await parse_document(file_obj)
    print("done")


# TODO : 파싱한 데이터 헤더 전처리

if __name__ == "__main__":
    # python -m app.rag.vector_db
    asyncio.run(main())



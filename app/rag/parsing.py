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
async def parse_document(file_obj) -> str:
    result = await client.parsing.parse(
    file_id=file_obj.id,
    tier="cost_effective",
    version="latest",
    expand=["markdown"],

    )
    pages = getattr(getattr(result, "markdown", None), "pages", None) or []
    markdown_context = "\n\n".join(
        page.markdown.strip()
        for page in pages
        if getattr(page, "success", True) and getattr(page, "markdown", None)
    )

    return markdown_context

@traceable(name="parsing_pipeline")
async def parsing_pipeline() -> str:
    file_obj = await upload_and_parse_document()
    result = await parse_document(file_obj)
    return result

if __name__ == "__main__":
    # python -m app.rag.vector_db
    result = asyncio.run(parsing_pipeline())




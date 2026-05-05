from langchain_text_splitters import MarkdownHeaderTextSplitter
from langsmith import traceable
from app.rag.parsing import parsing_pipeline
import asyncio
from langchain_chroma import Chroma
from app.config.config import EMBEDING_MODEL, CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

def get_vector_store_from_chroma() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDING_MODEL)
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )

@traceable(name="split_markdown_document")
async def split_markdown_document() -> list[Document]:
    markdown_document = await parsing_pipeline()
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on, strip_headers=False)
    documents = markdown_splitter.split_text(markdown_document)
    return documents

@traceable(name="save_chunks_to_chroma")
def save_chunks_to_chroma(documents: list[Document]) -> None:
    vector_store = get_vector_store_from_chroma()
    # WARINING!!! -> 현재 임시용으로 매번 컬렉션을 리셋함, 실사용에서는 해제
    vector_store.reset_collection() 
    vector_store.add_documents(documents=documents)
    print(f"Saved Done, Total saved nodes: {vector_store._collection.count()}")   

@traceable(name="split_and_save_pipeline")
async def split_and_save_pipeline() -> None:
    documents = await split_markdown_document()
    save_chunks_to_chroma(documents)  
    
if __name__ == "__main__":
    # python -m app.rag.split_vector
    asyncio.run(split_and_save_pipeline())


    




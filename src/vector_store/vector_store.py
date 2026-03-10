import json

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_community.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
import chromadb
from src.config.config import config

_COLLECTION_MAP = {
    "agentic": config.AGENTIC_COLLECTION_NAME,
    "hybrid": config.COLLECTION_NAME,
}

class VectorStoreManager:
    """Manages ChromaDB vector store operations."""

    def __init__(self, type="agentic"):
        if hasattr(self, "vector_store"):
            return
        self.client = chromadb.CloudClient(
            api_key=config.CHROMA_API_KEY,
            tenant=config.CHROMA_TENANT,
            database=config.CHROMA_DB
        )

        self.vector_store = Chroma(
            collection_name=_COLLECTION_MAP.get(type, config.COLLECTION_NAME),
            embedding_function=HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL),
            # embedding_function=OpenAIEmbeddings("text-embedding-3-small"),
            client=self.client
        )

    def add_documents(self, documents: list[Document]) -> None:
        """Normalize and add documents to the vector store."""
        if not documents:
            return
        print(f"Adding {len(documents)} documents to vector store...")
        self.vector_store.add_documents(documents=list(map(_normalize, documents)))


def _normalize(doc: Document) -> Document:
    """Serialize any list/dict metadata values to JSON strings for Chroma."""
    md = {
        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
        for k, v in (doc.metadata or {}).items()
    }
    return Document(page_content=doc.page_content, metadata=md)
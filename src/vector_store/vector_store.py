import json

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_community.docstore.document import Document
from langchain_community.embeddings import SentenceTransformerEmbeddings

from src.config.config import config

_CHROMA_SETTINGS = Settings(anonymized_telemetry=False, is_persistent=True)

class VectorStoreManager:
    """Manages ChromaDB vector store operations."""

    def __init__(self):
        self.vector_store = Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=SentenceTransformerEmbeddings(model_name=config.EMBEDDING_MODEL),
            persist_directory=config.CHROMA_PERSIST_DIRECTORY,
            client_settings=_CHROMA_SETTINGS,
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
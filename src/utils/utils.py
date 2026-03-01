from typing import Any, Dict
import json
from typing import Any, Dict, Optional
from src.prompts.chunking import METADATA_CHUNK_SYSTEM
from src.vector_store.vector_store import VectorStoreManager

from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from src.utils.openai_client import openai_client

import dotenv
import os

dotenv.load_dotenv()


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        return None
    
vector_store = VectorStoreManager().vector_store

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)

llm = openai_client

_metadata_chain = ChatPromptTemplate.from_messages([
    ("system", METADATA_CHUNK_SYSTEM),
    ("human", "{text}"),
]) | llm

_METADATA_FALLBACK: dict[str, Any] = {
    "content_type": "concept",
    "domain": "",
    "has_code": False,
}


def extract_metadata(text: str) -> dict[str, Any]:
    """Return LLM-generated metadata for a text chunk."""
    try:
        return json.loads(_metadata_chain.invoke({"text": text}).content)
    except Exception:
        return _METADATA_FALLBACK.copy()

def nav_fields(index: int, total: int) -> dict[str, Any]:
    """Return chunk navigation fields for a given index / total."""
    return {
        "chunk_index":      index,
        "total_chunks":     total,
        "position_pct":     round(index / max(total - 1, 1) * 100, 1),
        "prev_chunk_index": index - 1 if index > 0 else None,
        "next_chunk_index": index + 1 if index < total - 1 else None,
    }

def make_semantic_chunker(threshold: float = 0.80) -> SemanticChunker:
    """Return a SemanticChunker with the shared embedding model."""
    return SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=threshold,
    )

def store(docs: list[Document]) -> None:
    """Persist documents to the shared vector store."""
    if docs:
        vector_store.add_documents(docs)
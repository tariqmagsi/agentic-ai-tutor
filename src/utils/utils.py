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

_active_store_type: str = "agentic"

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
    "content_type": "concept"
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

def make_semantic_chunker(threshold: float = 1.0) -> SemanticChunker:
    """Return a SemanticChunker with the shared embedding model."""
    return SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=threshold,
    )

def set_active_store_type(type: str) -> None:
    """Set which collection store() writes to. Call before running processors."""
    global _active_store_type
    _active_store_type = type
    print(f"[utils] Active store type set to: {type}")

def store(docs: list[Document], type: str = None) -> None:
    """Persist documents to the vector store using the active store type."""
    store_type = type or _active_store_type
    if docs:
        print(f"[utils] Storing {len(docs)} docs to '{_active_store_type}' collection")
        VectorStoreManager(type=store_type).add_documents(docs)

from urllib.parse import urlparse, parse_qs

def get_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    parsed = urlparse(url)
    
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        # e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ
        return parse_qs(parsed.query).get('v', [None])[0]
    elif parsed.hostname == 'youtu.be':
        # e.g. https://youtu.be/dQw4w9WgXcQ
        return parsed.path.lstrip('/')
    
    return None

def is_youtube_url(url):
    """Check if a URL is a YouTube link."""
    parsed = urlparse(url)
    youtube_domains = (
        'youtube.com',
        'www.youtube.com',
        'm.youtube.com',
        'youtu.be',
        'www.youtu.be',
    )
    return parsed.hostname in youtube_domains
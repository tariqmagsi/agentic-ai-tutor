import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-5.2"
    
    # Vector Store Configuration
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    COLLECTION_NAME: str = "rag_tutor_collection"
    AGENTIC_COLLECTION_NAME: str = "agentic_tutor_collection"

    CHROMA_CLOUD_HOST = os.getenv("CHROMA_CLOUD_HOST")
    CHROMA_CLOUD_PORT = int(os.getenv("CHROMA_CLOUD_PORT", "8000"))
    CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
    CHROMA_TENANT = os.getenv("CHROMA_TENANT")
    CHROMA_DB = os.getenv("CHROMA_DATABASE")
    
    # Agent Configuration
    MAX_RETRIEVAL_DOCS: int = 5
    TEMPERATURE: float = 0.1

    class Server:
        PORT = 8000
        SSE_PATH = "/sse"
        TRANSPORT = "sse"

@dataclass
class ChunkConfig:
    """Configuration for text chunking"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    separators: List[str] = field(default_factory=lambda: [
        "\n\n", "\n", ". ", "? ", "! ", ", ", " ", ""
    ])
    keep_separator: bool = True

config = Config()


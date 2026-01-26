import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI as OpenAI   
from enum import Enum

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
    
    # Agent Configuration
    MAX_RETRIEVAL_DOCS: int = 5
    TEMPERATURE: float = 0.1

    class Server:
        PORT = 8000
        SSE_PATH = "/sse"
        TRANSPORT = "sse"

class FileType(Enum):
    """Supported file types"""
    PDF = "pdf"
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    MD = "md"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"

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

@dataclass
class EmbeddingConfig:
    """Configuration for embeddings"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_kwargs: Dict = field(default_factory=lambda: {'device': 'cpu'})
    encode_kwargs: Dict = field(default_factory=lambda: {'normalize_embeddings': True})
    use_openai: bool = False
    openai_api_key: Optional[str] = Config.OPENAI_API_KEY
    openai_model: str = "text-embedding-3-small"

@dataclass
class VectorStoreConfig:
    """Configuration for vector store"""
    store_type: str = "chroma"
    persist_directory: str = "./vector_store"
    collection_name: str = "documents"
    similarity_metric: str = "cosine"
    
    # Qdrant specific
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None

@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""
    chunk_config: ChunkConfig = field(default_factory=ChunkConfig)
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_config: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    rerank_enabled: bool = True
    hybrid_search_enabled: bool = False
    hybrid_search_alpha: float = 0.7
    max_retrieval_results: int = 10

config = Config()


from typing import Optional
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.config.config import EmbeddingConfig
from src.utils.utils import get_logger

logger = get_logger(__name__)

class EmbeddingManager:
    """Manages embedding models"""
    
    def __init__(self):
        self.config = EmbeddingConfig()
        self.model = self._initialize_model()
    
    def _initialize_model(self):
        """Initialize embeddings model"""
        try:
            if self.config.use_openai:
                if not self.config.openai_api_key:
                    raise ValueError("OpenAI API key required for OpenAI embeddings")
                
                logger.info("Initializing OpenAI embeddings")
                return OpenAIEmbeddings(
                    model=self.config.openai_model,
                    openai_api_key=self.config.openai_api_key
                )
            else:
                logger.info(f"Initializing HuggingFace embeddings: {self.config.model_name}")
                return HuggingFaceEmbeddings(
                    model_name=self.config.model_name,
                    model_kwargs=self.config.model_kwargs,
                    encode_kwargs=self.config.encode_kwargs
                )
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            raise
    
    def get_embedding_function(self):
        """Get the embedding function"""
        return self.model
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        if self.config.use_openai:
            # OpenAI embedding dimensions
            if "ada" in self.config.openai_model:
                return 1536
            elif "small" in self.config.openai_model:
                return 1536
            elif "large" in self.config.openai_model:
                return 3072
            else:
                return 1536
        else:
            # Common HuggingFace model dimensions
            if "MiniLM" in self.config.model_name:
                return 384
            elif "mpnet" in self.config.model_name:
                return 768
            else:
                return 768
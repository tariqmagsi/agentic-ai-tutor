import hashlib
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from src.config.config import ChunkConfig
from src.utils.utils import get_logger, calculate_token_count, clean_text

logger = get_logger(__name__)

class DocumentProcessor:
    """Enhanced document processor with hybrid chunking strategies"""
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            keep_separator=self.config.keep_separator
        )
    
    def chunk_document(self, document: Document, metadata: Dict[str, Any] = None, 
                      strategy: str = "auto") -> List[Document]:
        """Split document into chunks using hybrid strategies"""
        try:
            # Clean the text
            cleaned_text = clean_text(document.page_content)
            
            # Create base metadata
            base_metadata = metadata or {}
            if hasattr(document, 'metadata'):
                base_metadata.update(document.metadata)
            
            # Use hybrid chunker
            chunks = self.text_splitter.split_text(cleaned_text)
            
            logger.debug(f"Created {len(chunks)} chunks using strategy: {strategy}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking document with hybrid strategy: {e}")
            
            # Fallback to original method
            try:
                return self._fallback_chunking(document, base_metadata)
            except Exception as fallback_error:
                logger.error(f"Fallback chunking also failed: {fallback_error}")
                return []
    
    def _fallback_chunking(self, document: Document, metadata: Dict[str, Any]) -> List[Document]:
        """Fallback to original chunking method"""
        cleaned_text = clean_text(document.page_content)
        texts = self.text_splitter.split_text(cleaned_text)
        
        chunks = []
        for i, text in enumerate(texts):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_id": self.generate_chunk_id(metadata.get("document_id", "unknown"), i),
                "total_chunks": len(texts),
                "token_count": calculate_token_count(text),
                "char_count": len(text),
                "chunking_strategy": "recursive_fallback"
            })
            chunks.append(Document(page_content=text, metadata=chunk_metadata))
        
        logger.debug(f"Created {len(chunks)} chunks using fallback method")
        return chunks
    
    def generate_chunk_id(self, doc_id, text):
        h = hashlib.sha256(f"{doc_id}:{text}".encode()).hexdigest()
        return h[:16]  # short hash
    
    def chunk_markdown_with_headers(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Specialized chunking for markdown with header preservation"""
        try:
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on,
                strip_headers=False
            )
            
            md_chunks = markdown_splitter.split_text(content)
            chunks = []
            
            for i, chunk in enumerate(md_chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update(chunk.metadata)
                chunk_metadata.update({
                    "chunk_id": self.generate_chunk_id(metadata.get("document_id", "unknown"), i),
                    "total_chunks": len(md_chunks),
                    "type": "markdown",
                    "chunking_strategy": "markdown_header"
                })
                chunks.append(Document(page_content=chunk.page_content, metadata=chunk_metadata))
            
            logger.debug(f"Created {len(chunks)} markdown chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking markdown: {e}")
            # Fallback to paragraph chunking
            return self.chunk_document(Document(page_content=content), metadata, strategy="paragraph")
    
    # def get_available_strategies(self) -> List[str]:
    #     """Get list of available chunking strategies"""
    #     return list(self.hybrid_chunker.strategies.keys())
    
    # def chunk_with_specific_strategy(self, document: Document, 
    #                                 strategy: str, 
    #                                 metadata: Dict[str, Any] = None) -> List[Document]:
    #     """Chunk document using a specific strategy"""
    #     if strategy not in self.hybrid_chunker.strategies:
    #         raise ValueError(f"Unknown strategy: {strategy}. Available: {self.get_available_strategies()}")
        
    #     return self.chunk_document(document, metadata, strategy=strategy)
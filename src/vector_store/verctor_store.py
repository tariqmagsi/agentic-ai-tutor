import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import hashlib
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages ChromaDB vector store operations"""
    
    def __init__(self, config):
        self.config = config
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            collection = self.client.get_collection(self.config.COLLECTION_NAME)
            logger.info(f"Loaded existing collection: {self.config.COLLECTION_NAME}")
            return collection
        except:
            collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.config.COLLECTION_NAME}")
            return collection
    
    def _generate_document_id(self, content: str, source: str) -> str:
        """Generate unique ID for document"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        source_hash = hashlib.md5(source.encode()).hexdigest()[:8]
        return f"{source_hash}_{content_hash}"
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to vector store"""
        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})
            metadata["source"] = source
            
            # Chunk the content
            chunks = self._chunk_text(content)
            
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_document_id(chunk, f"{source}_chunk_{i}")
                ids.append(doc_id)
                texts.append(chunk)
                metadatas.append({**metadata, "chunk_index": i})
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts).tolist()
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(ids)} document chunks to vector store")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results["documents"]:
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                formatted_results.append({
                    "content": doc,
                    "metadata": metadata,
                    "score": 1 - distance,  # Convert distance to similarity score
                    "rank": i + 1
                })
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.config.COLLECTION_NAME
            }
        except:
            return {"total_documents": 0, "collection_name": self.config.COLLECTION_NAME}
    
    def clear_collection(self):
        """Clear all documents from collection"""
        self.client.delete_collection(self.config.COLLECTION_NAME)
        self.collection = self._get_or_create_collection()
        logger.info("Collection cleared")
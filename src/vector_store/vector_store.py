from langchain_chroma import Chroma
from chromadb.config import Settings
from typing import List, Dict, Any
import hashlib
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.docstore.document import Document
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages ChromaDB vector store operations"""
    
    def __init__(self, config):
        self.config = config
        self.embedding_model = SentenceTransformerEmbeddings(
            model_name=config.EMBEDDING_MODEL
        )
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE if hasattr(config, 'CHUNK_SIZE') else 1000,
            chunk_overlap=config.CHUNK_OVERLAP if hasattr(config, 'CHUNK_OVERLAP') else 200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize Chroma vector store
        self.vector_store = self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize Chroma vector store"""
        try:
            # Create vector store with existing data
            vector_store = Chroma(
                collection_name=self.config.COLLECTION_NAME,
                embedding_function=self.embedding_model,
                persist_directory=self.config.CHROMA_PERSIST_DIRECTORY,
                client_settings=Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )
            
            # Check if collection exists and has documents
            collection_count = vector_store._collection.count()
            logger.info(f"Loaded existing collection '{self.config.COLLECTION_NAME}' with {collection_count} documents")
            
            return vector_store
            
        except Exception as e:
            logger.warning(f"Could not load existing collection: {e}. Creating new one.")
            
            # Create new vector store
            vector_store = Chroma.from_documents(
                documents=[],  # Empty list to create collection
                embedding=self.embedding_model,
                collection_name=self.config.COLLECTION_NAME,
                persist_directory=self.config.CHROMA_PERSIST_DIRECTORY,
                client_settings=Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )
            
            logger.info(f"Created new collection: {self.config.COLLECTION_NAME}")
            return vector_store
    
    def _generate_document_id(self, content: str, source: str, chunk_index: int) -> str:
        """Generate unique ID for document chunk"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        source_hash = hashlib.md5(source.encode()).hexdigest()[:12]
        return f"{source_hash}_{content_hash}_{chunk_index}"
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to vector store using LangChain's Chroma integration"""
        all_chunks = []
        all_metadatas = []
        all_ids = []
        
        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            metadata = doc.get("metadata", {})
            
            # Create LangChain Document
            langchain_doc = Document(
                page_content=content,
                metadata={**metadata, "source": source}
            )
            
            # Split document into chunks
            chunks = self.text_splitter.split_documents([langchain_doc])
            
            # Prepare chunks for addition
            for i, chunk in enumerate(chunks):
                chunk_id = self._generate_document_id(
                    chunk.page_content, 
                    source, 
                    i
                )
                
                # Update chunk metadata
                chunk.metadata.update({
                    "chunk_index": i,
                    "source": source,
                    "document_id": doc.get("id", f"doc_{hash(source)[:8]}")
                })
                
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
        
        if all_chunks:
            # Add documents to vector store
            self.vector_store.add_documents(
                documents=all_chunks,
                ids=all_ids
            )
            
            # Persist to disk
            self.vector_store.persist()
            
            logger.info(f"Added {len(all_chunks)} document chunks to vector store")
        else:
            logger.warning("No document chunks to add")
    
    def search(self, query: str, n_results: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Search for similar documents with enhanced filtering"""
        try:
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=n_results,
                **kwargs
            )
            
            # Format results
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                # Convert similarity score (higher is better) to distance-like metric
                # Chroma uses cosine distance (0=identical, 2=opposite)
                distance = 1 - score  # Assuming score is cosine similarity
                
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                    "distance": float(distance),
                    "rank": i + 1
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
    def search_with_filter(self, query: str, filter_dict: Dict[str, Any], n_results: int = 5):
        """Search with metadata filtering"""
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=n_results,
                filter=filter_dict
            )
            
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                    "rank": i + 1
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error during filtered search: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            if hasattr(self.vector_store, '_collection'):
                count = self.vector_store._collection.count()
                return {
                    "total_documents": count,
                    "collection_name": self.config.COLLECTION_NAME,
                    "embedding_model": self.config.EMBEDDING_MODEL
                }
            else:
                return {
                    "total_documents": 0,
                    "collection_name": self.config.COLLECTION_NAME,
                    "embedding_model": self.config.EMBEDDING_MODEL,
                    "note": "Collection not accessible"
                }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "total_documents": 0,
                "collection_name": self.config.COLLECTION_NAME,
                "error": str(e)
            }
    
    def clear_collection(self):
        """Clear all documents from collection"""
        try:
            # Delete and recreate collection
            self.vector_store.delete_collection()
            self.vector_store = self._initialize_vector_store()
            logger.info("Collection cleared and recreated")
            
            return {"success": True, "message": "Collection cleared"}
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return {"success": False, "error": str(e)}
    
    def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all documents from collection (with limit)"""
        try:
            # Use get method to retrieve documents
            results = self.vector_store.get(
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            documents = []
            if results.get("documents"):
                for doc, metadata in zip(results["documents"], results["metadatas"]):
                    documents.append({
                        "content": doc,
                        "metadata": metadata
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    def delete_documents(self, ids: List[str]):
        """Delete specific documents by IDs"""
        try:
            if ids:
                self.vector_store.delete(ids=ids)
                logger.info(f"Deleted {len(ids)} documents")
                return {"success": True, "deleted_count": len(ids)}
            return {"success": False, "message": "No IDs provided"}
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return {"success": False, "error": str(e)}
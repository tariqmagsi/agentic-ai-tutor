from fastmcp import FastMCP
import asyncio
from typing import List, Dict, Any, Optional
import logging
import json
import os
from contextlib import asynccontextmanager

from src.config.config import config
from src.vector_store.vector_store import VectorStoreManager
from src.data_ingestion.data_ingestion import DataIngestor
from src.agents.question_understanding_agent import QuestionUnderstandingAgent
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.tutoring_agent import TutoringAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
vector_store = VectorStoreManager(config)
data_ingestor = DataIngestor()
question_agent = QuestionUnderstandingAgent(config)
retrieval_agent = RetrievalAgent(vector_store, config)
tutoring_agent = TutoringAgent(config)

# Create FastMCP server
mcp = FastMCP("RAG Tutor")

@asynccontextmanager
async def lifespan():
    """Manage server lifecycle"""
    logger.info("Starting RAG Tutor server...")
    yield
    logger.info("Shutting down RAG Tutor server...")

# Tool: Ingest documents
@mcp.tool()
async def ingest_documents(directory_path: str) -> Dict[str, Any]:
    """
    Ingest documents from a directory (supports PDF, TXT, JSON)
    
    Args:
        directory_path: Path to directory containing documents
    
    Returns:
        Dictionary with ingestion results
    """
    try:
        if not os.path.exists(directory_path):
            return {"success": False, "error": f"Directory not found: {directory_path}"}
        
        documents = data_ingestor.ingest_directory(directory_path)
        
        if documents:
            vector_store.add_documents(documents)
            return {
                "success": True,
                "documents_ingested": len(documents),
                "message": f"Successfully ingested {len(documents)} documents"
            }
        else:
            return {"success": False, "error": "No documents found or could be read"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Tool: Ingest text directly
@mcp.tool()
async def ingest_text(text: str, source: str = "user_input") -> Dict[str, Any]:
    """
    Ingest plain text directly
    
    Args:
        text: The text content to ingest
        source: Source identifier for the text
    
    Returns:
        Dictionary with ingestion results
    """
    try:
        documents = data_ingestor.ingest_text(text, source)
        vector_store.add_documents(documents)
        
        return {
            "success": True,
            "documents_ingested": len(documents),
            "message": f"Successfully ingested text from {source}"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Tool: Ask question (main tutoring interface)
@mcp.tool()
async def ask_question(question: str) -> Dict[str, Any]:
    """
    Ask a question to the RAG Tutor
    
    Args:
        question: The question to ask
    
    Returns:
        Comprehensive answer with metadata and supporting documents
    """
    try:
        logger.info(f"Processing question: {question}")
        
        # Step 1: Analyze the question
        analysis = question_agent.analyze_question(question)
        
        # Step 2: Generate search queries
        queries = question_agent.generate_search_queries(question, analysis)
        
        # Step 3: Retrieve relevant documents
        documents = retrieval_agent.retrieve_relevant_docs(
            queries, 
            n_results=config.MAX_RETRIEVAL_DOCS
        )
        
        # Step 4: Rerank documents for relevance
        documents = retrieval_agent.rerank_documents(question, documents)
        
        # Step 5: Generate tutoring response
        response = tutoring_agent.generate_response(question, analysis, documents)
        
        # Add question analysis to response
        response["question_analysis"] = analysis
        
        return response
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        return {
            "answer": f"I apologize, but I encountered an error while processing your question.\nError: {str(e)}",
            "metadata": {"error": str(e)},
            "supporting_documents": []
        }

# Tool: Get vector store statistics
@mcp.tool()
async def get_store_stats() -> Dict[str, Any]:
    """
    Get statistics about the vector store
    
    Returns:
        Dictionary with vector store statistics
    """
    try:
        stats = vector_store.get_collection_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Tool: Clear vector store
@mcp.tool()
async def clear_store() -> Dict[str, Any]:
    """
    Clear all documents from the vector store
    
    Returns:
        Dictionary with operation result
    """
    try:
        vector_store.clear_collection()
        return {"success": True, "message": "Vector store cleared successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Tool: Get system status
@mcp.tool()
async def get_system_status() -> Dict[str, Any]:
    """
    Get current system status and configuration
    
    Returns:
        Dictionary with system status
    """
    return {
        "status": "operational",
        "components": {
            "vector_store": "connected",
            "question_agent": "ready",
            "retrieval_agent": "ready",
            "tutoring_agent": "ready"
        },
        "config": {
            "embedding_model": config.EMBEDDING_MODEL,
            "llm_model": config.OPENAI_MODEL,
            "max_retrieval_docs": config.MAX_RETRIEVAL_DOCS
        }
    }

mcp_server=mcp.run(transport=config.Server.TRANSPORT)
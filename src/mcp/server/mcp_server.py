from fastmcp import FastMCP
from typing import Dict, Any
import logging
import os

from src.config.config import config
from src.utils.openai_client import openai_client
from src.vector_store.vector_store import VectorStoreManager
from src.data_processor.data_ingestor import DocumentIngestor as DataIngestor
from src.graph.graph import TutorGraphBuilder
from src.graph.visualize_graph import visualize_langgraph_app
from youtube_transcript_api import YouTubeTranscriptApi
from src.data_processor.chunk_lecture_videos import hybrid_chunk_pipeline_documents as hybrid_chunk_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
vector_store = VectorStoreManager()
data_ingestor = DataIngestor()
agent = TutorGraphBuilder(config, vector_store, openai_client)

mcp = FastMCP("Agentic AI Tutor")
ytt_api = YouTubeTranscriptApi()

graph = TutorGraphBuilder()

visualize_langgraph_app(graph.app, out_png="agentic_tutor_graph.png")

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
        print(documents)
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

# Tool: Ask question (agentic tutor)
@mcp.tool()
async def ask_question(question: str) -> Dict[str, Any]:
    try:
        state = agent.run(question)
        print("Final state from agentic graph:", state)
        # If graph decided to clarify:
        if state.get("clarifying_question"):
            return {
                "answer": state["clarifying_question"],
                "metadata": {"mode": "clarify", "analysis": state.get("analysis", {})},
                "supporting_documents": [],
            }

        return {
            "answer": state.get("answer", ""),
            "metadata": {
                "analysis": state.get("analysis", {}),
                "queries": state.get("queries", []),
                "grounding": {
                    "grounded": state.get("grounded", False),
                    "score": state.get("grounding_score", 0.0),
                    "judge": state.get("judge", {}),
                },
                "attempt": state.get("attempt", 0),
                "stop_reason": state.get("stop_reason", ""),
            },
            "supporting_documents": state.get("documents", []),
        }

    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "metadata": {"error": str(e)},
            "supporting_documents": [],
        }

@mcp.tool()
async def clear_vector_store() -> Dict[str, Any]:
    """Clear all documents from the vector store"""
    try:
        vector_store.clear()
        return {"success": True, "message": "Vector store cleared successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@mcp.tool()
async def ingest_youtube_video(video_id: str) -> Dict[str, Any]:
    """Ingest YouTube video transcript into vector store"""
    try:
        transcript_list = ytt_api.fetch(video_id)
        # transcript_text = "\n".join([t["text"] for t in transcript_list])
        raw_transcript = transcript_list.to_raw_data()
        
        docs = hybrid_chunk_pipeline(raw_transcript, video_id)
        print(docs)
        vector_store.add_documents(docs)

        
        return {"success": True, "message": f"Transcript from {video_id} ingested successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

mcp_server=mcp.run(transport=config.Server.TRANSPORT)
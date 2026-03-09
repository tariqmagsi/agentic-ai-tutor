import os
import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.data_processor.youtube_transcript_chunk import run as run_hybrid_youtube_chunk
from src.data_processor.webpage_chunk import run as run_hybrid_webpage_chunk
from src.data_processor.agentic_youtube_transcript_chunking import run as run_youtube_chunk
from src.data_processor.agentic_webpage_chunking import run as run_webpage_chunk
from src.utils.utils import get_video_id, is_youtube_url, set_active_store_type

app = FastAPI()

videos = [
        "https://www.youtube.com/watch?v=KywRgZpLb5w", 
        "https://www.youtube.com/watch?v=WTau26feewU", 
        "https://www.youtube.com/watch?v=kQDStoasH-Q", 
        "https://www.youtube.com/watch?v=BFVLXYFlNXg", 
        "https://www.youtube.com/watch?v=udPiJpvPsMQ", 
        "https://www.youtube.com/watch?v=swax9LubOec",
        "https://www.youtube.com/watch?v=2G20nqeHAn8",
        "https://www.youtube.com/watch?v=283EGmUxRN0"
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_graph():
    from src.graph.graph import TutorGraphBuilder
    graph = TutorGraphBuilder().build()
    TutorGraphBuilder().print_graph(graph)
    return graph

graph = _build_graph()

class ChatRequest(BaseModel):
    question: str
    conversation_history: str = "[]"
    chunk_type: str = "agentic"

class InjestRequest(BaseModel):
    url: str
    chunk_type: str

@app.post("/ingest_url")
async def ingest_information(request: InjestRequest):
    if not os.getenv("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not set"}
    
    try:
        set_active_store_type(request.chunk_type)
        url = request.url
        chunk_docs = []
        if is_youtube_url(url):
            video_id = get_video_id(url)
            if request.chunk_type == "agentic":
                chunk_docs = run_youtube_chunk(video_id)
            elif request.chunk_type == "hybrid":
                chunk_docs = run_hybrid_youtube_chunk(video_id)
        else:   
            if request.chunk_type == "agentic":
                chunk_docs = run_webpage_chunk(url)
            elif request.chunk_type == "hybrid":
                chunk_docs = run_hybrid_webpage_chunk(url)
        
        return {
            "docs": chunk_docs,
            "success": True,

        }
    except Exception as e:
        return {"error": str(e), "success": False}


@app.post("/chat")
async def chat(request: ChatRequest):
    if not os.getenv("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not set"}
    
    try:
        history = json.loads(request.conversation_history)
        state = graph.invoke({
            "original_question": request.question,
            "conversation_history": history,
            "chunk_type": request.chunk_type,
        })
        
        answer = state.get("final_answer", "")
        needs_clarification = bool(state.get("needs_clarification", False))
        
        if not needs_clarification:
            history.append({"role": "student", "content": request.question})
            history.append({"role": "tutor", "content": answer})
        
        return {
            "answer": answer,
            "conversation_history": json.dumps(history),
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
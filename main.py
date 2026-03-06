import os
import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

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

@app.post("/chat")
async def chat(request: ChatRequest):
    if not os.getenv("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not set"}
    
    try:
        history = json.loads(request.conversation_history)
        state = graph.invoke({
            "original_question": request.question,
            "conversation_history": history,
        })
        
        answer = state.get("final_answer", "")
        needs_clarification = bool(state.get("needs_clarification", False))
        
        if not needs_clarification:
            history.append({"role": "student", "content": request.question})
            history.append({"role": "tutor", "content": answer})
        
        return {
            "answer": answer,
            "conversation_history": json.dumps(history)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI as OpenAI   

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

config = Config()


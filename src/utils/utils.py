import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_pipeline.log'),
        logging.StreamHandler()
    ]
)

def get_logger(name: str) -> logging.Logger:
    """Get logger with given name"""
    return logging.getLogger(name)

logger = get_logger(__name__)

def generate_document_id(file_path: str, content: str) -> str:
    """Generate unique document ID"""
    file_hash = hashlib.md5(f"{file_path}{content[:1000]}".encode()).hexdigest()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"doc_{timestamp}_{file_hash[:8]}"

def calculate_token_count(text: str, encoding_name: str = "cl100k_base") -> int:
    """Calculate token count for text"""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except:
        # Fallback estimation
        return len(text.split())

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    import re
    # Remove excessive whitespace
    text = ' '.join(text.split())
    # Remove special characters (keep alphanumeric, punctuation, and whitespace)
    text = re.sub(r'[^\w\s.,!?;:()-]', ' ', text)
    return text.strip()

def format_metadata(metadata: Dict[str, Any]) -> str:
    """Format metadata for display"""
    return "\n".join([f"{k}: {v}" for k, v in metadata.items()])
import os
from typing import List, Dict, Any
import logging
from langchain_community.document_loaders import PyPDFLoader
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataIngestor:
    """Handles ingestion of various data formats"""
    
    @staticmethod
    def read_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            reader = PyPDFLoader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return ""
    
    @staticmethod
    def read_txt(file_path: str) -> str:
        """Read text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""
    
    @staticmethod
    def read_json(file_path: str) -> List[Dict[str, Any]]:
        """Read JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
                else:
                    return [{"content": str(data)}]
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            return []
    
    def ingest_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Ingest all supported files from a directory"""
        documents = []
        
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            if filename.lower().endswith('.pdf'):
                content = self.read_pdf(file_path)
                if content:
                    documents.append({
                        "content": content,
                        "source": filename,
                        "metadata": {"type": "pdf", "filename": filename}
                    })
            
            elif filename.lower().endswith('.txt'):
                content = self.read_txt(file_path)
                if content:
                    documents.append({
                        "content": content,
                        "source": filename,
                        "metadata": {"type": "text", "filename": filename}
                    })
            
            elif filename.lower().endswith('.json'):
                json_docs = self.read_json(file_path)
                for i, doc in enumerate(json_docs):
                    documents.append({
                        "content": doc.get("content", str(doc)),
                        "source": f"{filename}_{i}",
                        "metadata": {"type": "json", "filename": filename, "index": i}
                    })
        
        logger.info(f"Ingested {len(documents)} documents from {directory_path}")
        return documents
    
    def ingest_text(self, text: str, source: str = "user_input") -> List[Dict[str, Any]]:
        """Ingest plain text"""
        return [{
            "content": text,
            "source": source,
            "metadata": {"type": "text", "source": source}
        }]
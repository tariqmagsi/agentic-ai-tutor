import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
    
)

from src.data_processor.processing import DocumentProcessor
from src.utils.utils import get_logger, generate_document_id
from datetime import datetime

logger = get_logger(__name__)

class DocumentIngestor:
    """Handles document ingestion from various formats"""
    
    # Map file extensions to loaders
    LOADER_MAP = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.csv': CSVLoader,
        '.md': UnstructuredMarkdownLoader,
        '.docx': UnstructuredWordDocumentLoader,
        '.doc': UnstructuredWordDocumentLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
        '.pptx': UnstructuredPowerPointLoader,
        '.ppt': UnstructuredPowerPointLoader,
    }
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.supported_extensions = list(self.LOADER_MAP.keys()) + ['.json']
    
    def load_document(self, file_path: str) -> List[Document]:
        """Load document using appropriate loader"""
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {suffix}")
        
        if suffix == '.json':
            return self._load_json(file_path)
        
        # Use LangChain loaders for other formats
        try:
            loader_class = self.LOADER_MAP[suffix]
            loader = loader_class(str(file_path))
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
            return documents
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def _load_json(self, file_path: Path) -> List[Document]:
        """Load JSON files with flexible structure handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        content = item.get('content', str(item))
                        metadata = item.get('metadata', {})
                    else:
                        content = str(item)
                        metadata = {}
                    
                    metadata.update({
                        "source": str(file_path),
                        "json_index": i,
                        "type": "json"
                    })
                    
                    documents.append(Document(
                        page_content=content,
                        metadata=metadata
                    ))
            elif isinstance(data, dict):
                # Try to extract meaningful content from dict
                content_parts = []
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        content_parts.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        # Flatten nested dicts
                        content_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                
                content = "\n".join(content_parts)
                documents.append(Document(
                    page_content=content,
                    metadata={"source": str(file_path), "type": "json"}
                ))
            
            logger.info(f"Loaded {len(documents)} documents from JSON {file_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading JSON {file_path}: {e}")
            return []
    
    def ingest_file(self, file_path: str, additional_metadata: Dict = None) -> List[Document]:
        """Ingest single file with processing"""
        try:
            logger.info(f"Ingesting file: {file_path}")
            
            # Load raw documents
            raw_docs = self.load_document(file_path)
            
            if not raw_docs:
                logger.warning(f"No content extracted from {file_path}")
                return []
            
            # Process each document
            all_chunks = []
            for i, doc in enumerate(raw_docs):
                # Prepare metadata
                metadata = {
                    "source": file_path,
                    "filename": Path(file_path).name,
                    "file_type": Path(file_path).suffix[1:],
                    "document_index": i,
                    "ingestion_time": datetime.now().isoformat(),
                    "document_id": generate_document_id(file_path, doc.page_content)
                }
                
                if additional_metadata:
                    metadata.update(additional_metadata)
                
                if hasattr(doc, 'metadata'):
                    metadata.update(doc.metadata)
                
                # Special handling for markdown
                if Path(file_path).suffix.lower() == '.md':
                    chunks = self.processor.chunk_markdown_with_headers(doc.page_content, metadata)
                else:
                    chunks = self.processor.chunk_document(doc, metadata)
                
                all_chunks.extend(chunks)
            
            logger.info(f"Created {len(all_chunks)} chunks from {len(raw_docs)} documents in {file_path}")
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            return []
    
    def ingest_directory(self, directory_path: str, 
                        recursive: bool = True,
                        file_patterns: List[str] = None) -> List[Document]:
        """Ingest all supported files from directory"""
        
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        all_chunks = []
        
        # Walk through directory
        if recursive:
            file_iter = directory_path.rglob("*")
        else:
            file_iter = directory_path.glob("*")
        
        for file_path in file_iter:
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                print("processing 1")
                # Check if file should be processed
                if file_patterns:
                    if suffix[1:] not in file_patterns and suffix not in file_patterns:
                        continue
                
                if suffix in self.supported_extensions:
                    chunks = self.ingest_file(str(file_path))
                    all_chunks.extend(chunks)
        
        logger.info(f"Ingested {len(all_chunks)} total chunks from {directory_path}")
        return all_chunks
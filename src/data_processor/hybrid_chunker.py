
import hashlib
import re
from typing import List, Dict, Any, Callable
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from src.config.config import ChunkConfig
from src.utils.utils import get_logger, calculate_token_count, clean_text

logger = get_logger(__name__)

class HybridChunker:
    def __init__(self, config: ChunkConfig):
        self.config = config
        self.strategies: Dict[str, Callable] = {
            'recursive': self._recursive_chunk,
            'semantic': self._semantic_chunk,
            'markdown': self._markdown_chunk,
            'paragraph': self._paragraph_chunk,
            'sentence': self._sentence_chunk,
            'sliding_window': self._sliding_window_chunk,
        }
    
    def auto_select_strategy(self, text: str) -> str:
        # Check for markdown
        if re.search(r'^#{1,6}\s', text, re.MULTILINE):
            return 'markdown'
        
        # Check for code blocks
        if '```' in text or text.count('\n    ') > 5:
            return 'recursive'
        
        # Check for structured paragraphs
        paragraph_count = len(re.split(r'\n\s*\n', text))
        if paragraph_count > 3:
            return 'paragraph'
        
        # Check for sentence-based content
        sentence_count = len(re.split(r'[.!?]+\s', text))
        if sentence_count > 10 and len(text) < 5000:
            return 'sentence'
        
        # Check for very long documents
        if len(text) > 10000:
            return 'sliding_window'
        
        # Default to semantic for general content
        return 'semantic'
    
    def chunk(self, text: str, strategy: str = 'auto') -> List[str]:
        if strategy == 'auto':
            strategy = self.auto_select_strategy(text)
        
        if strategy not in self.strategies:
            logger.warning(f"Unknown strategy '{strategy}', falling back to recursive")
            strategy = 'recursive'
        
        logger.debug(f"Using chunking strategy: {strategy}")
        return self.strategies[strategy](text)
    
    def _recursive_chunk(self, text: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            keep_separator=self.config.keep_separator
        )
        return splitter.split_text(text)
    
    def _semantic_chunk(self, text: str) -> List[str]:
        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If paragraph alone exceeds chunk size, split it
            if para_size > self.config.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph recursively
                chunks.extend(self._recursive_chunk(para))
            
            # If adding paragraph exceeds limit, save current chunk
            elif current_size + para_size > self.config.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            
            # Otherwise add to current chunk
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for \n\n
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _markdown_chunk(self, text: str) -> List[str]:
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        
        md_docs = markdown_splitter.split_text(text)
        chunks = []
        
        for doc in md_docs:
            chunk_text = doc.page_content
            
            # If chunk is too large, further split it
            if len(chunk_text) > self.config.chunk_size:
                sub_chunks = self._recursive_chunk(chunk_text)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk_text)
        
        return chunks if chunks else [text]
    
    def _paragraph_chunk(self, text: str) -> List[str]:
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if current_size + para_size > self.config.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _sentence_chunk(self, text: str) -> List[str]:
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.config.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _sliding_window_chunk(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.config.chunk_size
            
            # Find natural break point (space, newline)
            if end < text_len:
                # Look for space within last 10% of chunk
                search_start = end - int(self.config.chunk_size * 0.1)
                break_point = text.rfind(' ', search_start, end)
                
                if break_point > start:
                    end = break_point
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.config.chunk_overlap
            if start <= 0:
                break
        
        return chunks if chunks else [text]
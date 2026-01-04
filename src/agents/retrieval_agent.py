from typing import Dict, Any, List, Optional
import logging
from openai import OpenAI
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrievalAgent:
    """Handles retrieval of relevant information from vector store"""
    
    def __init__(self, vector_store_manager, config):
        self.vector_store = vector_store_manager
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def retrieve_relevant_docs(self, queries: List[str], n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve documents using multiple queries"""
        all_results = []
        
        for query in queries:
            results = self.vector_store.search(query, n_results=n_results)
            all_results.extend(results)
        
        # Remove duplicates based on content
        seen_contents = set()
        unique_results = []
        
        for result in all_results:
            content_hash = hash(result["content"][:100])  # Hash first 100 chars
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        # Sort by score
        unique_results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Retrieved {len(unique_results)} unique documents")
        return unique_results[:n_results]
    
    def rerank_documents(self, question: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank documents based on relevance to the specific question"""
        
        if not documents:
            return []
        
        system_prompt = """You are a document relevance evaluator. Given a question and a list of documents, 
        evaluate how relevant each document is to answering the question. Consider:
        1. Direct answer to the question
        2. Supporting evidence
        3. Contextual information
        4. Conceptual relevance
        
        Return a JSON array with relevance scores (0-1) for each document."""
        
        try:
            # Prepare document list for LLM
            doc_list = []
            for i, doc in enumerate(documents):
                doc_list.append(f"Document {i+1}:\n{doc['content'][:500]}...")  # First 500 chars
            
            context = f"Question: {question}\n\nDocuments:\n" + "\n---\n".join(doc_list)
            
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            scores_data = json.loads(response.choices[0].message.content)
            scores = scores_data.get("scores", [])
            
            # Update document scores
            for i, doc in enumerate(documents):
                if i < len(scores):
                    doc["relevance_score"] = scores[i]
                else:
                    doc["relevance_score"] = doc.get("score", 0)
            
            # Sort by relevance score
            documents.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            logger.info(f"Reranked {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error in document reranking: {e}")
            return documents
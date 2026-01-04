from typing import Dict, Any, List, Optional
import logging
from openai import OpenAI
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TutoringAgent:
    """Main tutoring agent that generates responses based on retrieved information"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def generate_response(self, question: str, analysis: Dict[str, Any], 
                         documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a tutoring response based on retrieved documents"""
        
        system_prompt = """You are an expert tutor. Your task is to:
        1. Answer the question clearly and accurately
        2. Explain concepts in an educational manner
        3. Use the provided reference documents to support your answer
        4. If information is insufficient, say so and explain what additional information would help
        5. Provide additional examples or analogies if helpful
        6. Suggest follow-up questions or topics for deeper learning
        
        Structure your response with:
        - Direct Answer
        - Detailed Explanation
        - Supporting Evidence (with citations to documents)
        - Examples/Analogies
        - Follow-up Suggestions
        
        Reference documents by their number in brackets, e.g., [Doc 1]."""
        
        # Prepare context from documents
        context_parts = []
        for i, doc in enumerate(documents[:5]):  # Use top 5 documents
            context_parts.append(f"[Document {i+1} - Relevance: {doc.get('relevance_score', doc.get('score', 0)):.2f}]\n{doc['content'][:800]}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        user_content = f"""Question: {question}

Question Analysis:
{json.dumps(analysis, indent=2)}

Relevant Documents:
{context}

Please provide a comprehensive tutoring response:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=self.config.TEMPERATURE,
                max_tokens=1500
            )
            
            answer = response.choices[0].message.content
            
            # Generate metadata about the response
            metadata = {
                "documents_used": len(documents),
                "question_type": analysis.get("question_type", "unknown"),
                "complexity": analysis.get("complexity", "basic"),
                "response_length": len(answer)
            }
            
            logger.info(f"Generated tutoring response ({metadata['response_length']} chars)")
            
            return {
                "answer": answer,
                "metadata": metadata,
                "supporting_documents": documents[:3]  # Top 3 most relevant
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": f"I apologize, but I encountered an error while generating the response. Please try again.\nError: {str(e)}",
                "metadata": {"error": str(e)},
                "supporting_documents": []
            }
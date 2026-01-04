from typing import Dict, Any, List, Optional
import logging
from openai import OpenAI
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionUnderstandingAgent:
    """Analyzes and understands the user's question"""
    
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze the question to extract key components"""
        
        system_prompt = """You are a question analysis expert. Analyze the given question and extract:
        1. Main topic/subject
        2. Key concepts mentioned
        3. Question type (factual, conceptual, analytical, comparative, etc.)
        4. Complexity level (basic, intermediate, advanced)
        5. Any implicit assumptions or context needed
        6. Potential related concepts that might be relevant
        
        Return your analysis in JSON format."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Question: {question}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            logger.info(f"Question analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in question analysis: {e}")
            return {
                "topic": "unknown",
                "key_concepts": [],
                "question_type": "factual",
                "complexity": "basic",
                "assumptions": [],
                "related_concepts": []
            }
    
    def generate_search_queries(self, question: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate multiple search queries based on question analysis"""
        
        system_prompt = """You are a search query expert. Based on the question and analysis, generate 
        multiple search queries that would help find relevant information. Consider:
        1. Direct query matching the question
        2. Broader concept queries
        3. Specific aspect queries
        4. Related concept queries
        
        Return a JSON array of search strings."""
        
        try:
            context = f"Question: {question}\nAnalysis: {json.dumps(analysis, indent=2)}"
            
            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            queries = result.get("queries", [question])
            
            # Ensure we have at least the original question
            if question not in queries:
                queries.insert(0, question)
            
            logger.info(f"Generated {len(queries)} search queries")
            return queries[:5]  # Limit to 5 queries
            
        except Exception as e:
            logger.error(f"Error generating search queries: {e}")
            return [question]
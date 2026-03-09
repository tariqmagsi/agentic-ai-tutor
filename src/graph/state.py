from typing import List, Literal, TypedDict
from langchain_core.documents import Document

CompetenceLevel = Literal["novice", "intermediate", "advanced"]


class TutorState(TypedDict, total=False):
    # Input
    original_question: str
    chunk_type: str

    # QuestionUnderstandingAgent
    intent: str          
    response_style: str   
    question_analysis: str
    complexity: str 

    # PersonalizationAgent
    competence_level: CompetenceLevel

    # RouterAgent
    route: str
    needs_clarification: bool
    clarification_question: str

    # MultiQueryAgent
    search_queries: List[str]

    # RetrievalAgent
    retrieved_docs: List[Document]

    # Conversation memory
    conversation_history: List[dict]

    # Output
    final_answer: str

    # EvaluationAgent
    evaluation: dict
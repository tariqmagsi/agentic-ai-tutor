from typing import List, Literal, TypedDict
from langchain_core.documents import Document

CompetenceLevel = Literal["novice", "intermediate", "advanced"]


class TutorState(TypedDict, total=False):
    # Input
    original_question: str

    # QuestionUnderstandingAgent
    intent: str           # concept | example | procedure | comparison | rule | summary
    response_style: str   # redirect | step_by_step | debug_guide | conceptual | design_guidance | resource_list | clarify_req
    question_analysis: str
    has_code: bool
    language: str
    complexity: str       # simple | complex
    domain: str

    # PersonalizationAgent
    competence_level: CompetenceLevel

    # RouterAgent
    route: str
    needs_clarification: bool
    clarification_question: str

    # RetrievalAgent
    retrieved_docs: List[Document]

    # Conversation memory
    conversation_history: List[dict]

    # Output
    final_answer: str
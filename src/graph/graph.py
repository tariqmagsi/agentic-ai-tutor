from langgraph.graph import StateGraph, END
from src.graph.state import TutorState
from src.agents.question_understanding import QuestionUnderstandingAgent
from src.agents.personalization import PersonalizationAgent
from src.agents.router import RouterAgent
from src.agents.clarification import ClarificationAgent
from src.agents.retrieval import RetrievalAgent, RetrievalNode
from src.agents.tutor import TutorAgent
from src.agents.evaluation import EvaluationAgent


def _route_after_router(state: TutorState, config=None) -> str:
    route = state.get("route", "tutor")
    print(f"[Graph] routing → {route}")
    return route


class TutorGraphBuilder:
    def __init__(self):
        self.question_understanding_agent = QuestionUnderstandingAgent()
        self.personalization_agent = PersonalizationAgent()
        self.router_agent = RouterAgent()
        self.clarification_agent = ClarificationAgent()
        self.retrieval_node = RetrievalNode(retrieval_agent=RetrievalAgent(), rerank=True)
        self.tutor_agent = TutorAgent()
        self.evaluation = EvaluationAgent()

    def build(self) -> StateGraph:
        graph = StateGraph(TutorState)

        graph.add_node("question_understanding", self.question_understanding_agent)
        graph.add_node("personalization", self.personalization_agent)
        graph.add_node("router", self.router_agent)
        graph.add_node("clarification", self.clarification_agent)
        graph.add_node("retrieval", self.retrieval_node)
        graph.add_node("tutor", self.tutor_agent)
        graph.add_node("evaluation", self.evaluation)

        graph.set_entry_point("question_understanding")
        graph.add_edge("question_understanding", "router")
        graph.add_conditional_edges(
            "router",
            _route_after_router,
            {
                "clarify": "clarification",
                "tutor": "personalization",
            },
        )
        graph.add_edge("personalization", "retrieval")
        graph.add_edge("retrieval", "tutor")


        graph.add_edge("tutor", "evaluation")
        graph.add_edge("clarification", "evaluation")
        graph.add_edge("evaluation", END)
        
        return graph.compile()

    @staticmethod
    def print_graph(graph, mermaid_path: str = "tutor_graph.mmd") -> None:
        mermaid = graph.get_graph().draw_mermaid()
        print("\n=== MERMAID GRAPH ===\n")
        print(mermaid)
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(mermaid)
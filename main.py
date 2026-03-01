import os
from dotenv import load_dotenv

from src.graph.graph import TutorGraphBuilder
from src.graph.visualize_graph import visualize_langgraph_app
from src.agents.tutor import TutorAgent
from src.agents.question_understanding import QuestionUnderstandingAgent
from src.agents.personalization import PersonalizationAgent

load_dotenv()


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in environment.")

    # Build and visualize graph
    tutor_graph = TutorGraphBuilder()
    graph = tutor_graph.build()
    tutor_graph.print_graph(graph)
    visualize_langgraph_app(graph, out_png="agentic_tutor_graph.png")

    print("\n" + "=" * 50)
    print("  Welcome to the AI Tutor!")
    print("  Type 'exit' to quit.")
    print("=" * 50 + "\n")

    question = input("You> ").strip()
    if not question or question.lower() == "exit":
        return

    conversation_history = []

    # Agents used directly in the conversation loop (no graph re-run)
    understanding_agent = QuestionUnderstandingAgent()
    personalization_agent = PersonalizationAgent()
    tutor_agent = TutorAgent()

    # ── First message: full graph run ─────────────────────────────────────
    # understand → personalize → router → (clarify | retrieve → tutor)
    state = graph.invoke({
        "original_question": question,
        "conversation_history": conversation_history,
    })

    # ── Clarification loop ────────────────────────────────────────────────
    while state.get("needs_clarification", False):
        print(f"\n[Tutor] {state.get('final_answer', '')}\n")
        student_input = input("You> ").strip()
        if student_input.lower() == "exit":
            return
        # Append clarification to original question and retry
        question = question + "\n\n[Student clarification]\n" + student_input
        state = graph.invoke({
            "original_question": question,
            "conversation_history": conversation_history,
        })

    # ── Show first tutor response ─────────────────────────────────────────
    tutor_answer = state.get("final_answer", "")
    print(f"\n[Tutor] {tutor_answer}\n")

    conversation_history.append({"role": "student", "content": question})
    conversation_history.append({"role": "tutor", "content": tutor_answer})

    # Retrieved docs reused for entire session — no re-retrieval needed
    retrieved_docs = state.get("retrieved_docs", [])

    # ── Conversation loop ─────────────────────────────────────────────────
    # Per turn:
    #   1. QuestionUnderstandingAgent → intent + response_style + analysis
    #   2. PersonalizationAgent       → competence_level from writing style
    #   3. TutorAgent                 → response using all context
    while True:
        student_input = input("You> ").strip()
        if not student_input:
            continue
        if student_input.lower() == "exit":
            print("\nGoodbye! Keep up the great work.\n")
            break

        # 1. Understand the message
        understanding = understanding_agent({
            "original_question": student_input,
            "conversation_history": conversation_history,
        })

        # 2. Assess competence from writing style + history
        personalization = personalization_agent({
            "original_question": student_input,
            "conversation_history": conversation_history,
        })

        # 3. Generate response
        result = tutor_agent({
            "original_question": student_input,
            "intent": understanding.get("intent", "concept"),
            "response_style": understanding.get("response_style", "conceptual"),
            "question_analysis": understanding.get("question_analysis", ""),
            "has_code": understanding.get("has_code", False),
            "complexity": understanding.get("complexity", "simple"),
            "domain": understanding.get("domain", "general"),
            "competence_level": personalization.get("competence_level", "novice"),
            "retrieved_docs": retrieved_docs,
            "conversation_history": conversation_history,
        })

        tutor_answer = result.get("final_answer", "")
        print(f"\n[Tutor] {tutor_answer}\n")

        conversation_history.append({"role": "student", "content": student_input})
        conversation_history.append({"role": "tutor", "content": tutor_answer})


if __name__ == "__main__":
    main()
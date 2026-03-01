from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.clarification import CLARIFICATION_SYSTEM


class ClarificationAgent:
    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        original_q = (state.get("original_question") or "").strip()
        clar_hint = (state.get("clarification_question") or "").strip()

        resp = self.llm.invoke([
            SystemMessage(content=CLARIFICATION_SYSTEM),
            HumanMessage(content=(
                f"Student's message: {original_q}\n"
                f"What's missing: {clar_hint}"
            )),
        ])

        data = safe_json_loads(resp.content) or {}

        summary = (data.get("summary") or "I want to help you!").strip()
        question = (data.get("clarification_question") or clar_hint or "Could you share more details?").strip()

        final_answer = f"{summary} {question}"
        print(f"[ClarificationAgent] {final_answer}")

        return {
            "needs_clarification": True,
            "clarification_question": question,
            "final_answer": final_answer,
        }
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.router import ROUTER_SYSTEM


class RouterAgent:
    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or "").strip()
        question_analysis = state.get("question_analysis", "")
        history = state.get("conversation_history", [])
        has_history = len(history) > 0

        resp = self.llm.invoke([
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=(
                f"Student message: {q}\n"
                f"Analysis: {question_analysis}\n"
                f"Has conversation history: {has_history}"
            )),
        ])

        data = safe_json_loads(resp.content) or {}
        needs_clarification = bool(data.get("needs_clarification", False))
        clarification_question = (data.get("clarification_question") or "").strip()
        reason = (data.get("reason") or "").strip()

        route = "clarify" if needs_clarification else "tutor"
        print(f"[RouterAgent] route={route}, reason={reason}")

        return {
            "route": route,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
        }
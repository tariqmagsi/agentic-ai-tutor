from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.question_understanding import QUESTION_UNDERSTANDING_SYSTEM

_ALLOWED_INTENTS = {"concept", "example", "procedure", "comparison", "rule", "summary"}
_ALLOWED_STYLES = {
    "redirect", "step_by_step", "debug_guide", "conceptual",
    "design_guidance", "resource_list", "clarify_req",
}


class QuestionUnderstandingAgent:
    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or state.get("user_input") or "").strip()
        history = state.get("conversation_history", [])

        if not q:
            return {
                "intent": "concept",
                "response_style": "conceptual",
                "question_analysis": "No question provided.",
                "has_code": False,
                "language": "en",
                "complexity": "simple",
                "domain": "general",
            }

        # Include recent history so the agent understands follow-ups correctly
        history_snippet = ""
        if history:
            history_snippet = "\n".join(
                f"{t.get('role', '').capitalize()}: {(t.get('content') or '')[:200]}"
                for t in history[-4:]
            )

        user_content = f"Student message: {q}"
        if history_snippet:
            user_content += f"\n\nRecent conversation:\n{history_snippet}"

        resp = self.llm.invoke([
            SystemMessage(content=QUESTION_UNDERSTANDING_SYSTEM),
            HumanMessage(content=user_content),
        ])

        data = safe_json_loads(getattr(resp, "content", "") or "") or {}

        intent = data.get("intent")
        if intent not in _ALLOWED_INTENTS:
            intent = "concept"

        response_style = data.get("response_style")
        if response_style not in _ALLOWED_STYLES:
            response_style = "conceptual"

        question_analysis = (data.get("question_analysis") or "General programming question.").strip()

        has_code = data.get("has_code")
        if not isinstance(has_code, bool):
            has_code = "```" in q or any(
                kw in q for kw in ["class ", "def ", "public ", "void ", "return "]
            )

        language = data.get("language") or "en"
        complexity = (
            data.get("complexity")
            if data.get("complexity") in ("simple", "complex")
            else ("complex" if len(q.split()) > 25 else "simple")
        )
        domain = (data.get("domain") or "general").strip()

        print(f"[QuestionUnderstanding] intent={intent}, style={response_style}, "
              f"complexity={complexity}, has_code={has_code}, domain={domain}")
        print(f"[QuestionUnderstanding] analysis: {question_analysis}")

        return {
            "intent": intent,
            "response_style": response_style,
            "question_analysis": question_analysis,
            "has_code": has_code,
            "language": language,
            "complexity": complexity,
            "domain": domain,
        }
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.evaluation import EVALUATION_SYSTEM


class EvaluationAgent:
    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or "").strip()
        final_answer = state.get("final_answer", "")
        steps = state.get("steps", [])
        current_step = state.get("current_step", 0)
        history = state.get("conversation_history", [])

        history_str = ""
        if history:
            history_str = "\n".join(
                f"{t.get('role', '').capitalize()}: {(t.get('content') or '')[:300]}"
                for t in history[-8:]
            )

        steps_str = ""
        if steps:
            steps_str = "\n".join(
                f"{s.get('step_number', i+1)}. {s.get('title', '')}: {s.get('what_to_do', '')}"
                for i, s in enumerate(steps)
            )

        user_content = f"Student's question: {q}\n\n"
        if steps_str:
            user_content += f"Steps plan:\n{steps_str}\nCurrently on step: {current_step + 1}\n\n"
        if history_str:
            user_content += f"Conversation:\n{history_str}\n\n"
        user_content += f"Tutor's response:\n{final_answer}"

        resp = self.llm.invoke([
            SystemMessage(content=EVALUATION_SYSTEM),
            HumanMessage(content=user_content),
        ])

        data = safe_json_loads(resp.content) or {}

        understanding = data.get("understanding_level", "unclear")
        if understanding not in ("strong", "moderate", "weak", "unclear"):
            understanding = "unclear"

        print(f"[EvaluationAgent] accuracy={data.get('accuracy_score', 0)}, understanding={understanding}")

        return {"evaluation": data}
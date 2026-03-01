from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.personalization import COMPETENCE_SYSTEM


class PersonalizationAgent:
    """
    Assesses student competence level live from their writing style.
    No file storage — assessed fresh every turn from the message + history.
    """

    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or "").strip()
        history = state.get("conversation_history", [])

        # Include last 6 turns for a stable assessment
        history_snippet = ""
        if history:
            history_snippet = "\n".join(
                f"{t.get('role', '').capitalize()}: {(t.get('content') or '')[:300]}"
                for t in history[-6:]
            )

        user_content = f"Student's current message: {q}"
        if history_snippet:
            user_content += f"\n\nConversation so far:\n{history_snippet}"

        resp = self.llm.invoke([
            SystemMessage(content=COMPETENCE_SYSTEM),
            HumanMessage(content=user_content),
        ])

        data = safe_json_loads(resp.content) or {}

        competence_level = data.get("competence_level")
        if competence_level not in ("novice", "intermediate", "advanced"):
            competence_level = "novice"

        reasoning = (data.get("reasoning") or "").strip()
        print(f"[PersonalizationAgent] competence={competence_level} | {reasoning}")

        return {"competence_level": competence_level}
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.openai_client import openai_client
from src.utils.utils import safe_json_loads
from src.prompts.multi_queries import MULTI_QUERY_SYSTEM


class MultiQueryAgent:
    def __init__(self, max_queries: int = 5):
        self.llm = openai_client
        self.max_queries = max_queries

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or "").strip()
        intent = state.get("intent", "concept")
        domain = state.get("domain", "general")
        question_analysis = state.get("question_analysis", "")
        history = state.get("conversation_history", [])

        if not q:
            return {"search_queries": [q] if q else []}

        # Build history snippet so the LLM can resolve references
        history_snippet = ""
        if history:
            history_snippet = "\n".join(
                f"{t.get('role', '').capitalize()}: {(t.get('content') or '')[:200]}"
                for t in history[-4:]
            )

        user_content = (
            f"Student message: {q}\n"
            f"Analysis: {question_analysis}\n"
            f"Intent: {intent}\n"
            f"Domain: {domain}"
        )
        if history_snippet:
            user_content += f"\n\nRecent conversation:\n{history_snippet}"

        resp = self.llm.invoke([
            SystemMessage(content=MULTI_QUERY_SYSTEM),
            HumanMessage(content=user_content),
        ])

        data = safe_json_loads(resp.content) or {}

        queries = data.get("queries", [])
        reasoning = (data.get("reasoning") or "").strip()

        # Validate and cap
        if not isinstance(queries, list) or not queries:
            queries = [q]  # fallback to original question
        else:
            # Ensure all entries are non-empty strings
            queries = [str(qr).strip() for qr in queries if str(qr).strip()]
            if not queries:
                queries = [q]

        queries = queries[: self.max_queries]

        # Always include the original question for baseline recall
        if q not in queries:
            queries.insert(0, q)
            queries = queries[: self.max_queries]

        print(f"[MultiQueryAgent] Generated {len(queries)} queries | {reasoning}")
        for i, qr in enumerate(queries):
            print(f"  Q{i+1}: {qr}")

        return {"search_queries": queries}
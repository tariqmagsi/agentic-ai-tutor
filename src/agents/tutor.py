from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.openai_client import openai_client
from src.prompts.tutor import TUTOR_SYSTEM


class TutorAgent:
    def __init__(self):
        self.llm = openai_client

    def __call__(self, state: dict) -> dict:
        q = (state.get("original_question") or "").strip()
        docs = state.get("retrieved_docs", [])
        intent = state.get("intent", "concept")
        response_style = state.get("response_style", "conceptual")
        question_analysis = state.get("question_analysis", "")
        competence_level = state.get("competence_level", "novice")
        complexity = state.get("complexity", "simple")
        history = state.get("conversation_history", [])

        print(f"[TutorAgent] intent={intent}, style={response_style}, "
              f"competence={competence_level}, complexity={complexity}, "
              f"docs={len(docs)}, history={len(history)} turns")

        # Build course material context
        if docs:
            parts = []
            for i, d in enumerate(docs):
                meta = getattr(d, "metadata", {}) or {}
                # Build a rich header from whichever metadata fields exist
                title = meta.get("page_title") or meta.get("video_title") or ""
                header_items = [f"[Material {i+1}]"]
                if title:
                    header_items.append(f"Title: {title}")
                if meta.get("source"):
                    header_items.append(f"Source: {meta['source']}")
                if meta.get("url"):
                    header_items.append(f"URL: {meta['url']}")
                if meta.get("author"):
                    header_items.append(f"Author: {meta['author']}")
                if meta.get("content_type"):
                    header_items.append(f"Type: {meta['content_type']}")
                if meta.get("section_heading"):
                    header_items.append(f"Section: {meta['section_heading']}")
                if meta.get("chapter"):
                    header_items.append(f"Chapter: {meta['chapter']}")
                if meta.get("page"):
                    header_items.append(f"Page: {meta['page']}")
                if meta.get("code_description"):
                    header_items.append(f"Code: {meta['code_description']}")
                header = " | ".join(header_items)
                parts.append(f"{header}\n{d.page_content}")
            context = "\n\n".join(parts)
        else:
            context = "No relevant course material found. Use general programming knowledge."

        # Build conversation history string
        history_str = ""
        if history:
            history_str = "\n".join(
                f"{t.get('role', '').capitalize()}: {(t.get('content') or '').strip()}"
                for t in history
                if t.get("role") and t.get("content")
            )

        user_message = (
            f"== What the student needs ==\n{question_analysis}\n\n"
            f"== Response style ==\n{response_style}\n\n"
            f"== Student competence ==\n{competence_level}\n\n"
            f"== Student message ==\n{q}\n\n"
            f"Intent: {intent} | Complexity: {complexity}\n"
        )

        if history_str:
            user_message += f"\n== Conversation history ==\n{history_str}\n"

        user_message += f"\n== Course material ==\n{context}"

        resp = self.llm.invoke([
            SystemMessage(content=TUTOR_SYSTEM),
            HumanMessage(content=user_message),
        ])

        print("[TutorAgent] response generated.")
        return {"final_answer": resp.content}
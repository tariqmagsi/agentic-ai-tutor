from dataclasses import dataclass
from typing import Any, Dict, List
import json

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document

from src.utils.openai_client import openai_client
from src.vector_store.vector_store import VectorStoreManager


class RetrievalAgent:
    """
    Retrieves docs from vector store and reranks with LLM.

    Key fix: uses plain similarity_search() instead of
    similarity_search_with_relevance_scores(). The latter returns
    negative cosine scores for MiniLM embeddings, which caused
    score >= 0.2 filtering to eliminate everything. We fetch top-k
    unconditionally and let the LLM reranker decide relevance.
    """

    def __init__(self):
        self.vector_store = VectorStoreManager().vector_store
        self.client = openai_client

    def retrieve(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        try:
            docs = self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            print(f"[RetrievalAgent] Vector store error: {e}")
            return []

        print(f"[RetrievalAgent] Retrieved {len(docs)} raw docs.")
        if docs:
            print(f"[RetrievalAgent] Sample: {docs[0].page_content[:150]}")

        return [
            {
                "content": (getattr(d, "page_content", "") or "").strip(),
                "metadata": (getattr(d, "metadata", {}) or {}),
            }
            for d in docs
            if (getattr(d, "page_content", "") or "").strip()
        ]

    def rerank(self, question: str, docs: List[Dict[str, Any]], threshold: float = 0.35) -> List[Dict[str, Any]]:
        """LLM scores each doc 0-1. Keeps docs above threshold, sorted by score."""
        if not docs:
            return []

        system = (
            "Score each document's relevance to the student's question from 0.0 to 1.0.\n"
            "1.0 = directly teaches the concept being asked about.\n"
            "0.0 = completely unrelated.\n"
            "Return ONLY a JSON array of floats, one per document, in order.\n"
            "Example for 3 docs: [0.9, 0.1, 0.0]\n"
            "No explanation. No markdown. JSON array only."
        )

        parts = [f"Doc {i+1}:\n{d.get('content', '')[:400]}" for i, d in enumerate(docs)]
        user = f"Question: {question}\n\n" + "\n---\n".join(parts)

        try:
            resp = self.client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            raw = resp.content.strip().replace("```json", "").replace("```", "").strip()
            scores = json.loads(raw)

            if not isinstance(scores, list):
                return docs

            for i, d in enumerate(docs):
                try:
                    d["relevance_score"] = float(scores[i])
                except (IndexError, ValueError, TypeError):
                    d["relevance_score"] = 0.0

            relevant = [d for d in docs if d.get("relevance_score", 0.0) >= threshold]
            relevant.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

            print(f"[RetrievalAgent] Reranked: {len(relevant)}/{len(docs)} docs above threshold={threshold}")
            return relevant if relevant else []

        except Exception as e:
            print(f"[RetrievalAgent] Rerank error: {e} — returning all docs unfiltered.")
            return docs


@dataclass
class RetrievalNode:
    retrieval_agent: RetrievalAgent
    k: int = 8
    rerank: bool = True

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        question = (state.get("original_question") or "").strip()

        results = self.retrieval_agent.retrieve(question, k=self.k)

        if self.rerank and results:
            results = self.retrieval_agent.rerank(question, results)

        lc_docs: List[Document] = []
        for r in results:
            content = (r.get("content") or "").strip()
            if not content:
                continue
            meta = dict(r.get("metadata", {}) or {})
            if "relevance_score" in r:
                meta["relevance_score"] = r["relevance_score"]
            lc_docs.append(Document(page_content=content, metadata=meta))

        print(f"[RetrievalNode] Passing {len(lc_docs)} docs to TutorAgent.")
        return {"retrieved_docs": lc_docs}
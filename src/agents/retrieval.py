from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document

from src.utils.openai_client import openai_client
from src.vector_store.vector_store import VectorStoreManager

_INTENT_TO_CONTENT_TYPE = {
    "concept": "concept", "procedure": "procedure", "example": "example",
    "comparison": "comparison", "rule": "rule", "summary": "summary",
}


class RetrievalAgent:
    def __init__(self, type: str = "agentic"):
        self._type = type
        self.vector_store = VectorStoreManager(type=type).vector_store
        self.client = openai_client

    def retrieve(self, query: str, k: int = 8, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            kwargs = {"k": k}
            if metadata_filter:
                kwargs["filter"] = metadata_filter
            docs = self.vector_store.similarity_search(query, **kwargs)
        except Exception as e:
            print(f"[RetrievalAgent] Vector store error: {e}")
            return []

        filter_msg = f" (filter={metadata_filter})" if metadata_filter else ""
        print(f"[RetrievalAgent] Retrieved {len(docs)} raw docs.{filter_msg}")

        return [
            {
                "content": (getattr(d, "page_content", "") or "").strip(),
                "metadata": (getattr(d, "metadata", {}) or {}),
            }
            for d in docs
            if (getattr(d, "page_content", "") or "").strip()
        ]

    def retrieve_mmr(self, query: str, k: int = 8, fetch_k: int = 20,
                     lambda_mult: float = 0.5,
                     metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Maximal Marginal Relevance — balances relevance with diversity."""
        try:
            kwargs = {"k": k, "fetch_k": fetch_k, "lambda_mult": lambda_mult}
            if metadata_filter:
                kwargs["filter"] = metadata_filter
            docs = self.vector_store.max_marginal_relevance_search(query, **kwargs)
        except Exception as e:
            print(f"[RetrievalAgent] MMR error: {e}")
            return []
 
        print(f"[RetrievalAgent] MMR retrieved {len(docs)} docs (lambda={lambda_mult}).")
 
        return [
            {
                "content": (getattr(d, "page_content", "") or "").strip(),
                "metadata": (getattr(d, "metadata", {}) or {}),
            }
            for d in docs
            if (getattr(d, "page_content", "") or "").strip()
        ]

    def retrieve_multi(self, queries: List[str], k_per_query: int = 5,
                       metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run retrieval per query, deduplicate, fuse with Reciprocal Rank Fusion."""
        if not queries:
            return []

        seen_content: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60

        for qi, query in enumerate(queries):
            docs = self.retrieve(query, k=k_per_query, metadata_filter=metadata_filter)
            for rank, doc in enumerate(docs):
                content = doc.get("content", "").strip()
                if not content:
                    continue
                content_key = content[:200]
                rrf_score = 1.0 / (rrf_k + rank + 1)
                if content_key in seen_content:
                    seen_content[content_key]["rrf_score"] += rrf_score
                else:
                    doc_copy = dict(doc)
                    doc_copy["rrf_score"] = rrf_score
                    seen_content[content_key] = doc_copy

        fused = sorted(seen_content.values(), key=lambda x: x["rrf_score"], reverse=True)
        print(f"[RetrievalAgent] Multi-query fusion: {len(fused)} unique docs from {len(queries)} queries")
        return fused

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
    k_per_query: int = 5
    rerank: bool = True
    use_metadata_filter: bool = True
    min_filtered_results: int = 2

    def _build_metadata_filter(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.use_metadata_filter:
            return None
        response_style = state.get("response_style", "")
        if response_style == "resource_list":
            return {"content_type": "summary"}
        content_type = _INTENT_TO_CONTENT_TYPE.get(state.get("intent", ""))
        return {"content_type": content_type} if content_type else None

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        question = (state.get("original_question") or "").strip()
        search_queries = state.get("search_queries", [])
        metadata_filter = self._build_metadata_filter(state)

        # Step 1: Retrieve (multi-query if available, else single)
        if search_queries and len(search_queries) > 1:
            results = self.retrieval_agent.retrieve_multi(
                search_queries, k_per_query=self.k_per_query, metadata_filter=metadata_filter)
        else:
            results = self.retrieval_agent.retrieve(question, k=self.k, metadata_filter=metadata_filter)

        # Step 2: Fallback if hard filter returned too few results
        if metadata_filter and len(results) < self.min_filtered_results:
            print(f"[RetrievalNode] Only {len(results)} results with {metadata_filter}, falling back to unfiltered.")
            if search_queries and len(search_queries) > 1:
                results = self.retrieval_agent.retrieve_multi(
                    search_queries, k_per_query=self.k_per_query, metadata_filter=None)
            else:
                results = self.retrieval_agent.retrieve(question, k=self.k, metadata_filter=None)

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
            if "rrf_score" in r:
                meta["rrf_score"] = r["rrf_score"]
            lc_docs.append(Document(page_content=content, metadata=meta))

        print(f"[RetrievalNode] Passing {len(lc_docs)} docs to TutorAgent.")
        return {"retrieved_docs": lc_docs}
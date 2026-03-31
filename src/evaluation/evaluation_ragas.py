import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json, time, statistics

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRelevance,
    ResponseGroundedness,
)

from langchain_core.documents import Document
from src.agents.retrieval import RetrievalAgent
from src.agents.multi_queries import MultiQueryAgent
from src.agents.tutor import TutorAgent
from src.evaluation.test_questions import TEST_QUESTIONS
from src.evaluation.strategies import CHUNKING, RETRIEVAL

import dotenv
dotenv.load_dotenv()

# ── RAGAS setup ───────────────────────────────────────────────────────────

client = AsyncOpenAI()
evaluator_llm = llm_factory("gpt-4o-mini", client=client)
evaluator_embeddings = embedding_factory("openai", client=client)

METRICS = {
    "faithfulness": Faithfulness(llm=evaluator_llm),
    "answer_relevancy": AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
    "context_precision": ContextPrecision(llm=evaluator_llm),
    "context_relevance": ContextRelevance(llm=evaluator_llm),
    "response_groundedness": ResponseGroundedness(llm=evaluator_llm),
}

MAX_RESPONSE_CHARS = 800   # Prevents faithfulness max_tokens crash
MAX_CONTEXT_CHARS = 2000   # Cap total context size

# ── Source recall (no LLM) ────────────────────────────────────────────────

def compute_source_recall(docs, expected_sources):
    if not expected_sources:
        return 1.0
    found = set()
    for doc in docs:
        meta = doc.get("metadata", {})
        for field in ["slug", "video_id", "url", "page_title"]:
            val = str(meta.get(field, "")).lower()
            if val:
                found.add(val)
    hits = sum(1 for exp in expected_sources if any(exp.lower() in s for s in found))
    return round(hits / len(expected_sources), 2)

METRIC_KWARGS = {
    "faithfulness": lambda q, r, c, ref: dict(user_input=q, response=r, retrieved_contexts=c),
    "answer_relevancy": lambda q, r, c, ref: dict(user_input=q, response=r),
    "context_precision": lambda q, r, c, ref: dict(user_input=q, retrieved_contexts=c, reference=ref),
    "context_relevance": lambda q, r, c, ref: dict(user_input=q, retrieved_contexts=c),
    "response_groundedness": lambda q, r, c, ref: dict(response=r, retrieved_contexts=c),
}


def score_metric_sync(metric_name, metric, question, response, contexts, reference):
    """Score a single metric synchronously with correct kwargs."""
    try:
        kwargs_fn = METRIC_KWARGS.get(metric_name)
        if kwargs_fn:
            kwargs = kwargs_fn(question, response, contexts, reference)
        else:
            kwargs = dict(user_input=question, response=response, retrieved_contexts=contexts)

        result = metric.score(**kwargs)
        if hasattr(result, 'value'):
            return round(float(result.value), 3)
        return round(float(result), 3)
    except Exception as e:
        print(f"      [{metric_name} ERROR] {type(e).__name__}: {e}")
        return None


# ── Score all metrics for one sample ──────────────────────────────────────

def score_all_metrics(question, response, contexts, reference=None):
    """Run all RAGAS metrics on one sample. Returns dict of scores."""

    # Truncate to avoid max_tokens issues
    response_trunc = response[:MAX_RESPONSE_CHARS]
    contexts_trunc = []
    total = 0
    for c in contexts:
        if total + len(c) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining > 100:
                contexts_trunc.append(c[:remaining])
            break
        contexts_trunc.append(c)
        total += len(c)

    scores = {}
    for name, metric in METRICS.items():
        val = score_metric_sync(name, metric, question, response_trunc, contexts_trunc, reference or "")
        if val is not None and val == val:  # NaN check
            scores[name] = val
        else:
            scores[name] = 0.0
            print(f"      [{name}] failed → 0.0")

    return scores


# ── Single evaluation cell ────────────────────────────────────────────────

def evaluate_one(question_info, chunking, retrieval):
    question = question_info["question"]
    intent = question_info["intent"]
    expected_sources = question_info.get("expected_sources", [])
    ground_truth = question_info.get("ground_truth", "")

    agent = RetrievalAgent(type=chunking["chunk_type"])
    t0 = time.time()

    # Retrieve
    if retrieval["multi_query"]:
        state = {"original_question": question, "intent": intent,
                 "question_analysis": question, "conversation_history": []}
        queries = MultiQueryAgent()(state).get("search_queries", [question])
    else:
        queries = [question]

    all_docs = []
    for q in queries:
        if retrieval["search_type"] == "mmr":
            docs = agent.retrieve_mmr(q, k=8)
        else:
            docs = agent.retrieve(q, k=8)
        all_docs.extend(docs)

    # Deduplicate
    seen = set()
    unique = []
    for d in all_docs:
        key = d["content"][:200]
        if key not in seen:
            seen.add(key)
            unique.append(d)

    # Source recall (before reranking)
    source_recall = compute_source_recall(unique, expected_sources)

    # Rerank
    if retrieval["rerank"] and unique:
        unique = agent.rerank(question, unique)

    # Cap docs
    unique = unique[:4]
    contexts = [d["content"] for d in unique if d.get("content")]

    # Generate tutor response
    lc_docs = [Document(page_content=c) for c in contexts]
    try:
        answer = TutorAgent()({
            "original_question": question, "retrieved_docs": lc_docs,
            "intent": intent, "response_style": "conceptual",
            "question_analysis": question, "competence_level": "intermediate",
            "complexity": "simple", "conversation_history": [],
        }).get("final_answer", "")
    except Exception as e:
        print(f"    [TutorAgent error] {e}")
        answer = ""

    latency = round(time.time() - t0, 3)

    # RAGAS scoring (per-metric, with truncation)
    scores = score_all_metrics(question, answer, contexts, ground_truth)

    overall = round(statistics.mean(scores.values()), 3) if scores else 0.0

    return {
        "question": question, "intent": intent,
        "chunking": chunking["name"], "retrieval": retrieval["name"],
        "source_recall": source_recall,
        "latency_s": latency,
        **scores,
        "overall": overall,
    }


# ── Run all ───────────────────────────────────────────────────────────────

def run_evaluation():
    all_results = []
    total = len(CHUNKING) * len(RETRIEVAL)
    idx = 0

    for cs in CHUNKING:
        for rs in RETRIEVAL:
            idx += 1
            combo = f"{cs['name']}+{rs['name']}"
            print(f"\n{'='*60}")
            print(f"[{idx}/{total}] {combo}")
            print(f"{'='*60}")

            for q in TEST_QUESTIONS:
                print(f"  Q: {q['question'][:55]}...")
                try:
                    r = evaluate_one(q, cs, rs)
                    all_results.append(r)
                    metric_str = " ".join(f"{k}={v:.2f}" for k, v in r.items()
                                         if k in METRICS or k in ["source_recall", "overall"])
                    print(f"    {metric_str}")
                except Exception as e:
                    print(f"    ✗ {e}")

            # Auto-save after each combo
            with open("evaluation_results.json", "w") as f:
                json.dump(all_results, f, indent=2)
            print(f"  [{len(all_results)} results saved]")

    # ── Summary ───────────────────────────────────────────────────────
    metric_names = list(METRICS.keys())

    print("\n" + "=" * 130)
    combos = {}
    for r in all_results:
        key = f"{r['chunking']:<12} | {r['retrieval']}"
        combos.setdefault(key, []).append(r)

    header = f"{'Strategy':<40} {'Overall':>7}"
    for m in metric_names:
        header += f" {m[:8]:>9}"
    header += f" {'SrcRec':>7}"
    print(header)
    print("-" * 130)

    for key, grp in sorted(combos.items(), key=lambda x: -statistics.mean([r['overall'] for r in x[1]])):
        def a(f): return round(statistics.mean([r.get(f, 0) for r in grp]), 3)
        line = f"{key:<40} {a('overall'):>7.3f}"
        for m in metric_names:
            line += f" {a(m):>9.3f}"
        line += f" {a('source_recall'):>7.3f}"
        print(line)

    print("\n── By chunking ──")
    for name in ["fixed_size", "recursive", "semantic", "agentic"]:
        grp = [r for r in all_results if r["chunking"] == name]
        if grp:
            def a(f): return round(statistics.mean([r.get(f, 0) for r in grp]), 3)
            print(f"  {name:<12} overall={a('overall'):.3f} src_recall={a('source_recall'):.3f}")

    print("\n── By retrieval ──")
    for rs in RETRIEVAL:
        grp = [r for r in all_results if r["retrieval"] == rs["name"]]
        if grp:
            def a(f): return round(statistics.mean([r.get(f, 0) for r in grp]), 3)
            print(f"  {rs['name']:<22} overall={a('overall'):.3f} src_recall={a('source_recall'):.3f}")

    print(f"\n[✓] Saved evaluation_results.json ({len(all_results)} results)")
    return all_results


if __name__ == "__main__":
    run_evaluation()
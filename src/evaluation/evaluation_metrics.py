import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
 
import json, time, statistics
from openai import OpenAI
from langchain_core.documents import Document
 
from src.agents.retrieval import RetrievalAgent
from src.agents.multi_queries import MultiQueryAgent
from src.agents.tutor import TutorAgent
from src.evaluation.test_questions import TEST_QUESTIONS
from src.evaluation.strategies import CHUNKING, RETRIEVAL
 
import dotenv
dotenv.load_dotenv()
 
judge_client = OpenAI()
 
# ── Source recall ─────────────────────────────────────────────────────────
 
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
 
JUDGE_PROMPT = """Score this tutoring response. Be STRICT. Use the full 1-5 scale.
3 = acceptable baseline. Only give 5 for exceptional. Give 1-2 for poor.
 
1. faithfulness (1-5): Is the answer grounded in the provided context? Or does it hallucinate?
2. answer_relevancy (1-5): Does the answer actually address the student's question?
3. context_precision (1-5): Are the retrieved materials relevant, not noisy?
4. completeness (1-5): Does it cover all aspects the student needs?
5. pedagogical_quality (1-5): Does it GUIDE (Socratic) rather than give answers directly?
 
Return ONLY JSON: {"faithfulness":X,"answer_relevancy":X,"context_precision":X,"completeness":X,"pedagogical_quality":X}"""
 
 
def judge_response(question, contexts_text, answer):
    try:
        resp = judge_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=200,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nContext (first 500 chars):\n{contexts_text[:500]}\n\nAnswer (first 500 chars):\n{answer[:500]}"},
            ],
        )
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "")
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    [Judge error] {e}")
        return {k: 0 for k in ["faithfulness", "answer_relevancy", "context_precision", "completeness", "pedagogical_quality"]}
 
 
# ── Single evaluation ─────────────────────────────────────────────────────
 
SCORE_KEYS = ["faithfulness", "answer_relevancy", "context_precision", "completeness", "pedagogical_quality"]
 
def evaluate_one(question_info, chunking, retrieval):
    question = question_info["question"]
    intent = question_info["intent"]
    expected_sources = question_info.get("expected_sources", [])
 
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
 
    # Source recall
    source_recall = compute_source_recall(unique, expected_sources)
 
    # Rerank
    if retrieval["rerank"] and unique:
        unique = agent.rerank(question, unique)
 
    # Cap to 4 docs (TutorAgent only uses 4 anyway)
    unique = unique[:4]
    contexts = [d["content"] for d in unique if d.get("content")]
    contexts_text = "\n---\n".join(contexts)
 
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
 
    # Judge (fast — truncated inputs, gpt-4o-mini)
    scores = judge_response(question, contexts_text, answer)
 
    # Normalize to 0-1 scale
    normalized = {k: round(scores.get(k, 0) / 5, 3) for k in SCORE_KEYS}
    overall = round(statistics.mean(normalized.values()), 3)
 
    return {
        "question": question, "intent": intent,
        "chunking": chunking["name"], "retrieval": retrieval["name"],
        "source_recall": source_recall,
        "latency_s": latency,
        **normalized,
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
                    print(f"    faith={r['faithfulness']:.2f} rel={r['answer_relevancy']:.2f} "
                          f"cp={r['context_precision']:.2f} comp={r['completeness']:.2f} "
                          f"ped={r['pedagogical_quality']:.2f} src={r['source_recall']:.2f} "
                          f"overall={r['overall']:.3f}")
                except Exception as e:
                    print(f"    ✗ {e}")
 
            # Auto-save after each combo
            with open("evaluation_results.json", "w") as f:
                json.dump(all_results, f, indent=2)
            print(f"  [{len(all_results)} results saved]")
 
    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 115)
    combos = {}
    for r in all_results:
        key = f"{r['chunking']:<12} | {r['retrieval']}"
        combos.setdefault(key, []).append(r)
 
    print(f"{'Strategy':<40} {'Overall':>7} {'Faith':>6} {'Rel':>6} {'CtxPr':>6} "
          f"{'Comp':>6} {'Pedag':>6} {'SrcRec':>7}")
    print("-" * 115)
    for key, grp in sorted(combos.items(), key=lambda x: -statistics.mean([r['overall'] for r in x[1]])):
        def a(f): return round(statistics.mean([r[f] for r in grp]), 3)
        print(f"{key:<40} {a('overall'):>7.3f} {a('faithfulness'):>6.3f} {a('answer_relevancy'):>6.3f} "
              f"{a('context_precision'):>6.3f} {a('completeness'):>6.3f} "
              f"{a('pedagogical_quality'):>6.3f} {a('source_recall'):>7.3f}")
 
    print("\n── By chunking ──")
    for name in ["fixed_size", "recursive", "semantic", "agentic"]:
        grp = [r for r in all_results if r["chunking"] == name]
        if grp:
            def a(f): return round(statistics.mean([r[f] for r in grp]), 3)
            print(f"  {name:<12} overall={a('overall'):.3f} src_recall={a('source_recall'):.3f}")
 
    print("\n── By retrieval ──")
    for rs in RETRIEVAL:
        grp = [r for r in all_results if r["retrieval"] == rs["name"]]
        if grp:
            def a(f): return round(statistics.mean([r[f] for r in grp]), 3)
            print(f"  {rs['name']:<22} overall={a('overall'):.3f} src_recall={a('source_recall'):.3f}")
 
    print(f"\n[✓] Saved evaluation_results.json ({len(all_results)} results)")
    return all_results
 
 
if __name__ == "__main__":
    run_evaluation()
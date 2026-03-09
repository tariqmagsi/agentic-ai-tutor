import json, re
import numpy as np
from tabulate import tabulate
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_chroma import Chroma

from ragas.evaluation import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.llms.base import LangchainLLMWrapper
from ragas.embeddings.base import LangchainEmbeddingsWrapper
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithoutReference,
    SemanticSimilarity,
    BleuScore,
    RougeScore,
)
import dotenv

dotenv.load_dotenv()

# ─── Setup ────────────────────────────────────────────────────────────────────

LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
EMB = OpenAIEmbeddings(model="text-embedding-3-small")
EVAL_LLM = LangchainLLMWrapper(LLM)
EVAL_EMB = LangchainEmbeddingsWrapper(EMB)
TOP_K = 5

# Level A: no reference needed
METRICS_NO_REF = [
    Faithfulness(llm=EVAL_LLM),
    ResponseRelevancy(llm=EVAL_LLM, embeddings=EVAL_EMB),
    LLMContextPrecisionWithoutReference(llm=EVAL_LLM),
]

# Level B: needs reference
METRICS_WITH_REF = [
    SemanticSimilarity(embeddings=EVAL_EMB),
    BleuScore(),
    RougeScore(),
]


# ─── Data Sources ────────────────────────────────────────────────────────────

URLS = [
    "https://www.archi-lab.io/infopages/spring/antipatterns-spring-jpa.html",
    "https://www.archi-lab.io/infopages/spring/frequent-mistakes-in-spring.html",
    "https://www.archi-lab.io/infopages/spring/implementing-aggregates-with-spring-jpa.html",
    "https://www.archi-lab.io/infopages/material/checklist-clean-code-and-solid.html",
    "https://www.archi-lab.io/infopages/material/pmd-plugin.html",
    "https://www.archi-lab.io/infopages/coding/zykel-aufloesen-mit-dip.html",
    "https://www.archi-lab.io/infopages/ddd/ddd-glossary.html",
    "https://www.archi-lab.io/infopages/ddd/ddd-literature.html",
    "https://www.archi-lab.io/infopages/ddd/aggregate-design-rules-vernon.html",
]

YOUTUBE_IDS = ["KywRgZpLb5w"]


# ─── 6 Questions with reference answers, content types, Bloom's levels ───────

QUESTIONS = [
    {
        "q": "What is an Aggregate in Domain-Driven Design and why is it important?",
        "type": "concept",
        "bloom": "understand",
        "reference": (
            "An Aggregate is a cluster of domain objects treated as a single unit "
            "for data changes. It has a root Entity that controls all access to inner "
            "objects. Aggregates are important because they define transactional "
            "consistency boundaries, prevent tight coupling between domain objects, "
            "and enforce business invariants within their boundaries."
        ),
    },
    {
        "q": "How do I implement Constructor-based Autowiring instead of Field-based Autowiring in Spring?",
        "type": "procedure",
        "bloom": "apply",
        "reference": (
            "Instead of annotating fields with @Autowired, declare dependencies as "
            "private final fields and accept them through the constructor. Spring "
            "automatically injects them. Example: @Service public class OrderService { "
            "private final OrderRepository repo; public OrderService(OrderRepository repo) "
            "{ this.repo = repo; } }. This makes dependencies explicit, enables easier "
            "testing, and prevents circular dependencies."
        ),
    },
    {
        "q": "Show me a code example of a side effect in a method that violates Clean Code principles.",
        "type": "example",
        "bloom": "analyze",
        "reference": (
            "A checkPassword method that also initializes a session is a side effect "
            "violation. The method name says 'check' but it also does something hidden: "
            "public boolean checkPassword(String user, String pw) { User u = findUser(user); "
            "if (u.passwordMatches(pw)) { Session.initialize(); return true; } return false; }. "
            "The Session.initialize() call is a hidden side effect that violates the "
            "Clean Code principle of doing only one thing per function."
        ),
    },
    {
        "q": "What is the difference between Entity and Value Object in DDD?",
        "type": "comparison",
        "bloom": "analyze",
        "reference": (
            "An Entity is defined by its identity — two Entities with the same ID are "
            "equal even if their attributes differ. A Value Object has no identity and "
            "is defined entirely by its attributes — two Value Objects with the same "
            "attributes are equal. Value Objects are immutable. Entities have a lifecycle "
            "managed by Repositories, while Value Objects are typically embedded."
        ),
    },
    {
        "q": "Why should I use UUID instead of Long for Entity IDs in Spring JPA?",
        "type": "rule",
        "bloom": "evaluate",
        "reference": (
            "Long IDs lack type safety — you can accidentally pass an OrderId where "
            "a CustomerId is expected and the compiler won't catch it. UUID wrapped "
            "in a typed Value Object (e.g., @Embeddable OrderId) prevents this mix-up, "
            "provides globally unique identifiers, and follows DDD best practices for "
            "aggregate identity."
        ),
    },
    {
        "q": "Why should I learn about Clean Code rules and what are the key takeaways?",
        "type": "summary",
        "bloom": "synthesize",
        "reference": (
            "Bad code slows teams down exponentially over time through technical debt. "
            "Key takeaways: use meaningful intention-revealing names, keep functions small "
            "and focused on one thing, avoid side effects, follow the DRY principle, "
            "handle errors with exceptions not return codes, and write comments only when "
            "necessary. Clean Code saves time and makes teams more productive."
        ),
    },
]


# ─── Eval Agent (your pedagogical evaluation prompt) ─────────────────────────

EVAL_AGENT_PROMPT = """You are an evaluation agent for an AI tutor.

Your job: check the tutor's response for accuracy against the retrieved context,
and assess pedagogical quality.

You receive the student's question, the tutor's response, and the retrieved context.

Return ONLY this JSON:
{
  "accuracy_score": float 0.0 to 1.0,
  "accuracy_issues": ["list any errors found, or empty"],
  "understanding_level": "strong" | "moderate" | "weak" | "unclear",
  "avoided_direct_answers": true | false,
  "scaffolding_quality": "excellent" | "good" | "fair" | "poor",
  "bloom_level_match": true | false,
  "explanation": "one sentence explaining your assessment"
}

Scoring guide:
- accuracy_score: 1.0 = fully correct, 0.0 = completely wrong
- understanding_level: based on whether the answer would help a student understand
  - strong: clear explanation with examples, builds understanding step by step
  - moderate: correct but could explain better
  - weak: incomplete or confusing explanation
  - unclear: not enough content to judge
- scaffolding_quality: does the answer build from simple to complex?
  - excellent: introduces concept, explains, gives example, connects to broader context
  - good: explains well but missing one element
  - fair: just states facts without building understanding
  - poor: confusing or disorganized
- bloom_level_match: does the answer match the expected cognitive level?
  For "understand" questions: should define and explain
  For "apply" questions: should show how to do something with code
  For "analyze" questions: should break down and compare
  For "evaluate" questions: should explain trade-offs and reasoning
  For "synthesize" questions: should connect multiple ideas

Output ONLY valid JSON. No markdown, no explanation outside JSON."""


def run_eval_agent(question, answer, context, bloom_level):
    """Run your pedagogical evaluation agent on one Q&A pair."""
    prompt = (
        f"{EVAL_AGENT_PROMPT}\n\n"
        f"Expected Bloom's level: {bloom_level}\n"
        f"Question: {question}\n"
        f"Retrieved Context: {context[:2000]}\n"
        f"Tutor's Response: {answer}"
    )
    try:
        raw = LLM.invoke(prompt).content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return {
            "accuracy_score": 0.0, "understanding_level": "unclear",
            "avoided_direct_answers": False, "scaffolding_quality": "poor",
            "bloom_level_match": False,
        }


# ─── Content-Type Alignment Check ───────────────────────────────────────────

def check_content_type_alignment(retrieved_docs, expected_type):
    """Check if retrieved chunks match the expected content type."""
    if not retrieved_docs:
        return 0.0
    matches = 0
    for doc in retrieved_docs:
        chunk_type = doc.metadata.get("content_type", "")
        if chunk_type == expected_type:
            matches += 1
    return matches / len(retrieved_docs)


# ─── Raw Document Loading ────────────────────────────────────────────────────

def _fetch_soup(url):
    soup = BeautifulSoup(requests.get(url, timeout=15).text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()
    return soup


def _extract_prose(soup):
    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    sections, heading, lines = [], "", []
    for tag in main.find_all(["h1", "h2", "h3", "p", "li", "td", "th", "blockquote"]):
        if tag.name in ("h1", "h2", "h3"):
            if lines:
                sections.append((heading, " ".join(lines)))
                lines = []
            heading = tag.get_text(strip=True)
        elif (text := tag.get_text(strip=True)):
            lines.append(text)
    if lines:
        sections.append((heading, " ".join(lines)))
    return [Document(page_content=t, metadata={"heading": h}) for h, t in sections if t]


def _extract_code(soup, url):
    docs = []
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    for pre in soup.find_all("pre"):
        code = pre.get_text().strip()
        if code:
            docs.append(Document(page_content=code, metadata={"slug": slug, "is_code": True}))
        pre.decompose()
    return docs


def load_all_raw():
    print("\n── Loading raw documents ──")
    raw = []
    for url in URLS:
        try:
            soup = _fetch_soup(url)
            raw.extend(_extract_code(soup, url))
            raw.extend(_extract_prose(soup))
            print(f"  ✓ {url.split('/')[-1]}")
        except Exception as e:
            print(f"  ✗ {url}: {e}")
    for vid in YOUTUBE_IDS:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript = YouTubeTranscriptApi().fetch(vid).to_raw_data()
            text = " ".join(t.get("text", "") for t in transcript if t.get("text"))
            raw.append(Document(page_content=text, metadata={"video_id": vid}))
            print(f"  ✓ YouTube: {vid}")
        except Exception as e:
            print(f"  ✗ YouTube {vid}: {e}")
    print(f"  Total: {len(raw)} raw documents")
    return raw


# ─── Chunking Strategies ────────────────────────────────────────────────────

def _agentic_chunk(docs):
    """LLM splits into topical chunks. 1 call per doc."""
    result = []
    for doc in docs:
        text = doc.page_content
        if len(text) < 50:
            result.append(Document(page_content=text))
            continue
        prompt = (
            "Split this text into coherent topical chunks.\n"
            "Return ONLY a JSON array: [{\"title\": \"...\", \"content\": \"...\"}]\n"
            "Rules: replace pronouns, keep code intact, 100-500 words each.\n\n"
            f"Text:\n{text[:4000]}"
        )
        try:
            raw = LLM.invoke(prompt).content.strip().replace("```json", "").replace("```", "").strip()
            chunks = json.loads(raw)
            for c in chunks:
                content = c.get("content", "")
                title = c.get("title", "")
                if content:
                    result.append(Document(page_content=f"{title}\n\n{content}" if title else content))
        except Exception:
            result.append(Document(page_content=text))
    return result or [Document(page_content=d.page_content) for d in docs]


CHUNKERS = {
    "Semantic(0.80)": lambda d: SemanticChunker(
        embeddings=EMB, breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=0.80).split_documents(d),
    "Recursive(500)": lambda d: RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " "]).split_documents(d),
    "Fixed(500)": lambda d: CharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separator=" ").split_documents(d),
    "Agentic": _agentic_chunk,
}


# ─── Retrieval (ChromaDB) ───────────────────────────────────────────────────

def build_chroma(chunks, name="eval"):
    return Chroma.from_documents(chunks, EMB, collection_name=name)


def ret_similarity(db, q):
    return db.similarity_search(q, k=TOP_K)


def ret_mmr(db, q):
    return db.max_marginal_relevance_search(q, k=TOP_K, fetch_k=TOP_K * 3)


def ret_rerank(db, q):
    cands = db.similarity_search(q, k=8)
    prompt = (
        "Score each doc's relevance 0.0–1.0. Return ONLY a JSON array of floats.\n\n"
        f"Question: {q}\n\n"
        + "\n---\n".join(f"Doc {i+1}: {d.page_content[:300]}" for i, d in enumerate(cands))
    )
    try:
        raw = LLM.invoke(prompt).content.strip().replace("```json", "").replace("```", "")
        scores = json.loads(raw)
        ranked = sorted(zip(cands, scores), key=lambda x: x[1], reverse=True)
        return [d for d, s in ranked if s >= 0.35][:TOP_K]
    except Exception:
        return cands[:TOP_K]


RETRIEVERS = {
    "Similarity": ret_similarity,
    "MMR": ret_mmr,
    "Rerank": ret_rerank,
}


# ─── Evaluate One Strategy ──────────────────────────────────────────────────

def run_eval(chunks, ret_fn, label):
    print(f"\n  ▸ {label} ({len(chunks)} chunks)")
    safe = re.sub(r'[^a-zA-Z0-9]', '', label)
    if len(safe) < 3:
        safe = "eval" + safe
    db = build_chroma(chunks, name=safe)

    samples = []
    agent_scores = []

    for i, qdata in enumerate(QUESTIONS):
        q = qdata["q"]
        print(f"    Q{i+1}({qdata['type']}/{qdata['bloom']}): {q[:50]}…")

        docs = ret_fn(db, q)
        ctx = "\n\n".join(d.page_content for d in docs)

        # Generate answer
        ans = LLM.invoke(
            f"You are a helpful AI tutor. Answer using the context below.\n"
            f"Guide the student to understand — don't just give the answer directly.\n\n"
            f"Context: {ctx}\n\nQuestion: {q}"
        ).content.strip()

        # RAGAS sample (with reference for BLEU/ROUGE/SemanticSim)
        samples.append(SingleTurnSample(
            user_input=q,
            response=ans,
            retrieved_contexts=[d.page_content for d in docs],
            reference=qdata["reference"],
        ))

        # Eval agent (pedagogical quality)
        agent = run_eval_agent(q, ans, ctx, qdata["bloom"])
        agent["content_type_alignment"] = check_content_type_alignment(docs, qdata["type"])
        agent["question_type"] = qdata["type"]
        agent["bloom_level"] = qdata["bloom"]
        agent_scores.append(agent)

    # Run RAGAS (both ref-free and ref-based metrics)
    dataset = EvaluationDataset(samples=samples)
    all_metrics = METRICS_NO_REF + METRICS_WITH_REF
    result = evaluate(dataset=dataset, metrics=all_metrics)
    df = result.to_pandas()

    # Build result row
    row = {"Strategy": label, "#Chunks": len(chunks)}

    # RAGAS scores
    skip = {"user_input", "response", "retrieved_contexts", "reference"}
    for col in df.columns:
        if col not in skip:
            vals = df[col].dropna().tolist()
            if vals:
                row[col] = f"{np.mean(vals):.3f}±{np.std(vals):.3f}"

    # Eval agent averages
    acc = [a["accuracy_score"] for a in agent_scores]
    row["accuracy"] = f"{np.mean(acc):.3f}±{np.std(acc):.3f}"

    understand = {"strong": 3, "moderate": 2, "weak": 1, "unclear": 0}
    und = [understand.get(a["understanding_level"], 0) for a in agent_scores]
    row["understanding"] = f"{np.mean(und):.2f}/3"

    scaffold = {"excellent": 3, "good": 2, "fair": 1, "poor": 0}
    scf = [scaffold.get(a.get("scaffolding_quality", "poor"), 0) for a in agent_scores]
    row["scaffolding"] = f"{np.mean(scf):.2f}/3"

    bloom_match = [1 if a.get("bloom_level_match") else 0 for a in agent_scores]
    row["bloom_match"] = f"{np.mean(bloom_match):.2f}"

    avoided = [1 if a.get("avoided_direct_answers") else 0 for a in agent_scores]
    row["guided"] = f"{np.mean(avoided):.2f}"

    cta = [a["content_type_alignment"] for a in agent_scores]
    row["type_align"] = f"{np.mean(cta):.3f}"

    db.delete_collection()
    return row, agent_scores


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Master Thesis Evaluation")
    print("  RQ: Chunking & retrieval → explanation quality + learning")
    print("  Levels: Retrieval | Answer | Pedagogical")
    print("=" * 60)

    raw_docs = load_all_raw()
    results = []
    all_agent = {}

    # A) Chunking only
    print("\n" + "=" * 60)
    print("  MODE A: Chunking Only (retrieval = Similarity)")
    print("=" * 60)
    for cname, cfn in CHUNKERS.items():
        chunks = cfn(raw_docs)
        row, agents = run_eval(chunks, ret_similarity, cname)
        results.append(row)
        all_agent[cname] = agents

    # B) Retrieval only
    print("\n" + "=" * 60)
    print("  MODE B: Retrieval Only (chunking = Semantic 0.80)")
    print("=" * 60)
    fixed = CHUNKERS["Semantic(0.80)"](raw_docs)
    for rname, rfn in RETRIEVERS.items():
        label = f"Sem+{rname}"
        row, agents = run_eval(fixed, rfn, label)
        results.append(row)
        all_agent[label] = agents

    # C) Combined (top candidates only to save time)
    print("\n" + "=" * 60)
    print("  MODE C: Combined")
    print("=" * 60)
    for cname in ["Semantic(0.80)", "Recursive(500)", "Agentic"]:
        chunks = CHUNKERS[cname](raw_docs)
        for rname, rfn in RETRIEVERS.items():
            label = f"{cname}+{rname}"
            row, agents = run_eval(chunks, rfn, label)
            results.append(row)
            all_agent[label] = agents

    # ── Print comparison table ──
    print("\n" + "=" * 70)
    print("  FULL COMPARISON TABLE")
    print("=" * 70)
    print(tabulate(results, headers="keys", tablefmt="github"))

    # ── Per-question breakdown by content type ──
    print("\n" + "=" * 70)
    print("  PER-QUESTION TYPE ANALYSIS (averaged across strategies)")
    print("=" * 70)
    type_stats = {}
    for label, agents in all_agent.items():
        for a in agents:
            qt = a["question_type"]
            if qt not in type_stats:
                type_stats[qt] = {"accuracy": [], "understanding": [], "scaffolding": [], "alignment": []}
            type_stats[qt]["accuracy"].append(a["accuracy_score"])
            understand_map = {"strong": 3, "moderate": 2, "weak": 1, "unclear": 0}
            type_stats[qt]["understanding"].append(understand_map.get(a["understanding_level"], 0))
            scaffold_map = {"excellent": 3, "good": 2, "fair": 1, "poor": 0}
            type_stats[qt]["scaffolding"].append(scaffold_map.get(a.get("scaffolding_quality", "poor"), 0))
            type_stats[qt]["alignment"].append(a["content_type_alignment"])

    type_table = []
    for qt, stats in type_stats.items():
        bloom = next((q["bloom"] for q in QUESTIONS if q["type"] == qt), "")
        type_table.append({
            "Type": qt,
            "Bloom": bloom,
            "Accuracy": f"{np.mean(stats['accuracy']):.3f}",
            "Understanding": f"{np.mean(stats['understanding']):.2f}/3",
            "Scaffolding": f"{np.mean(stats['scaffolding']):.2f}/3",
            "TypeAlign": f"{np.mean(stats['alignment']):.3f}",
        })
    print(tabulate(type_table, headers="keys", tablefmt="github"))

    # ── Best strategies ──
    print("\n── Best Strategies ──")
    for col in results[0]:
        if col in ("Strategy", "#Chunks"):
            continue
        try:
            best = max(results, key=lambda r: float(r.get(col, "0").split("±")[0].split("/")[0]))
            print(f"  {col:30s} → {best['Strategy']:25s} ({best[col]})")
        except Exception:
            pass

    # Save
    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    with open("eval_agent_details.json", "w") as f:
        json.dump(all_agent, f, indent=2, default=str)
    print("\n✅ Saved to eval_results.json + eval_agent_details.json")


if __name__ == "__main__":
    main()
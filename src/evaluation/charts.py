import json, sys, statistics
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
 
matplotlib.rcParams.update({"font.size": 11, "font.family": "sans-serif", "figure.dpi": 150})
 
path = sys.argv[1] if len(sys.argv) > 1 else "evaluation_results.json"
with open(path) as f:
    results = json.load(f)
 
DIMS = ["relevance", "completeness", "pedagogical_quality", "accuracy", "coherence"]
DIM_LABELS = ["Relevance", "Completeness", "Pedagogical\nQuality", "Accuracy", "Coherence"]
DIM_SHORT = ["Relev.", "Compl.", "Pedag.", "Accur.", "Coher."]
 
CHUNK_ORDER = ["fixed_size", "recursive", "semantic", "agentic"]
CHUNK_LABELS = ["Fixed-size", "Recursive", "Semantic", "Agentic"]
 
RETR_ORDER = ["cosine_similarity", "mmr", "multi_query_cosine", "multi_query_rerank"]
RETR_LABELS = ["Cosine\nSimilarity", "MMR", "Multi-Query\n+ Cosine", "Multi-Query\n+ Rerank"]
 
 
def avg(group, field=None):
    if field:
        return round(statistics.mean([r["scores"][field] for r in group]), 2)
    return round(statistics.mean([r["overall"] for r in group]), 2)

 
 
# ── Fig 1: Chunking comparison ────────────────────────────────────────────
 
def fig1_chunking():
    by_chunk = {c: [r for r in results if r["chunking"] == c] for c in CHUNK_ORDER}
    x = np.arange(len(DIMS))
    width = 0.2
    colors = ["#95a5a6", "#3498db", "#e67e22", "#27ae60"]
 
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (name, label) in enumerate(zip(CHUNK_ORDER, CHUNK_LABELS)):
        vals = [avg(by_chunk[name], d) for d in DIMS]
        bars = ax.bar(x + i * width, vals, width, label=label, color=colors[i], edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8)
 
    ax.set_ylabel("Average Score (1–5)")
    ax.set_ylim(0, 5.5)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(DIM_LABELS)
    ax.legend(loc="upper left")
    ax.set_title("Figure 2: Chunking strategy comparison across quality dimensions", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("fig1_chunking.png", bbox_inches="tight")
    plt.close()
    print("[✓] fig1_chunking.png")
 
 
# ── Fig 2: Retrieval comparison ───────────────────────────────────────────
 
def fig2_retrieval():
    by_retr = {r: [x for x in results if x["retrieval"] == r] for r in RETR_ORDER}
    x = np.arange(len(DIMS))
    width = 0.2
    colors = ["#95a5a6", "#9b59b6", "#e67e22", "#27ae60"]
    labels = ["Cosine Similarity", "MMR", "Multi-Query + Cosine", "Multi-Query + Rerank"]
 
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (name, label) in enumerate(zip(RETR_ORDER, labels)):
        vals = [avg(by_retr[name], d) for d in DIMS]
        bars = ax.bar(x + i * width, vals, width, label=label, color=colors[i], edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8)
 
    ax.set_ylabel("Average Score (1–5)")
    ax.set_ylim(0, 5.5)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(DIM_LABELS)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Figure 3: Retrieval strategy comparison across quality dimensions", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("fig2_retrieval.png", bbox_inches="tight")
    plt.close()
    print("[✓] fig2_retrieval.png")

 
 
# ── Run all ───────────────────────────────────────────────────────────────
fig1_chunking()
fig2_retrieval()
print("\nAll 5 figures saved.")
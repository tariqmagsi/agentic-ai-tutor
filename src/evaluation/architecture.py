# ── Agent definitions (mirrors graph.py) ──────────────────────────────────

AGENTS = [
    {
        "name": "QuestionUnderstandingAgent",
        "role": "understanding",
        "description": "Classifies intent (concept/example/procedure/comparison/rule/summary), "
                       "response_style, complexity, and rewrites the query for retrieval.",
        "inputs": ["original_question", "conversation_history"],
        "outputs": ["intent", "response_style", "question_analysis", "complexity"],
        "rationale": "Decouples interpretation from generation — downstream agents get explicit "
                     "instructions on WHAT to teach and HOW to teach.",
    },
    {
        "name": "RouterAgent",
        "role": "routing",
        "description": "Decides if clarification is needed (high threshold) or the tutor pipeline can proceed.",
        "inputs": ["original_question", "question_analysis", "conversation_history"],
        "outputs": ["route", "needs_clarification", "clarification_question"],
        "rationale": "Prevents low-quality responses on ambiguous input without over-asking.",
    },
    {
        "name": "ClarificationAgent",
        "role": "clarification",
        "description": "Generates a warm, specific clarification question when the router flags ambiguity.",
        "inputs": ["original_question", "clarification_question"],
        "outputs": ["final_answer"],
        "rationale": "Dedicated agent ensures clarification is empathetic and targeted.",
    },
    {
        "name": "PersonalizationAgent",
        "role": "personalization",
        "description": "Assesses competence (novice/intermediate/advanced) from writing style per turn.",
        "inputs": ["original_question", "conversation_history"],
        "outputs": ["competence_level"],
        "rationale": "Enables adaptive depth — novices get analogies, advanced students get trade-offs.",
    },
    {
        "name": "MultiQueryAgent",
        "role": "query_expansion",
        "description": "Expands the question into 3-4 diverse search queries for better retrieval recall.",
        "inputs": ["original_question", "intent", "question_analysis", "conversation_history"],
        "outputs": ["search_queries"],
        "rationale": "Addresses vocabulary mismatch — a single query misses chunks with different terminology.",
    },
    {
        "name": "RetrievalNode",
        "role": "retrieval",
        "description": "Multi-query vector search → RRF fusion → LLM reranking → fallback if too few results.",
        "inputs": ["original_question", "search_queries", "intent", "response_style"],
        "outputs": ["retrieved_docs"],
        "rationale": "Multi-query + RRF = high recall; LLM reranking = high precision; fallback = robustness.",
    },
    {
        "name": "TutorAgent",
        "role": "generation",
        "description": "Generates Socratic response using course material. Never gives full solutions. "
                       "Ends with exactly one guiding question.",
        "inputs": ["original_question", "retrieved_docs", "intent", "response_style",
                   "competence_level", "complexity", "conversation_history"],
        "outputs": ["final_answer"],
        "rationale": "Core pedagogical engine with tightly scoped behavior per response_style.",
    },
    {
        "name": "EvaluationAgent",
        "role": "evaluation",
        "description": "Scores the tutor's response on multiple quality dimensions for monitoring.",
        "inputs": ["original_question", "final_answer", "retrieved_docs"],
        "outputs": ["evaluation"],
        "rationale": "Enables continuous quality monitoring and degradation detection.",
    },
]

DESIGN_PRINCIPLES = [
    "Single Responsibility — each agent handles exactly one cognitive task.",
    "Separation of WHAT vs HOW — intent and response_style classified independently.",
    "Adaptive Personalization — competence assessed per-turn from writing style.",
    "Multi-Query RAG with Reranking — query expansion + RRF fusion + LLM scoring.",
    "Socratic Pedagogy by Design — TutorAgent prompt enforces guiding, not telling.",
    "Graceful Degradation — fallback to unfiltered retrieval; clarification on ambiguity.",
    "Observable Pipeline — every agent logs; EvaluationAgent scores every response.",
    "LangGraph Orchestration — declarative StateGraph with conditional branching.",
]


# ── Mermaid diagram generators ────────────────────────────────────────────

def agent_flow_mermaid():
    return """graph TD
    QU[Question understanding] --> RT[Router]
    RT -->|clarify| CL[Clarification]
    RT -->|tutor| PR[Personalization]
    PR --> MQ[Multi-query expansion]
    MQ --> RN[Retrieval + reranking]
    RN --> TA[Tutor - Socratic]
    TA --> EV[Evaluation]
    CL --> EV
    EV --> END([END])

    subgraph Input_Analysis["Input analysis"]
        QU; RT
    end
    subgraph Tutor_Pipeline["Tutor pipeline"]
        PR; MQ; RN; TA
    end
"""


def sequence_mermaid():
    return """sequenceDiagram
    participant S as Student
    participant QU as QuestionUnderstanding
    participant RT as Router
    participant PR as Personalization
    participant MQ as MultiQueryAgent
    participant VS as ChromaDB
    participant RR as Reranker (LLM)
    participant TA as TutorAgent
    participant EV as EvaluationAgent

    S->>QU: student question
    QU->>RT: intent, style, complexity
    RT->>PR: route=tutor
    PR->>MQ: competence_level
    MQ->>VS: 3-4 diverse queries
    VS-->>RR: fused chunks (RRF)
    RR-->>TA: top relevant chunks
    TA->>EV: Socratic response
    EV-->>S: final answer + quality scores
"""


def ingestion_mermaid():
    return """graph LR
    subgraph Sources
        WP[Web Pages] 
        YT[YouTube Transcripts]
    end

    subgraph Semantic["Semantic chunking"]
        S1[Fetch + extract] --> S2[Embedding-based split] --> S3[Metadata extraction] --> S4[(rag_tutor_collection)]
    end

    subgraph Agentic["Agentic chunking"]
        A1[Fetch + extract] --> A2[LLM-driven split] --> A3[Metadata extraction] --> A4[(agentic_tutor_collection)]
    end

    WP --> S1; WP --> A1
    YT --> S1; YT --> A1
"""


# ── Markdown report ───────────────────────────────────────────────────────

def generate_report():
    lines = ["# Agentic AI Tutor — Multi-Agent RAG Architecture\n"]
    lines.append("A LangGraph-orchestrated pipeline of 8 specialized LLM agents implementing "
                 "a Socratic programming tutor with RAG over course material.\n")

    lines.append("## Design Principles\n")
    for i, p in enumerate(DESIGN_PRINCIPLES, 1):
        lines.append(f"{i}. {p}")
    lines.append("")

    lines.append("## Agent Specifications\n")
    for a in AGENTS:
        lines.append(f"### {a['name']} ({a['role']})\n")
        lines.append(f"{a['description']}\n")
        lines.append(f"- **Inputs:** {', '.join(a['inputs'])}")
        lines.append(f"- **Outputs:** {', '.join(a['outputs'])}")
        lines.append(f"- **Rationale:** {a['rationale']}\n")

    lines.append("## Agent Flow Diagram\n```mermaid")
    lines.append(agent_flow_mermaid())
    lines.append("```\n")

    lines.append("## Data Flow — Sequence Diagram\n```mermaid")
    lines.append(sequence_mermaid())
    lines.append("```\n")

    lines.append("## Ingestion Pipelines\n```mermaid")
    lines.append(ingestion_mermaid())
    lines.append("```\n")

    lines.append("## Chunking Strategy Comparison\n")
    lines.append("| Aspect | Semantic | Agentic (LLM) |")
    lines.append("|--------|----------|---------------|")
    lines.append("| Split method | Embedding similarity threshold | LLM decides split points |")
    lines.append("| Chunk coherence | Good for uniform text | Superior for mixed content |")
    lines.append("| Cost | Low (embeddings only) | Higher (LLM calls per window) |")
    lines.append("| Best for | Homogeneous prose | Lectures, mixed-format pages |\n")

    lines.append("## Retrieval Strategy Comparison\n")
    lines.append("| Strategy | Multi-Query | Reranking | Recall | Precision |")
    lines.append("|----------|-------------|-----------|--------|-----------|")
    lines.append("| Single, no rerank | No | No | Low | Variable |")
    lines.append("| Single + rerank | No | Yes | Low | High |")
    lines.append("| Multi + no rerank | Yes | No | High | Variable |")
    lines.append("| Multi + rerank | Yes | Yes | High | High |")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    # Print summary
    print("=" * 60)
    print("  Agentic AI Tutor Architecture")
    print("=" * 60)

    print(f"\nAgents ({len(AGENTS)}):")
    for a in AGENTS:
        print(f"  • {a['name']:<30} [{a['role']}]")

    print(f"\nDesign Principles:")
    for i, p in enumerate(DESIGN_PRINCIPLES, 1):
        print(f"  {i}. {p}")

    # Save files
    report = generate_report()
    with open("architecture_report.md", "w") as f:
        f.write(report)
    print("\n[✓] Saved architecture_report.md")

    with open("architecture_graph.mmd", "w") as f:
        f.write(agent_flow_mermaid())
    print("[✓] Saved architecture_graph.mmd")

    print("\n── Mermaid (copy to mermaid.live) ──\n")
    print(agent_flow_mermaid())


if __name__ == "__main__":
    main()
# ── Strategy definitions ──────────────────────────────────────────────────

CHUNKING = [
    {"name": "fixed_size",  "chunk_type": "fixed_size"},
    {"name": "recursive",   "chunk_type": "recursive"},
    {"name": "semantic",    "chunk_type": "semantic"},
    {"name": "agentic",     "chunk_type": "agentic"},
]

RETRIEVAL = [
    {"name": "cosine",              "multi_query": False, "search_type": "similarity", "rerank": False},
    {"name": "cosine_rerank",       "multi_query": False, "search_type": "similarity", "rerank": True},
    {"name": "mmr",                 "multi_query": False, "search_type": "mmr",        "rerank": False},
    {"name": "mmr_rerank",          "multi_query": False, "search_type": "mmr",        "rerank": True},
    {"name": "multi_cosine",        "multi_query": True,  "search_type": "similarity", "rerank": False},
    {"name": "multi_cosine_rerank", "multi_query": True,  "search_type": "similarity", "rerank": True},
    {"name": "multi_mmr",           "multi_query": True,  "search_type": "mmr",        "rerank": False},
    {"name": "multi_mmr_rerank",    "multi_query": True,  "search_type": "mmr",        "rerank": True},
]

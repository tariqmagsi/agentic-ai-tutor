import yt_dlp
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from youtube_transcript_api import YouTubeTranscriptApi

from src.prompts.chunking import AGENTIC_CHUNK_SYSTEM
from src.utils.utils import extract_metadata, nav_fields, store, llm
from src.utils.utils import safe_json_loads

# ── Load ──────────────────────────────────────────────────────────────────────

def _load(video_id: str) -> Document:
    url = f"https://www.youtube.com/watch?v={video_id}"

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    transcript = YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    text = " ".join(t.get("text", "") for t in transcript if t.get("text"))

    return Document(
        page_content=text,
        metadata={
            "video_id":    video_id,
            "video_title": info.get("title", "Untitled"),
            "author":      info.get("uploader", "Unknown"),
            "url":         url,
        },
    )


# ── Agentic chunking — LLM decides where to split ────────────────────────────

def _agentic_chunk(text: str, max_chars: int = 12000) -> list[str]:
    """Send text to LLM in windows, let it split into semantic chunks."""
    all_chunks = []
    # Process in windows to stay within context limits
    for start in range(0, len(text), max_chars):
        window = text[start:start + max_chars]
        resp = llm.invoke([
            SystemMessage(content=AGENTIC_CHUNK_SYSTEM),
            HumanMessage(content=window),
        ])
        raw = resp.content.strip().replace("```json", "").replace("```", "").strip()
        chunks = safe_json_loads(raw)
        if isinstance(chunks, list):
            all_chunks.extend([c for c in chunks if isinstance(c, str) and c.strip()])
        else:
            all_chunks.append(window)
    return all_chunks


def _enrich(docs: list[Document], base_meta: dict) -> list[Document]:
    total = len(docs)
    for i, doc in enumerate(docs):
        m = extract_metadata(doc.page_content)
        doc.metadata.update({
            **base_meta,
            **nav_fields(i, total),
            "source":       "youtube",
            "content_type": m.get("content_type", "explanation")
        })
        print(f"  [{i+1}/{total}] {m.get('content_type')}")
    return docs


# ── Public entry point ────────────────────────────────────────────────────────


def run(video_id: str) -> list[Document]:
    print("📥  Loading transcript...")
    raw = _load(video_id)
    base_meta = raw.metadata.copy()

    print("🤖  Agentic chunking (LLM-driven)...")
    chunks = _agentic_chunk(raw.page_content)
    docs = [Document(page_content=c) for c in chunks]
    print(f"    → {len(docs)} chunks created")

    print(f"🧠  Extracting metadata for {len(docs)} chunks...")
    final = _enrich(docs, base_meta)

    store(final, type="agentic")
    print(f"\n✅  Stored {len(final)} chunks for '{base_meta.get('video_title')}'")
    return final
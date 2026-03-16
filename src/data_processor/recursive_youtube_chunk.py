import yt_dlp
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from youtube_transcript_api import YouTubeTranscriptApi
 
from src.utils.utils import extract_metadata, nav_fields, store
 
 
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
 
 
# ── Recursive chunker ─────────────────────────────────────────────────────────
 
_recursive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", "? ", "! ", ", ", " ", ""],
)
 
 
# ── Enrich metadata ───────────────────────────────────────────────────────────
 
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
 
    print("🔀  Recursive chunking (multi-separator)...")
    docs = _recursive_splitter.split_documents([raw])
    print(f"    → {len(docs)} chunks created")
 
    print(f"🧠  Extracting metadata for {len(docs)} chunks...")
    final = _enrich(docs, base_meta)
 
    store(final, type="recursive")
    print(f"\n✅  Stored {len(final)} recursive chunks for '{base_meta.get('video_title')}'")
    return final
import yt_dlp
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from youtube_transcript_api import YouTubeTranscriptApi

from src.utils.utils import extract_metadata, make_semantic_chunker, nav_fields, store

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


# ── Enrich metadata ───────────────────────────────────────────────────────────

_fine_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=240,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
)


def _enrich(docs: list[Document], base_meta: dict) -> list[Document]:
    total = len(docs)
    for i, doc in enumerate(docs):
        m = extract_metadata(doc.page_content)
        doc.metadata.update({
            **base_meta,
            **nav_fields(i, total),
            "source":       "youtube",
            "content_type": m.get("content_type", "explanation"),
            "domain":       "software_engineering",
            "has_code":     m.get("has_code", False),
        })
        print(f"  [{i+1}/{total}] {m.get('content_type')} | code={m.get('has_code')}")
    return docs


# ── Public entry point ────────────────────────────────────────────────────────

_semantic_chunker = make_semantic_chunker(threshold=0.75)


def run(video_id: str) -> list[Document]:
    print("📥  Loading transcript...")
    raw = _load(video_id)
    base_meta = raw.metadata.copy()

    print("🔀  Semantic chunking...")
    sem = _semantic_chunker.split_documents([raw])

    print("✂️   Fine splitting...")
    fine = _fine_splitter.split_documents(sem)

    print(f"🧠  Extracting metadata for {len(fine)} chunks...")
    final = _enrich(fine, base_meta)

    store(final)
    print(f"\n✅  Stored {len(final)} chunks for '{base_meta.get('video_title')}'")
    return final
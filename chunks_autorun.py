import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
 
from src.data_processor.fixed_size_webpage_chunk import run as fixed_webpage
from src.data_processor.recursive_webpage_chunk import run as recursive_webpage
from src.data_processor.fixed_size_youtube_chunk import run as fixed_youtube
from src.data_processor.recursive_youtube_chunk import run as recursive_youtube
from src.data_processor.webpage_chunk import run as semantic_webpage
from src.data_processor.youtube_transcript_chunk import run as semantic_youtube
from src.utils.utils import get_video_id
 
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
 
VIDEOS = [
    # "KywRgZpLb5w",
    # "WTau26feewU",
    # "kQDStoasH-Q",
    # "BFVLXYFlNXg",
    # "udPiJpvPsMQ",
    # "swax9LubOec",
    "2G20nqeHAn8",
    # "283EGmUxRN0",
]
 
if __name__ == "__main__":
    # ── Webpages ──────────────────────────────────────────────────────
    print("=" * 60)
    print("  POPULATING WEBPAGE CHUNKS")
    print("=" * 60)
    
    # for url in URLS:
    #     recursive_webpage(url)
    #     fixed_webpage(url)
    
    for video_url in VIDEOS:
        # recursive_youtube(video_url)
        fixed_youtube(video_url)
    # for url in URLS:
    #     print(f"\n{'─'*60}")
    #     print(f"[FIXED-SIZE] {url}")
    #     fixed_webpage(url)
 
    #     print(f"\n[RECURSIVE] {url}")
    #     recursive_webpage(url)
 
    # # ── YouTube ───────────────────────────────────────────────────────
    # print("\n" + "=" * 60)
    # print("  POPULATING YOUTUBE CHUNKS")
    # print("=" * 60)
 
    # for video_url in VIDEOS:
    #     video_id = get_video_id(video_url)
    #     if not video_id:
    #         print(f"  ✗ Could not extract video ID from {video_url}")
    #         continue
 
    #     print(f"\n{'─'*60}")
    #     print(f"[FIXED-SIZE] {video_url} (id={video_id})")
    #     try:
    #         fixed_youtube(video_id)
    #     except Exception as e:
    #         print(f"  ✗ Fixed-size failed: {e}")
 
    #     print(f"\n[RECURSIVE] {video_url} (id={video_id})")
    #     try:
    #         recursive_youtube(video_id)
    #     except Exception as e:
    #         print(f"  ✗ Recursive failed: {e}")
 
    print("\n" + "=" * 60)
    print("  DONE — Both collections populated!")
    print("=" * 60)
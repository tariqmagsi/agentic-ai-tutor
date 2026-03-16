import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
 
from src.data_processor.fixed_size_webpage_chunk import run as fixed_webpage
from src.data_processor.recursive_webpage_chunk import run as recursive_webpage
from src.data_processor.fixed_size_youtube_chunk import run as fixed_youtube
from src.data_processor.recursive_youtube_chunk import run as recursive_youtube
from src.utils.utils import get_video_id
 
URLS = [
    # "https://www.archi-lab.io/infopages/spring/antipatterns-spring-jpa.html",
    # "https://www.archi-lab.io/infopages/spring/frequent-mistakes-in-spring.html",
    # "https://www.archi-lab.io/infopages/spring/implementing-aggregates-with-spring-jpa.html",
    # "https://www.archi-lab.io/infopages/material/checklist-clean-code-and-solid.html",
    # "https://www.archi-lab.io/infopages/material/pmd-plugin.html",
    # "https://www.archi-lab.io/infopages/coding/zykel-aufloesen-mit-dip.html",
    # "https://www.archi-lab.io/infopages/ddd/ddd-glossary.html",
    # "https://www.archi-lab.io/infopages/ddd/ddd-literature.html",
    # "https://www.archi-lab.io/infopages/ddd/aggregate-design-rules-vernon.html",
]
 
VIDEOS = [
    # "https://www.youtube.com/watch?v=KywRgZpLb5w",
    # "https://www.youtube.com/watch?v=WTau26feewU",
    # "https://www.youtube.com/watch?v=kQDStoasH-Q",
    # "https://www.youtube.com/watch?v=BFVLXYFlNXg",
    # "https://www.youtube.com/watch?v=udPiJpvPsMQ",
    "https://www.youtube.com/watch?v=swax9LubOec",
    "https://www.youtube.com/watch?v=2G20nqeHAn8",
    "https://www.youtube.com/watch?v=283EGmUxRN0",
]
 
if __name__ == "__main__":
    # ── Webpages ──────────────────────────────────────────────────────
    print("=" * 60)
    print("  POPULATING WEBPAGE CHUNKS")
    print("=" * 60)
 
    for url in URLS:
        print(f"\n{'─'*60}")
        print(f"[FIXED-SIZE] {url}")
        fixed_webpage(url)
 
        print(f"\n[RECURSIVE] {url}")
        recursive_webpage(url)
 
    # ── YouTube ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  POPULATING YOUTUBE CHUNKS")
    print("=" * 60)
 
    for video_url in VIDEOS:
        video_id = get_video_id(video_url)
        if not video_id:
            print(f"  ✗ Could not extract video ID from {video_url}")
            continue
 
        print(f"\n{'─'*60}")
        print(f"[FIXED-SIZE] {video_url} (id={video_id})")
        try:
            fixed_youtube(video_id)
        except Exception as e:
            print(f"  ✗ Fixed-size failed: {e}")
 
        print(f"\n[RECURSIVE] {video_url} (id={video_id})")
        try:
            recursive_youtube(video_id)
        except Exception as e:
            print(f"  ✗ Recursive failed: {e}")
 
    print("\n" + "=" * 60)
    print("  DONE — Both collections populated!")
    print("=" * 60)
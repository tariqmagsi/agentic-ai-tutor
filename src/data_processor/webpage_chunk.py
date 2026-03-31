from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from src.prompts.chunking import CODE_CHUNK_SYSTEM
from src.utils.utils import extract_metadata, make_semantic_chunker, nav_fields, store, llm

# ── Code-block description ────────────────────────────────────────────────────

_code_desc_chain = ChatPromptTemplate.from_messages([
    ("system", CODE_CHUNK_SYSTEM),
    ("human", "Code block:\n\n{code}"),
]) | llm


def _describe_code(code: str) -> str:
    try:
        return _code_desc_chain.invoke({"code": code}).content.strip()
    except Exception:
        return ""


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _fetch_soup(url: str) -> BeautifulSoup:
    html = requests.get(url, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()
    return soup


def _page_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title") or soup.find("h2")
    return tag.get_text(strip=True) if tag else ""


# ── Extract code blocks ───────────────────────────────────────────────────────

def _extract_code_blocks(soup: BeautifulSoup, url: str, slug: str, page_title: str) -> list[Document]:
    """Pull every <pre> block out as an un-split Document and remove it from the soup."""
    docs = []
    for pre in soup.find_all("pre"):
        code = pre.get_text().strip()
        if code:
            desc = _describe_code(code)
            docs.append(Document(
                page_content=f"{desc}\n\n{code}" if desc else code,
                metadata={
                    "source": "webpage", "url": url, "slug": slug,
                    "page_title": page_title, "content_type": "example",
                    "code_description": desc
                },
            ))
        pre.decompose()
    return docs


# ── Extract prose sections ────────────────────────────────────────────────────

def _extract_prose(soup: BeautifulSoup) -> list[Document]:
    """Walk the cleaned HTML and return one Document per heading-section."""
    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    sections, heading, lines = [], "", []

    for tag in main.find_all(["h1", "h2", "h3", "p", "li", "td", "th", "blockquote"]):
        if tag.name in ("h1", "h2", "h3"):
            if lines:
                sections.append((heading, " ".join(lines)))
                lines = []
            heading = tag.get_text(strip=True)
        elif text := tag.get_text(strip=True):
            lines.append(text)

    if lines:
        sections.append((heading, " ".join(lines)))

    return [
        Document(page_content=text, metadata={"section_heading": h})
        for h, text in sections if text
    ]


# ── Enrich metadata ───────────────────────────────────────────────────────────

def _enrich(docs: list[Document], url: str, slug: str, page_title: str) -> list[Document]:
    total = len(docs)
    for i, doc in enumerate(docs):
        nav = nav_fields(i, total)
        if doc.metadata.get("is_code_block"):
            doc.metadata.update(nav)
            print(f"  [{i+1}/{total}] [CODE] {doc.metadata.get('code_description', '')[:70]}")
        else:
            m = extract_metadata(doc.page_content)
            doc.metadata.update({
                **nav,
                "source": "webpage", "url": url, "slug": slug,
                "page_title": page_title, "is_code_block": False,
                "content_type": m.get("content_type", "concept")
            })
            print(f"  [{i+1}/{total}] [{doc.metadata.get('section_heading', '')}] "
                  f"{m.get('content_type')}")
    return docs


# ── Public entry point ────────────────────────────────────────────────────────

# URLS = [
#     "https://www.archi-lab.io/infopages/spring/antipatterns-spring-jpa.html",
#     "https://www.archi-lab.io/infopages/spring/frequent-mistakes-in-spring.html",
#     "https://www.archi-lab.io/infopages/spring/implementing-aggregates-with-spring-jpa.html",
#     "https://www.archi-lab.io/infopages/material/checklist-clean-code-and-solid.html",
#     "https://www.archi-lab.io/infopages/material/pmd-plugin.html",
#     "https://www.archi-lab.io/infopages/coding/zykel-aufloesen-mit-dip.html",
#     "https://www.archi-lab.io/infopages/ddd/ddd-glossary.html",
#     "https://www.archi-lab.io/infopages/ddd/ddd-literature.html",
#     "https://www.archi-lab.io/infopages/ddd/aggregate-design-rules-vernon.html",
# ]


def run(url: str) -> list[Document]:
    all_docs: list[Document] = []
    
    
    # for url in urls:
    try:
        print(f"\n📥  Loading: {url}")
        soup       = _fetch_soup(url)
        slug       = urlparse(url).path.rstrip("/").split("/")[-1]
        page_title = _page_title(soup)

        print("🔲  Extracting code blocks...")
        _chunker = make_semantic_chunker(threshold=0.80)
        code_docs  = _extract_code_blocks(soup, url, slug, page_title)

        print("🔀  Semantic chunking prose...")
        prose_docs = _chunker.split_documents(_extract_prose(soup))

        chunks = _enrich(code_docs + prose_docs, url, slug, page_title)
        all_docs.extend(chunks)
        print(f"🧠  {len(chunks)} chunks enriched.")

    except Exception as e:
        print(f"  ❌ Failed: {url} — {e}")

    store(all_docs, type="semantic")
    print(f"\n✅  Stored {len(all_docs)} chunks from {len(url)} pages")
    return all_docs

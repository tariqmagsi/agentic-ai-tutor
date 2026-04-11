import os
import re
import zipfile
import tempfile
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage

from src.prompts.chunking import AGENTIC_CHUNK_SYSTEM, JAVA_DESCRIBE_SYSTEM, JAVA_TEST_SYSTEM
from src.utils.utils import extract_metadata, nav_fields, store, llm, safe_json_loads

# ── File discovery ────────────────────────────────────────────────────────────

_SKIP = {".git", ".idea", ".mvn", ".gradle", "build", "target", "bin", "out", "node_modules"}
_DOC_EXT = {".md", ".txt", ".adoc", ".rst"}
_CFG_EXT = {".properties", ".yml", ".yaml", ".xml", ".json"}
_CFG_NAMES = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"}


def _discover(root: str) -> dict[str, list[Path]]:
    base = Path(root)
    buckets: dict[str, list[Path]] = {"src": [], "test": [], "config": [], "docs": []}
    for p in sorted(base.rglob("*")):
        if any(s in p.parts for s in _SKIP) or not p.is_file():
            continue
        parts_lower = [x.lower() for x in p.relative_to(base).parts]
        if p.suffix == ".java":
            is_test = "test" in parts_lower or p.name.endswith(("Test.java", "Tests.java", "IT.java"))
            buckets["test" if is_test else "src"].append(p)
        elif p.suffix in _CFG_EXT or p.name in _CFG_NAMES:
            buckets["config"].append(p)
        elif p.suffix in _DOC_EXT:
            buckets["docs"].append(p)
    return buckets


# ── Java helpers ──────────────────────────────────────────────────────────────

_PKG_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
_KIND_RE = re.compile(r"\b(interface|abstract\s+class|enum|record|class)\s+(\w+)", re.MULTILINE)


def _parse_info(source: str) -> dict:
    pkg = (m.group(1) if (m := _PKG_RE.search(source)) else "")
    km = _KIND_RE.search(source)
    kind = km.group(1).replace("abstract ", "abstract_") if km else "class"
    name = km.group(2) if km else ""
    return {"package": pkg, "kind": kind, "name": name}


def _is_spec(kind: str) -> bool:
    return kind in ("interface", "abstract_class", "annotation")


def _strip_bodies(source: str) -> str:
    """Remove method bodies — keep signatures, fields, annotations."""
    lines, out, depth, in_body = source.splitlines(), [], 0, False
    for line in lines:
        if line.strip().startswith(("package ", "import ")):
            out.append(line); continue
        opens, closes = line.count("{"), line.count("}")
        if not in_body:
            out.append(line)
            if depth >= 1 and opens > 0:
                in_body = True
        depth += opens - closes
        if in_body and depth <= 1:
            out.append("    // ... implementation hidden ...")
            out.append("  }")
            in_body = False
    return "\n".join(out)


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _describe(skeleton: str, info: dict) -> str:
    resp = llm.invoke([
        SystemMessage(content=JAVA_DESCRIBE_SYSTEM),
        HumanMessage(content=f"{info['kind']}: {info['name']}\nPackage: {info['package']}\n\n{skeleton}"),
    ])
    return resp.content.strip()


def _summarize_tests(source: str, name: str) -> str:
    resp = llm.invoke([
        SystemMessage(content=JAVA_TEST_SYSTEM),
        HumanMessage(content=f"Test class: {name}\n\n{source[:8000]}"),
    ])
    return resp.content.strip()


def _agentic_chunk(text: str, max_chars: int = 12000) -> list[str]:
    all_chunks = []
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


# ── Enrich metadata (same pattern as webpage & youtube) ──────────────────────

def _enrich(docs: list[Document], repo: str) -> list[Document]:
    total = len(docs)
    for i, doc in enumerate(docs):
        m = extract_metadata(doc.page_content)
        nav = nav_fields(i, total)

        content_type = m.get("content_type", doc.metadata.get("content_type", "concept"))

        doc.metadata.update({
            **nav,
            "source": "java_repo",
            "page_title": repo,
            "content_type": content_type,
        })

        heading = doc.metadata.get("section_heading", "")
        desc = doc.metadata.get("code_description", "")
        print(f"  [{i+1}/{total}] [{heading}] {desc[:70]}")
    return docs


# ── Public entry point ────────────────────────────────────────────────────────

def _resolve_path(path: str) -> tuple[str, any]:
    """Handle zip files or plain folders. Returns (project_root, temp_dir_or_None)."""
    p = Path(path)
    if p.suffix == ".zip" and p.is_file():
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(p) as zf:
            zf.extractall(tmp)
        children = [d for d in Path(tmp).iterdir() if d.is_dir()]
        root = str(children[0]) if len(children) == 1 else tmp
        return root, tmp
    return str(p), None


def _find_project_root(path: str) -> str:
    """Walk down until we find src/ or pom.xml — handles nested folders."""
    root = Path(path)
    if (root / "src").exists() or (root / "pom.xml").exists() or (root / "build.gradle").exists():
        return str(root)
    for child in root.iterdir():
        if child.is_dir():
            if (child / "src").exists() or (child / "pom.xml").exists():
                return str(child)
    return str(root)


def run(repo_path: str) -> list[Document]:
    """Chunk a Java project folder or zip file for the agentic tutor."""
    resolved, tmp_dir = _resolve_path(repo_path)
    resolved = _find_project_root(resolved)
    repo_name = os.path.basename(os.path.normpath(resolved))
    all_docs: list[Document] = []

    print(f"\n📂  Scanning: {resolved}")
    buckets = _discover(resolved)
    print(f"    {len(buckets['src'])} src, {len(buckets['test'])} test, "
          f"{len(buckets['config'])} config, {len(buckets['docs'])} docs")

    # ── Source files ──────────────────────────────────────────────────────
    print("\n📄  Processing source files...")
    for path in buckets["src"]:
        try:
            source = path.read_text(errors="replace")
            info = _parse_info(source)
            skeleton = _strip_bodies(source)
            desc = _describe(skeleton, info)
            rel = str(path.relative_to(resolved))

            if _is_spec(info["kind"]):
                # Contract description (prose — like webpage prose chunk)
                all_docs.append(Document(
                    page_content=desc,
                    metadata={
                        "source": "java_repo", "url": rel, "slug": info["name"],
                        "page_title": repo_name, "content_type": "rule",
                        "is_code_block": False,
                        "code_description": "",
                        "section_heading": f"contract:{info['name']}",
                    },
                ))
                # Contract skeleton (code — like webpage code block)
                all_docs.append(Document(
                    page_content=skeleton,
                    metadata={
                        "source": "java_repo", "url": rel, "slug": info["name"],
                        "page_title": repo_name, "content_type": "example",
                        "is_code_block": True,
                        "code_description": desc,
                        "section_heading": f"contract_skeleton:{info['name']}",
                    },
                ))
            else:
                # Solution description (prose, no code revealed)
                all_docs.append(Document(
                    page_content=desc,
                    metadata={
                        "source": "java_repo", "url": rel, "slug": info["name"],
                        "page_title": repo_name, "content_type": "concept",
                        "is_code_block": False,
                        "code_description": "",
                        "section_heading": f"skeleton:{info['name']}",
                    },
                ))

            print(f"  ✔ [{info['kind']}] {rel}")
        except Exception as e:
            print(f"  ✘ {path.name} — {e}")

    # ── Test files ────────────────────────────────────────────────────────
    print("\n🧪  Processing test files...")
    for path in buckets["test"]:
        try:
            source = path.read_text(errors="replace")
            summary = _summarize_tests(source, path.stem)
            rel = str(path.relative_to(resolved))
            all_docs.append(Document(
                page_content=summary,
                metadata={
                    "source": "java_repo", "url": rel, "slug": path.stem,
                    "page_title": repo_name, "content_type": "rule",
                    "is_code_block": False,
                    "code_description": "",
                    "section_heading": f"test:{path.stem}",
                },
            ))
            print(f"  ✔ {path.name}")
        except Exception as e:
            print(f"  ✘ {path.name} — {e}")

    # ── Config files ──────────────────────────────────────────────────────
    print("\n⚙️  Processing config files...")
    for path in buckets["config"]:
        try:
            content = path.read_text(errors="replace")[:5000]
            rel = str(path.relative_to(resolved))
            all_docs.append(Document(
                page_content=f"# {path.name}\n\n{content}",
                metadata={
                    "source": "java_repo", "url": rel, "slug": path.name,
                    "page_title": repo_name, "content_type": "procedure",
                    "is_code_block": True,
                    "code_description": f"Configuration file: {path.name}",
                    "section_heading": f"config:{path.name}",
                },
            ))
            print(f"  ✔ {path.name}")
        except Exception as e:
            print(f"  ✘ {path.name} — {e}")

    # ── Docs (README, assignments) ────────────────────────────────────────
    if buckets["docs"]:
        print("\n📝  Processing docs...")
        for path in buckets["docs"]:
            content = path.read_text(errors="replace")
            if len(content) < 100:
                continue
            rel = str(path.relative_to(resolved))
            for chunk in _agentic_chunk(content):
                all_docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": "java_repo", "url": rel, "slug": path.stem,
                        "page_title": repo_name, "content_type": "summary",
                        "is_code_block": False,
                        "code_description": "",
                        "section_heading": f"task:{path.name}",
                    },
                ))
            print(f"  ✔ {path.name}")

    # ── Enrich & store ────────────────────────────────────────────────────
    print(f"\n🧠  Enriching {len(all_docs)} chunks...")
    final = _enrich(all_docs, repo_name)

    store(final, type="agentic")
    print(f"\n✅  Stored {len(final)} chunks from '{repo_name}'")

    if tmp_dir:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return final
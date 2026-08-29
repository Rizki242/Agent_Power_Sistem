"""Knowledge Base and Skill Processor.

Converts various document formats (Markdown, PDF, DOCX, JSON, TXT) into
structured knowledge modules (Schema V2) for MCSA AI memory and RAG retrieval.
"""

import io
import json
import os
import re
from typing import Optional

from src.knowledge_retriever import load_knowledge_base


def _slugify(text: str) -> str:
    """Generate a clean slug for file naming and ID."""
    s = re.sub(r"[^A-Za-z0-9_\-\s]", "", str(text or "")).strip()
    return re.sub(r"[\s_]+", "-", s).lower() or "knowledge-doc"


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Normalize excessive spaces and blank lines
    text = re.sub(r"\r\n|\r", "\n", str(text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_markdown_file(content_str: str, default_title: str = "Dokumen Markdown") -> dict:
    """Parse a markdown document (with optional YAML frontmatter) into structured sections."""
    text = _clean_text(content_str)
    title = default_title
    tags = []
    level = "General"
    source = "Knowledge Base Upload"
    language = "id"

    # 1. Parse optional YAML frontmatter (--- ... ---)
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if frontmatter_match:
        fm_content = frontmatter_match.group(1)
        body_text = frontmatter_match.group(2)
        text = body_text

        for line in fm_content.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip().strip("'\"")
                if k == "title" and v:
                    title = v
                elif k == "tags" and v:
                    # Handle comma-separated or json-style array
                    v_clean = v.strip("[]")
                    tags = [t.strip().strip("'\"") for t in v_clean.split(",") if t.strip()]
                elif k in {"level", "skill_level", "difficulty"} and v:
                    level = v
                elif k in {"source", "author", "reference"} and v:
                    source = v
                elif k == "language" and v:
                    language = v

    # 2. Extract first # Heading 1 as title if not specified
    if title == default_title:
        h1_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()

    # 3. Split sections by markdown headings (#, ##, ###, ####)
    sections = []
    heading_pattern = r"(^#{1,4}\s+.+$)"
    chunks = re.split(heading_pattern, text, flags=re.MULTILINE)

    current_heading = "Pengantar"
    current_body = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if re.match(r"^#{1,4}\s+", chunk):
            # If we had previous section, flush it
            if current_body:
                body_str = "\n".join(current_body).strip()
                if body_str:
                    sections.append({
                        "id": _slugify(current_heading),
                        "heading": current_heading,
                        "content": body_str,
                    })
                current_body = []
            # Strip hashes
            current_heading = re.sub(r"^#{1,4}\s+", "", chunk).strip()
        else:
            current_body.append(chunk)

    if current_body:
        body_str = "\n".join(current_body).strip()
        if body_str:
            sections.append({
                "id": _slugify(current_heading),
                "heading": current_heading,
                "content": body_str,
            })

    if not sections and text:
        sections.append({
            "id": "content",
            "heading": "Isi Materi",
            "content": text,
        })

    return {
        "id": _slugify(title),
        "title": title,
        "tags": tags,
        "level": level,
        "source": source,
        "language": language,
        "sections": sections,
    }


def parse_pdf_file(file_bytes: bytes, default_title: str = "Dokumen PDF") -> dict:
    """Extract text from PDF pages and convert to structured knowledge sections."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError(f"Library pypdf belum terinstall: {exc}")

    reader = PdfReader(io.BytesIO(file_bytes))
    sections = []
    title = default_title

    # Try metadata title
    if reader.metadata and reader.metadata.title:
        meta_t = str(reader.metadata.title).strip()
        if meta_t and len(meta_t) > 2:
            title = meta_t

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_text = _clean_text(page.extract_text())
        if not page_text:
            continue

        # Check if first line can serve as a heading
        lines = page_text.splitlines()
        first_line = lines[0].strip() if lines else ""
        if len(first_line) < 60 and not first_line.isdigit() and len(lines) > 1:
            heading = f"Halaman {page_num}: {first_line}"
            content = "\n".join(lines[1:]).strip() or page_text
        else:
            heading = f"Halaman {page_num}"
            content = page_text

        sections.append({
            "id": f"page-{page_num}",
            "heading": heading,
            "content": content,
        })

    if not sections:
        sections.append({
            "id": "page-1",
            "heading": "Halaman 1",
            "content": "Tidak ada teks yang dapat diekstrak dari PDF (kemungkinan berupa scan gambar murni).",
        })

    return {
        "id": _slugify(title),
        "title": title,
        "tags": ["PDF", "Dokumen", "Manual"],
        "level": "General",
        "source": "PDF Upload",
        "language": "id",
        "sections": sections,
    }


def parse_docx_file(file_bytes: bytes, default_title: str = "Dokumen Word") -> dict:
    """Extract headings and paragraphs from DOCX into structured sections."""
    try:
        import docx
    except ImportError as exc:
        raise ImportError(f"Library python-docx belum terinstall: {exc}")

    doc = docx.Document(io.BytesIO(file_bytes))
    sections = []
    current_heading = "Pendahuluan"
    current_paragraphs = []
    title = default_title

    for p in doc.paragraphs:
        p_text = _clean_text(p.text)
        if not p_text:
            continue

        # Detect heading styles or bold short lines
        is_heading = p.style.name.startswith("Heading") or (len(p_text) < 60 and (p_text.isupper() or p_text.endswith(":")))
        if is_heading:
            if current_paragraphs:
                body_str = "\n".join(current_paragraphs).strip()
                if body_str:
                    sections.append({
                        "id": _slugify(current_heading),
                        "heading": current_heading,
                        "content": body_str,
                    })
                current_paragraphs = []
            current_heading = p_text
            if title == default_title:
                title = p_text
        else:
            current_paragraphs.append(p_text)

    if current_paragraphs:
        body_str = "\n".join(current_paragraphs).strip()
        if body_str:
            sections.append({
                "id": _slugify(current_heading),
                "heading": current_heading,
                "content": body_str,
            })

    if not sections:
        sections.append({
            "id": "content",
            "heading": "Isi Dokumen",
            "content": "Tidak ada paragraf teks yang ditemukan dalam file Word.",
        })

    return {
        "id": _slugify(title),
        "title": title,
        "tags": ["Word", "SOP", "Panduan"],
        "level": "General",
        "source": "DOCX Upload",
        "language": "id",
        "sections": sections,
    }


def process_and_save_knowledge_file(
    file_name: str,
    file_bytes: bytes,
    custom_title: Optional[str] = None,
    custom_tags: Optional[list[str]] = None,
    level: str = "General",
    source: str = "",
) -> tuple[bool, str, dict]:
    """Process uploaded file bytes, format into Schema V2 JSON, and save into Materi directory."""
    ext = os.path.splitext(file_name)[1].lower()
    base_name = os.path.splitext(file_name)[0]
    default_title = custom_title.strip() if (custom_title and custom_title.strip()) else base_name.replace("_", " ").title()

    try:
        if ext == ".md":
            content_str = file_bytes.decode("utf-8", errors="ignore")
            doc_data = parse_markdown_file(content_str, default_title=default_title)
        elif ext == ".pdf":
            doc_data = parse_pdf_file(file_bytes, default_title=default_title)
        elif ext == ".docx":
            doc_data = parse_docx_file(file_bytes, default_title=default_title)
        elif ext == ".json":
            content_str = file_bytes.decode("utf-8", errors="ignore")
            raw_json = json.loads(content_str)
            if isinstance(raw_json, dict) and "sections" in raw_json:
                doc_data = raw_json
            elif isinstance(raw_json, list) and all(isinstance(x, dict) for x in raw_json):
                # Convert v1 list of pages to v2 sections
                doc_data = {
                    "id": _slugify(default_title),
                    "title": default_title,
                    "tags": ["JSON", "Materi"],
                    "level": "General",
                    "source": "JSON Upload",
                    "language": "id",
                    "sections": [
                        {
                            "id": f"page-{x.get('page', i+1)}",
                            "heading": f"Halaman {x.get('page', i+1)}",
                            "content": _clean_text(x.get("content")),
                        }
                        for i, x in enumerate(raw_json)
                        if _clean_text(x.get("content"))
                    ],
                }
            else:
                raise ValueError("Format JSON tidak sesuai dengan schema materi (perlu 'sections' atau daftar 'pages').")
        elif ext == ".txt":
            content_str = file_bytes.decode("utf-8", errors="ignore")
            doc_data = parse_markdown_file(content_str, default_title=default_title)
        else:
            return False, f"Format file '{ext}' belum didukung. Gunakan PDF, Markdown (.md), DOCX, JSON, atau TXT.", {}

        # Apply custom overrides
        if custom_title and custom_title.strip():
            doc_data["title"] = custom_title.strip()
            doc_data["id"] = _slugify(custom_title)
        if custom_tags:
            doc_data["tags"] = [str(t).strip() for t in custom_tags if str(t).strip()]
        if level:
            doc_data["level"] = level
        if source:
            doc_data["source"] = source

        # Ensure directory exists
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        materi_dir = os.path.join(root_dir, "Materi")
        os.makedirs(materi_dir, exist_ok=True)

        target_fn = f"{_slugify(doc_data['title'])}.json"
        target_path = os.path.join(materi_dir, target_fn)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)

        # Trigger hot-reload of active knowledge base index
        load_knowledge_base(force_reload=True)

        total_sections = len(doc_data.get("sections", []))
        return (
            True,
            f"Berhasil memproses '{file_name}' menjadi {total_sections} bagian memori dan disimpan sebagai '{target_fn}'.",
            doc_data,
        )

    except Exception as exc:
        return False, f"Gagal memproses file: {exc}", {}


def delete_knowledge_file(file_name: str) -> tuple[bool, str]:
    """Delete a knowledge base JSON file from Materi folder and refresh index."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materi_dir = os.path.join(root_dir, "Materi")
    target_path = os.path.join(materi_dir, file_name)

    if not os.path.exists(target_path):
        return False, f"File '{file_name}' tidak ditemukan di folder Materi."

    try:
        os.remove(target_path)
        # Refresh active index
        load_knowledge_base(force_reload=True)
        return True, f"File '{file_name}' berhasil dihapus dari memori Knowledge Base."
    except Exception as exc:
        return False, f"Gagal menghapus file: {exc}"

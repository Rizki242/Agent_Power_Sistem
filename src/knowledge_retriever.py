"""Knowledge Base Indexer and Retriever for MCSA Technical Standards and Training Materials.

Provides lightweight, dependency-free semantic and keyword search across
SOPs, manuals, diagnostic guidelines, and threshold configurations.
"""

import json
import os
import re
from typing import Optional


_KNOWLEDGE_CACHE = None


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Normalize whitespace
    return re.sub(r"\s+", " ", str(text)).strip()


def _tokenize(text: str) -> list[str]:
    # Extract lowercase alphanumeric words
    return [w.lower() for w in re.findall(r"[A-Za-z0-9_/%+\-\.]{2,}", text) if len(w) > 1]


def load_knowledge_base(force_reload: bool = False) -> list[dict]:
    """Load all training materials and config guidance into memory as searchable chunks."""
    global _KNOWLEDGE_CACHE
    if _KNOWLEDGE_CACHE is not None and not force_reload:
        return _KNOWLEDGE_CACHE

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materi_dir = os.path.join(root_dir, "Materi")
    config_dir = os.path.join(root_dir, "data", "config")

    documents = []

    # 1. Index Materi folder (.json files)
    if os.path.exists(materi_dir):
        for fn in sorted(os.listdir(materi_dir)):
            if not fn.lower().endswith(".json"):
                continue
            path = os.path.join(materi_dir, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                source_name = os.path.splitext(fn)[0]

                # Schema V2 (dict with 'sections')
                if isinstance(data, dict) and isinstance(data.get("sections"), list):
                    title = data.get("title") or source_name
                    tags = " ".join(data.get("tags") or [])
                    for s in data["sections"]:
                        if not isinstance(s, dict):
                            continue
                        heading = s.get("heading") or s.get("title") or "Section"
                        content = _clean_text(s.get("content"))
                        if content:
                            documents.append({
                                "source": source_name,
                                "title": title,
                                "heading": heading,
                                "tags": tags,
                                "content": content,
                                "search_blob": f"{title} {tags} {heading} {content}".lower(),
                            })

                # Schema V2 array (list of dicts with 'sections')
                elif isinstance(data, list) and any(isinstance(x, dict) and isinstance(x.get("sections"), list) for x in data):
                    for doc in data:
                        if not isinstance(doc, dict):
                            continue
                        title = doc.get("title") or source_name
                        tags = " ".join(doc.get("tags") or [])
                        for s in doc.get("sections", []):
                            if not isinstance(s, dict):
                                continue
                            heading = s.get("heading") or s.get("title") or "Section"
                            content = _clean_text(s.get("content"))
                            if content:
                                documents.append({
                                    "source": source_name,
                                    "title": title,
                                    "heading": heading,
                                    "tags": tags,
                                    "content": content,
                                    "search_blob": f"{title} {tags} {heading} {content}".lower(),
                                })

                # Schema V1 (list of pages or dict with 'pages')
                elif isinstance(data, list) and all(isinstance(x, dict) for x in data):
                    for item in data:
                        pg = item.get("page", 1)
                        content = _clean_text(item.get("content"))
                        if content:
                            documents.append({
                                "source": source_name,
                                "title": source_name,
                                "heading": f"Halaman {pg}",
                                "tags": "SOP Manual Training",
                                "content": content,
                                "search_blob": f"{source_name} Halaman {pg} {content}".lower(),
                            })

            except Exception:
                continue

    # 2. Index Guidance & Standards from data/config/
    if os.path.exists(config_dir):
        guidance_path = os.path.join(config_dir, "esa_mcsa_guidance.json")
        if os.path.exists(guidance_path):
            try:
                with open(guidance_path, "r", encoding="utf-8") as f:
                    gdata = json.load(f)
                for cat, val in gdata.items():
                    if isinstance(val, dict):
                        for subk, recs in val.items():
                            if isinstance(recs, list) and recs:
                                content = " ".join(recs)
                                documents.append({
                                    "source": "ESA/MCSA International Guidance",
                                    "title": f"Panduan Diagnostik: {cat.replace('_', ' ').title()}",
                                    "heading": f"Kategori: {subk.upper()}",
                                    "tags": f"ESA MCSA Guidance {cat} {subk}",
                                    "content": content,
                                    "search_blob": f"ESA MCSA Guidance {cat} {subk} {content}".lower(),
                                })
            except Exception:
                pass

        threshold_path = os.path.join(config_dir, "thresholds_default.json")
        if os.path.exists(threshold_path):
            try:
                with open(threshold_path, "r", encoding="utf-8") as f:
                    tdata = json.load(f)
                t_lines = []
                for k, v in tdata.items():
                    t_lines.append(f"- {k}: {v}")
                if t_lines:
                    t_content = "Ambang Batas Alarm/High Standar:\n" + "\n".join(t_lines)
                    documents.append({
                        "source": "Thresholds Standard MCSA",
                        "title": "Batas Nilai Parameter (Thresholds)",
                        "heading": "Standard Alarm & High",
                        "tags": "Threshold Alarm High Limit NEMA IEEE ISO",
                        "content": t_content,
                        "search_blob": f"Thresholds Standard Alarm High {t_content}".lower(),
                    })
            except Exception:
                pass

    _KNOWLEDGE_CACHE = documents
    return _KNOWLEDGE_CACHE


def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """Search knowledge base using keyword relevance scoring."""
    docs = load_knowledge_base()
    if not docs or not query:
        return []

    q = query.lower().strip()
    q_tokens = _tokenize(q)
    if not q_tokens:
        return []

    # Common Indonesian / English stop words to de-emphasize
    stop_words = {"yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "pada", "adalah", "apa", "bagaimana", "cara", "the", "and", "in", "of", "to", "is", "motor", "equipment"}

    meaningful_tokens = [t for t in q_tokens if t not in stop_words] or q_tokens

    scored_docs = []
    for doc in docs:
        blob = doc["search_blob"]
        score = 0.0

        # Exact phrase match in blob
        if len(q) > 4 and q in blob:
            score += 15.0

        # Title / Heading matching has higher weight
        title_lower = doc["title"].lower()
        heading_lower = doc["heading"].lower()
        tags_lower = doc["tags"].lower()

        for token in meaningful_tokens:
            count = blob.count(token)
            if count > 0:
                score += min(count, 5) * 1.5
            if token in title_lower:
                score += 4.0
            if token in heading_lower:
                score += 3.0
            if token in tags_lower:
                score += 2.5

        if score > 0:
            scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)

    results = []
    seen_content = set()
    for score, doc in scored_docs:
        # Avoid duplicate content chunks
        snippet = doc["content"][:100]
        if snippet in seen_content:
            continue
        seen_content.add(snippet)

        res = dict(doc)
        res["score"] = score
        results.append(res)
        if len(results) >= top_k:
            break

    return results


def build_knowledge_context(query: str, max_items: int = 3, max_chars: int = 2500, use_rag: bool = True) -> tuple[str, list[dict]]:
    """Build a context string for LLM prompting and list of citations for the UI.
    
    If use_rag=True and RAG engine is available, uses semantic search (LangChain + FAISS).
    Falls back to keyword search if RAG is not available.
    """
    if use_rag:
        try:
            from src.rag_engine import rag_build_context, is_rag_available
            if is_rag_available():
                context_str, citations = rag_build_context(query, max_items=max_items, max_chars=max_chars)
                if context_str:
                    return context_str, citations
        except Exception:
            pass

    matches = search_knowledge_base(query, top_k=max_items)
    if not matches:
        return "", []

    lines = []
    total_len = 0
    citations = []

    for item in matches:
        chunk_header = f"[{item['source']} — {item['title']} / {item['heading']}]"
        chunk_text = f"{chunk_header}\n{item['content']}"

        if total_len + len(chunk_text) > max_chars and lines:
            break

        lines.append(chunk_text)
        total_len += len(chunk_text)
        citations.append({
            "source": item["source"],
            "title": item["title"],
            "heading": item["heading"],
            "preview": item["content"][:200] + ("..." if len(item["content"]) > 200 else ""),
        })

    context_str = "\n\n".join(lines)
    return context_str, citations

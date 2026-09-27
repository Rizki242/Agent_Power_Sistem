"""RAG (Retrieval Augmented Generation) Engine using LangChain.

Provides semantic search over VIBRASI and TRIBOLOGY knowledge base documents
using embeddings and FAISS vector store.
"""

import hashlib
import json
import os
import re
from typing import Optional


RAG_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rag_index")
RAG_DOCS_CACHE_FILE = os.path.join(RAG_INDEX_DIR, "parsed_docs.json")

_RAG_ENGINE = None


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r"\r\n|\r", "\n", str(text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _get_materi_subdirs() -> list[str]:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materi_dir = os.path.join(root_dir, "Materi")
    subdirs = []
    if os.path.isdir(materi_dir):
        for item in sorted(os.listdir(materi_dir)):
            path = os.path.join(materi_dir, item)
            if os.path.isdir(path) and not item.startswith(".") and item != "__pycache__":
                subdirs.append(path)
    return subdirs


def _load_markdown_files() -> list[dict]:
    documents = []
    for subdir in _get_materi_subdirs():
        for root, _, files in os.walk(subdir):
            for fn in files:
                if fn.lower().endswith(".md"):
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if _clean_text(content):
                            documents.append({
                                "source": os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "title": os.path.splitext(fn)[0].replace("_", " ").title(),
                                "content": _clean_text(content),
                                "type": "markdown",
                            })
                    except Exception:
                        continue
    return documents


def _load_json_knowledge_files() -> list[dict]:
    documents = []
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materi_dir = os.path.join(root_dir, "Materi")
    if not os.path.isdir(materi_dir):
        return documents

    # Scan both root Materi and all subdirectories
    search_dirs = [materi_dir] + _get_materi_subdirs()
    seen_paths = set()

    for s_dir in search_dirs:
        for fn in sorted(os.listdir(s_dir)):
            if not fn.lower().endswith(".json"):
                continue
            path = os.path.join(s_dir, fn)
            if path in seen_paths or not os.path.isfile(path):
                continue
            seen_paths.add(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                source_name = os.path.splitext(fn)[0]
                rel_src = os.path.relpath(path, root_dir)
                if isinstance(data, dict) and isinstance(data.get("sections"), list):
                    title = data.get("title") or source_name
                    for s in data["sections"]:
                        if not isinstance(s, dict):
                            continue
                        content = _clean_text(s.get("content"))
                        if content:
                            heading = s.get("heading") or "Section"
                            documents.append({
                                "source": rel_src,
                                "title": title,
                                "heading": heading,
                                "content": content,
                                "type": "json",
                            })
                elif isinstance(data, list) and all(isinstance(x, dict) for x in data):
                    for item in data:
                        content = _clean_text(item.get("content"))
                        if content:
                            pg = item.get("page", 1)
                            documents.append({
                                "source": rel_src,
                                "title": source_name,
                                "heading": f"Halaman {pg}",
                                "content": content,
                                "type": "json",
                            })
            except Exception:
                continue
    return documents


_RAW_DOCS_CACHE: Optional[list[dict]] = None
_CHUNKS_CACHE: Optional[list[dict]] = None


def clear_rag_cache():
    """Clear memory cache of parsed documents and chunks."""
    global _RAW_DOCS_CACHE, _CHUNKS_CACHE
    _RAW_DOCS_CACHE = None
    _CHUNKS_CACHE = None


def _materi_fingerprint() -> str:
    """Sidik jari seluruh berkas sumber Materi (path relatif + ukuran + mtime).

    Dipakai untuk memutuskan apakah cache hasil parsing di disk masih sahih. Hanya
    `os.stat` per berkas, jadi jauh lebih murah daripada mem-parse ulang ratusan PDF.
    Sengaja mencakup semua .md/.json/.pdf di bawah Materi - superset dari yang benar-benar
    dimuat - supaya kesalahan selalu condong ke "rebuild tak perlu", bukan "cache basi".
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materi_dir = os.path.join(root_dir, "Materi")
    entries = []
    for root, _, files in os.walk(materi_dir):
        for fn in files:
            if not fn.lower().endswith((".md", ".json", ".pdf")):
                continue
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            entries.append(f"{os.path.relpath(path, root_dir)}|{st.st_size}|{st.st_mtime_ns}")
    entries.sort()
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    return f"{len(entries)}:{digest}"


def _read_docs_cache(fingerprint: str) -> Optional[list[dict]]:
    """Baca cache dokumen hasil parsing bila sidik jarinya masih cocok, selain itu None."""
    try:
        with open(RAG_DOCS_CACHE_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("fingerprint") != fingerprint:
        return None
    docs = payload.get("docs")
    return docs if isinstance(docs, list) else None


def _write_docs_cache(docs: list[dict], fingerprint: str) -> None:
    """Tulis cache dokumen secara atomik. Fail-open: cache hanya percepatan, jadi
    direktori yang read-only tidak boleh membuat RAG gagal - cukup dilaporkan."""
    tmp_path = f"{RAG_DOCS_CACHE_FILE}.tmp"
    try:
        os.makedirs(RAG_INDEX_DIR, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"fingerprint": fingerprint, "docs": docs}, f, ensure_ascii=False)
        os.replace(tmp_path, RAG_DOCS_CACHE_FILE)
    except (OSError, ValueError) as exc:
        print(f"[RAG] Gagal menulis cache dokumen: {exc}")
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _load_pdf_files() -> list[dict]:
    documents = []
    try:
        from pypdf import PdfReader
    except ImportError:
        return documents
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    for subdir in _get_materi_subdirs():
        for root, _, files in os.walk(subdir):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    path = os.path.join(root, fn)
                    try:
                        reader = PdfReader(path)
                        title = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").title()
                        all_text = []
                        # Read up to 50 pages per PDF to keep indexing performant
                        for page in reader.pages[:50]:
                            t = _clean_text(page.extract_text() or "")
                            if t:
                                all_text.append(t)
                        if all_text:
                            documents.append({
                                "source": os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "title": title,
                                "content": "\n\n".join(all_text),
                                "type": "pdf",
                            })
                    except Exception:
                        continue
    return documents


def _load_all_documents(force_reload: bool = False) -> list[dict]:
    """Muat seluruh dokumen Materi, berurutan: cache memori -> cache disk -> parse ulang.

    Parsing penuh berarti membaca ratusan PDF dengan pypdf dan memakan waktu beberapa menit,
    dan cache memori saja tidak menolong karena hilang tiap proses restart (deploy, reload dev
    server, dan tiap worker uvicorn membayarnya sendiri). Karena itu hasilnya dipersist ke
    `data/rag_index/parsed_docs.json` - direktori artefak build yang sudah gitignored.
    """
    global _RAW_DOCS_CACHE
    if _RAW_DOCS_CACHE is not None and not force_reload:
        return _RAW_DOCS_CACHE

    fingerprint = _materi_fingerprint()
    if not force_reload:
        cached = _read_docs_cache(fingerprint)
        if cached is not None:
            _RAW_DOCS_CACHE = cached
            return cached

    docs = []
    docs.extend(_load_markdown_files())
    docs.extend(_load_json_knowledge_files())
    docs.extend(_load_pdf_files())
    _RAW_DOCS_CACHE = docs
    _write_docs_cache(docs, fingerprint)
    return docs


def _chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - chunk_overlap
    return chunks


def _create_documents_with_metadata(raw_docs: list[dict], force_reload: bool = False) -> list[dict]:
    global _CHUNKS_CACHE
    if _CHUNKS_CACHE is not None and not force_reload:
        return _CHUNKS_CACHE

    langchain_docs = []
    for doc in raw_docs:
        content = doc.get("content", "")
        if not content:
            continue
        chunks = _chunk_text(content, chunk_size=1000, chunk_overlap=200)
        for i, chunk in enumerate(chunks):
            langchain_docs.append({
                "page_content": chunk,
                "metadata": {
                    "source": doc.get("source", ""),
                    "title": doc.get("title", ""),
                    "heading": doc.get("heading", ""),
                    "chunk_index": i,
                    "type": doc.get("type", ""),
                },
            })
    _CHUNKS_CACHE = langchain_docs
    return langchain_docs


class RAGEngine:
    """LangChain-based RAG engine with FAISS vector store."""

    def __init__(self, index_dir: Optional[str] = None):
        self.index_dir = index_dir or RAG_INDEX_DIR
        self.vectorstore = None
        self.embeddings = None
        self._initialized = False

    def _get_embeddings(self):
        if self.embeddings is not None:
            return self.embeddings
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            # First try local cache to avoid network hang on offline/sandboxed environments
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    model_kwargs={"device": "cpu", "local_files_only": True},
                    encode_kwargs={"normalize_embeddings": True},
                )
                return self.embeddings
            except Exception:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                return self.embeddings
        except Exception:
            try:
                from langchain_community.embeddings import GeminiEmbeddings
                from src.llm_assistant import resolve_provider_key
                api_key = resolve_provider_key("gemini")
                if api_key:
                    self.embeddings = GeminiEmbeddings(
                        google_api_key=api_key,
                        model="models/embedding-001",
                    )
                    return self.embeddings
            except Exception:
                pass
        return None

    def build_index(self, force: bool = False) -> tuple[bool, str]:
        if os.path.exists(os.path.join(self.index_dir, "index.faiss")) and not force:
            return self.load_index()

        try:
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
        except ImportError as exc:
            return False, f"LangChain/FAISS belum terinstall: {exc}. Jalankan: pip install langchain langchain-community faiss-cpu sentence-transformers"

        embeddings = self._get_embeddings()
        if embeddings is None:
            return False, "Embeddings model tidak tersedia. Install sentence-transformers atau set GEMINI_API_KEY."

        raw_docs = _load_all_documents()
        if not raw_docs:
            return False, "Tidak ada dokumen ditemukan di folder VIBRASI dan TRIBOLOGY."

        lc_docs = _create_documents_with_metadata(raw_docs)
        if not lc_docs:
            return False, "Gagal membuat chunk dari dokumen."

        documents = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in lc_docs]

        try:
            self.vectorstore = FAISS.from_documents(documents, embeddings)
            os.makedirs(self.index_dir, exist_ok=True)
            self.vectorstore.save_local(self.index_dir)
            self._initialized = True
            return True, f"Index RAG berhasil dibuat: {len(documents)} chunks dari {len(raw_docs)} dokumen."
        except Exception as exc:
            return False, f"Gagal membuat index FAISS: {exc}"

    def load_index(self) -> tuple[bool, str]:
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError as exc:
            return False, f"LangChain/FAISS belum terinstall: {exc}"

        embeddings = self._get_embeddings()
        if embeddings is None:
            return False, "Embeddings model tidak tersedia."

        index_path = os.path.join(self.index_dir, "index.faiss")
        if not os.path.exists(index_path):
            return False, "Index RAG belum dibuat. Jalankan build_index() terlebih dahulu."

        try:
            self.vectorstore = FAISS.load_local(self.index_dir, embeddings, allow_dangerous_deserialization=True)
            self._initialized = True
            return True, f"Index RAG berhasil dimuat dari {self.index_dir}."
        except Exception as exc:
            return False, f"Gagal memuat index FAISS: {exc}"

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if not self._initialized:
            ok, msg = self.load_index()
            if not ok:
                return []

        if self.vectorstore is None:
            return []

        try:
            results = self.vectorstore.similarity_search(query, k=top_k)
            output = []
            for doc in results:
                output.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", ""),
                    "title": doc.metadata.get("title", ""),
                    "heading": doc.metadata.get("heading", ""),
                    "score": 0.0,
                })
            return output
        except Exception:
            return []

    def search_with_scores(self, query: str, top_k: int = 4) -> list[dict]:
        if not self._initialized:
            ok, msg = self.load_index()
            if not ok:
                return []

        if self.vectorstore is None:
            return []

        try:
            embeddings = self._get_embeddings()
            query_embedding = embeddings.embed_query(query)
            results = self.vectorstore.similarity_search_by_vector(query_embedding, k=top_k)

            import numpy as np
            doc_embeddings = self.vectorstore.index.reconstruct_n(0, self.vectorstore.index.ntotal)
            indices = self.vectorstore.index_to_docstore_id

            output = []
            for doc in results:
                doc_id = None
                for idx_id, doc_id_candidate in indices.items():
                    if self.vectorstore.docstore.search(doc_id_candidate).page_content == doc.page_content:
                        doc_id = idx_id
                        break
                score = 0.0
                if doc_id is not None and doc_id < len(doc_embeddings):
                    similarity = np.dot(query_embedding, doc_embeddings[doc_id])
                    score = float(similarity)
                output.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", ""),
                    "title": doc.metadata.get("title", ""),
                    "heading": doc.metadata.get("heading", ""),
                    "score": score,
                })
            return output
        except Exception:
            return self.search(query, top_k)

    def build_context(self, query: str, max_items: int = 3, max_chars: int = 3000) -> tuple[str, list[dict]]:
        matches = self.search(query, top_k=max_items)
        if not matches:
            return "", []

        lines = []
        total_len = 0
        citations = []

        for item in matches:
            chunk_header = f"[{item['source']} -- {item['title']}]"
            if item.get("heading"):
                chunk_header += f" / {item['heading']}"
            chunk_text = f"{chunk_header}\n{item['content']}"

            if total_len + len(chunk_text) > max_chars and lines:
                break

            lines.append(chunk_text)
            total_len += len(chunk_text)
            citations.append({
                "source": item["source"],
                "title": item["title"],
                "heading": item.get("heading", ""),
                "preview": item["content"][:200] + ("..." if len(item["content"]) > 200 else ""),
            })

        context_str = "\n\n".join(lines)
        return context_str, citations

    def get_metadata(self) -> dict:
        index_file = os.path.join(self.index_dir, "index.faiss")
        index_exists = os.path.exists(index_file)
        index_size_kb = round(os.path.getsize(index_file) / 1024, 1) if index_exists else 0.0
        total_chunks = 0
        if self.vectorstore and hasattr(self.vectorstore, "index") and self.vectorstore.index:
            total_chunks = getattr(self.vectorstore.index, "ntotal", 0)

        subdirs = [os.path.basename(d) for d in _get_materi_subdirs()]

        return {
            "is_available": is_rag_available(),
            "is_ready": self.is_ready,
            "index_exists": index_exists,
            "index_size_kb": index_size_kb,
            "total_chunks": total_chunks,
            "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "scanned_directories": subdirs,
        }

    def inspect_chunks(self, source_filter: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict:
        """Returns parsed document chunks with metadata for UI inspection and debugging."""
        all_chunks = []
        raw_docs = _load_all_documents()
        langchain_docs = _create_documents_with_metadata(raw_docs)

        for i, doc in enumerate(langchain_docs):
            src = doc.get("metadata", {}).get("source", "")
            if source_filter and source_filter.lower() not in src.lower():
                continue
            all_chunks.append({
                "chunk_id": f"chunk-{i}",
                "source": src,
                "title": doc.get("metadata", {}).get("title", ""),
                "heading": doc.get("metadata", {}).get("heading", ""),
                "chunk_index": doc.get("metadata", {}).get("chunk_index", 0),
                "type": doc.get("metadata", {}).get("type", ""),
                "content": doc.get("page_content", ""),
                "char_length": len(doc.get("page_content", "")),
            })

        total = len(all_chunks)
        paginated = all_chunks[offset : offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "chunks": paginated,
        }

    @property
    def is_ready(self) -> bool:
        return self._initialized and self.vectorstore is not None


def get_rag_engine() -> RAGEngine:
    global _RAG_ENGINE
    if _RAG_ENGINE is None:
        _RAG_ENGINE = RAGEngine()
    return _RAG_ENGINE


def rag_search(query: str, top_k: int = 4) -> list[dict]:
    engine = get_rag_engine()
    if not engine.is_ready:
        ok, _ = engine.load_index()
        if not ok:
            return []
    return engine.search(query, top_k=top_k)


def rag_build_context(query: str, max_items: int = 3, max_chars: int = 3000) -> tuple[str, list[dict]]:
    engine = get_rag_engine()
    if not engine.is_ready:
        ok, _ = engine.load_index()
        if not ok:
            return "", []
    return engine.build_context(query, max_items=max_items, max_chars=max_chars)


def is_rag_available() -> bool:
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return True
    except ImportError:
        return False


def rag_get_metadata() -> dict:
    engine = get_rag_engine()
    if not engine.is_ready and os.path.exists(os.path.join(engine.index_dir, "index.faiss")):
        engine.load_index()
    return engine.get_metadata()


def rag_inspect_chunks(source_filter: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict:
    engine = get_rag_engine()
    return engine.inspect_chunks(source_filter=source_filter, limit=limit, offset=offset)

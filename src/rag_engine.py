"""RAG (Retrieval Augmented Generation) Engine using LangChain.

Provides semantic search over VIBRASI and TRIBOLOGY knowledge base documents
using embeddings and FAISS vector store.
"""

import json
import os
import re
from typing import Optional


RAG_INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rag_index")

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
    for name in ["VIBRASI", "TRIBOLOGY"]:
        path = os.path.join(materi_dir, name)
        if os.path.isdir(path):
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
    for fn in sorted(os.listdir(materi_dir)):
        if not fn.lower().endswith(".json"):
            continue
        path = os.path.join(materi_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            source_name = os.path.splitext(fn)[0]
            if isinstance(data, dict) and isinstance(data.get("sections"), list):
                title = data.get("title") or source_name
                for s in data["sections"]:
                    if not isinstance(s, dict):
                        continue
                    content = _clean_text(s.get("content"))
                    if content:
                        heading = s.get("heading") or "Section"
                        documents.append({
                            "source": fn,
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
                            "source": fn,
                            "title": source_name,
                            "heading": f"Halaman {pg}",
                            "content": content,
                            "type": "json",
                        })
        except Exception:
            continue
    return documents


def _load_pdf_files() -> list[dict]:
    documents = []
    try:
        from pypdf import PdfReader
    except ImportError:
        return documents
    import io
    for subdir in _get_materi_subdirs():
        for root, _, files in os.walk(subdir):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    path = os.path.join(root, fn)
                    try:
                        reader = PdfReader(path)
                        title = os.path.splitext(fn)[0].replace("_", " ").replace("-", " ").title()
                        all_text = []
                        for page in reader.pages:
                            t = _clean_text(page.extract_text())
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


def _load_all_documents() -> list[dict]:
    docs = []
    docs.extend(_load_markdown_files())
    docs.extend(_load_json_knowledge_files())
    docs.extend(_load_pdf_files())
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


def _create_documents_with_metadata(raw_docs: list[dict]) -> list[dict]:
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
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            return self.embeddings
        except ImportError:
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

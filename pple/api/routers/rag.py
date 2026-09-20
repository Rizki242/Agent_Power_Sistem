"""RAG (Retrieval Augmented Generation) Knowledge Router for FastAPI."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.rag_engine import (
    get_rag_engine,
    is_rag_available,
    rag_build_context,
    rag_get_metadata,
    rag_inspect_chunks,
    rag_search,
)
from src.knowledge_retriever import search_knowledge_base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Pertanyaan atau kueri pencarian semantik")
    top_k: int = Field(default=5, ge=1, le=20, description="Jumlah potongan chunk yang diambil")


class RAGRebuildRequest(BaseModel):
    force: bool = Field(default=True, description="Paksa rebuild index FAISS dari awal")


@router.get("/status")
def get_rag_status() -> Dict[str, Any]:
    """Mengembalikan status kesiapan RAG, vector store FAISS, dan metadata chunk."""
    try:
        meta = rag_get_metadata()
        return {"status": "ok", "data": meta}
    except Exception as exc:
        logger.warning(f"Error getting RAG metadata: {exc}")
        return {
            "status": "warning",
            "data": {
                "is_available": is_rag_available(),
                "is_ready": False,
                "index_exists": False,
                "error": str(exc),
            },
        }


@router.post("/search")
def search_rag_chunks(payload: RAGSearchRequest = Body(...)) -> Dict[str, Any]:
    """Melakukan pencarian semantik terhadap potongan chunk dokumen menggunakan FAISS,
    dengan fallback otomatis ke pencarian kata kunci jika index belum siap."""
    q = payload.query.strip()
    if not q:
        raise HTTPException(status_code=422, detail="Query tidak boleh kosong.")

    engine = get_rag_engine()
    results: List[Dict[str, Any]] = []
    used_engine = "faiss_semantic"

    try:
        results = rag_search(q, top_k=payload.top_k)
    except Exception as exc:
        logger.warning(f"Semantic search failed, falling back to keyword search: {exc}")
        results = []

    # Fallback to keyword chunk matching if FAISS returned empty or is not ready
    if not results:
        used_engine = "keyword_fallback"
        kw_results = search_knowledge_base(q, top_k=payload.top_k)
        for item in kw_results:
            results.append({
                "content": item.get("content") or item.get("text") or item.get("snippet", ""),
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "heading": item.get("heading", ""),
                "score": float(item.get("score", 0.0)),
            })

    return {
        "status": "ok",
        "query": q,
        "engine": used_engine,
        "count": len(results),
        "results": results,
    }


@router.get("/chunks")
def list_rag_chunks(
    source: Optional[str] = Query(None, description="Filter berdasarkan nama file sumber"),
    limit: int = Query(50, ge=1, le=200, description="Maksimum chunk yang ditampilkan"),
    offset: int = Query(0, ge=0, description="Offset pagination"),
) -> Dict[str, Any]:
    """Mengembalikan daftar potongan teks (chunks) dari dokumen yang telah dipecah
    beserta informasi metadata untuk diinspeksi pengguna di React."""
    try:
        data = rag_inspect_chunks(source_filter=source, limit=limit, offset=offset)
        return {"status": "ok", "data": data}
    except Exception as exc:
        logger.error(f"Error inspecting RAG chunks: {exc}")
        raise HTTPException(status_code=500, detail=f"Gagal membaca chunks dokumen: {exc}")


@router.post("/rebuild")
def rebuild_rag_index(payload: Optional[RAGRebuildRequest] = Body(None)) -> Dict[str, Any]:
    """Membangun ulang index vector store FAISS dari seluruh dokumen Materi/."""
    force = payload.force if payload else True
    engine = get_rag_engine()

    if not is_rag_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Package RAG (langchain, faiss-cpu, sentence-transformers) belum terpasang di sistem.",
        )

    try:
        success, message = engine.build_index(force=force)
        meta = engine.get_metadata()
        if not success:
            raise HTTPException(status_code=500, detail=message)
        return {
            "status": "ok",
            "message": message,
            "metadata": meta,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to build RAG index: {exc}")
        raise HTTPException(status_code=500, detail=f"Gagal membangun index RAG: {exc}")


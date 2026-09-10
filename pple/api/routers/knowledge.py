"""Knowledge / Materi API router."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from src.knowledge_retriever import search_knowledge_base

router = APIRouter(prefix="/api", tags=["knowledge"])


class MateriSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


@router.get("/materi")
def get_materi_list():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    materi_dir = os.path.join(base_dir, "Materi")
    files = []
    if os.path.exists(materi_dir):
        files = sorted([f for f in os.listdir(materi_dir) if f.lower().endswith(".json")])
    materi = [
        {
            "id": os.path.splitext(f)[0],
            "filename": f,
            "title": os.path.splitext(f)[0].replace("-", " ").replace("_", " ").title(),
            "level": "General",
            "tags": [],
        }
        for f in files
    ]
    return {"materials": files, "materi": materi}


@router.post("/materi/search")
async def search_materi(
    payload: Optional[MateriSearchRequest] = Body(None),
    query: Optional[str] = Query(None, min_length=1),
):
    query_text = (payload.query if payload is not None else query) or ""
    query_text = query_text.strip()
    if not query_text:
        raise HTTPException(status_code=422, detail="query is required")
    results = search_knowledge_base(query_text, top_k=5)
    return {"results": results, "query": query_text}

"""Knowledge / Materi API router."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from src.knowledge_processor import process_and_save_knowledge_file
from src.knowledge_retriever import materi_dir, search_knowledge_base

router = APIRouter(prefix="/api", tags=["knowledge"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".md", ".docx", ".json", ".txt"}


class MateriSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class UploadedDocument(BaseModel):
    id: str
    title: str
    filename: str
    section_count: int = Field(ge=0)
    tags: List[str] = Field(default_factory=list)
    level: str


class MateriUploadResponse(BaseModel):
    message: str
    document: UploadedDocument


@router.get("/materi")
def get_materi_list():
    directory = materi_dir()
    files = []
    if os.path.exists(directory):
        files = sorted([f for f in os.listdir(directory) if f.lower().endswith(".json")])
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


@router.post(
    "/materi/upload",
    response_model=MateriUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_materi(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: str = Form(""),
    level: str = Form("General"),
):
    """Process one document through the shared knowledge pipeline."""
    filename = os.path.basename(file.filename or "")
    extension = os.path.splitext(filename)[1].lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PDF, MD, DOCX, JSON, atau TXT.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Ukuran file melebihi batas 20 MB.",
        )

    parsed_tags = [item.strip() for item in tags.split(",") if item.strip()]
    success, message, document = process_and_save_knowledge_file(
        file_name=filename,
        file_bytes=content,
        custom_title=title,
        custom_tags=parsed_tags,
        level=level,
        source="API Upload",
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    output_filename = f"{document.get('id', 'knowledge-doc')}.json"
    return {
        "message": message,
        "document": {
            "id": document.get("id", ""),
            "title": document.get("title", title or filename),
            "filename": output_filename,
            "section_count": len(document.get("sections", [])),
            "tags": document.get("tags", parsed_tags),
            "level": document.get("level", level),
        },
    }

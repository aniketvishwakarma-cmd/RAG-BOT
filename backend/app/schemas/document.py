from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChunkSchema(BaseModel):
    id: str
    document_id: str
    content: str
    source_layer: str
    section_no: Optional[str] = None
    clause_no: Optional[str] = None
    paragraph_no: Optional[str] = None
    page_no: Optional[int] = None
    heading: Optional[str] = None
    priority_rank: int
    token_count: int

    class Config:
        from_attributes = True


class DocumentSchema(BaseModel):
    id: str
    title: str
    source_layer: str
    regulator: Optional[str] = None
    document_type: Optional[str] = None
    effective_date: Optional[datetime] = None
    version: str
    source_url: Optional[str] = None
    file_path: Optional[str] = None
    is_active: bool
    is_superseded: bool
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str
    chunk_count: int
    status: str = "processed"


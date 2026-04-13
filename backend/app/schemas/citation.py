from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CitationCard(BaseModel):
    source_name: str
    source_layer: str
    layer_priority: int
    section_no: Optional[str] = None
    clause_no: Optional[str] = None
    paragraph_no: Optional[str] = None
    page_no: Optional[int] = None
    excerpt: str = Field(..., max_length=300)
    relevance_score: float


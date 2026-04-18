from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.citation import CitationCard


class DocumentLayer(str, Enum):
    RBI_MASTER = "RBI_MASTER"
    CICRA = "CICRA"
    RBI_CIRCULAR = "RBI_CIRCULAR"
    SOP = "SOP"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)
    layer_filter: Optional[List[DocumentLayer]] = None
    bypass_cache: bool = False
    include_graph_context: bool = False


class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    key_facts: List[str] = Field(default_factory=list)
    confidence: float
    resolution_note: str = ""
    citations: List[CitationCard] = Field(default_factory=list)
    requires_human_review: bool = False
    latency_ms: int
    layer_sources_used: List[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    citation_mismatch: bool = False
    citation_warning: Optional[str] = None
    source_relevance_score: Optional[float] = None
    source_relevance_warning: Optional[str] = None
    grounding_score: Optional[float] = None


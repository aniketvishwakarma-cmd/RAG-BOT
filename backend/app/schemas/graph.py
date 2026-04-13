from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    node_type: str
    label: str
    layer: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


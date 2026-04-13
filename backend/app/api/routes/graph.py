from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.graph.knowledge_graph import RegulatoryKnowledgeGraph

router = APIRouter()


@router.get("/relations")
async def get_graph_relations(limit: int = 100, db: Session = Depends(get_db)):
    return RegulatoryKnowledgeGraph(db).export_subgraph(limit=limit)


@router.get("/lineage/{document_id}")
async def get_document_lineage(document_id: str, db: Session = Depends(get_db)):
    return RegulatoryKnowledgeGraph(db).get_document_lineage(document_id)


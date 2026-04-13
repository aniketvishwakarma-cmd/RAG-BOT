from __future__ import annotations

from typing import Dict, List

import networkx as nx
import structlog
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document, GraphRelation

logger = structlog.get_logger()


class RegulatoryKnowledgeGraph:
    def __init__(self, db: Session):
        self.db = db
        self.graph = nx.DiGraph()
        self._load_from_db()

    def _load_from_db(self) -> None:
        for doc in self.db.query(Document).filter(Document.is_active.is_(True)).all():
            self.add_document_node(doc)

        for chunk in self.db.query(Chunk).filter(Chunk.is_superseded.is_(False)).all():
            self.graph.add_node(
                chunk.id,
                node_type="chunk",
                label=chunk.heading or chunk.section_no or chunk.id,
                layer=chunk.source_layer,
                section_no=chunk.section_no,
                clause_no=chunk.clause_no,
                page_no=chunk.page_no,
                document_id=chunk.document_id,
            )
            self.graph.add_edge(
                chunk.document_id,
                chunk.id,
                relation="contains",
                source_type="document",
                target_type="chunk",
                confidence=1.0,
            )

        for rel in self.db.query(GraphRelation).all():
            if rel.source_id not in self.graph:
                self.graph.add_node(rel.source_id, node_type=rel.source_type or "entity", label=rel.source_id)
            if rel.target_id not in self.graph:
                label = (rel.metadata_json or {}).get("label") or rel.target_id
                self.graph.add_node(rel.target_id, node_type=rel.target_type or "entity", label=label)
            self.graph.add_edge(
                rel.source_id,
                rel.target_id,
                relation=rel.relation,
                confidence=rel.confidence,
                source_type=rel.source_type,
                target_type=rel.target_type,
                **(rel.metadata_json or {}),
            )
        logger.info("graph_loaded", nodes=self.graph.number_of_nodes(), edges=self.graph.number_of_edges())

    def add_document_node(self, doc: Document) -> None:
        self.graph.add_node(
            doc.id,
            node_type="document",
            title=doc.title,
            layer=doc.source_layer,
            effective_date=str(doc.effective_date) if doc.effective_date else None,
            is_superseded=doc.is_superseded,
        )

    def add_chunk_node(self, chunk: dict) -> None:
        self.graph.add_node(
            chunk["id"],
            node_type="chunk",
            label=chunk.get("heading") or chunk.get("section_no") or chunk["id"],
            layer=chunk.get("source_layer"),
            section_no=chunk.get("section_no"),
            clause_no=chunk.get("clause_no"),
        )
        if chunk.get("document_id"):
            self.graph.add_edge(
                chunk["document_id"],
                chunk["id"],
                relation="contains",
                source_type="document",
                target_type="chunk",
                confidence=1.0,
            )

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        source_type: str,
        target_type: str,
        relation: str,
        confidence: float = 1.0,
        metadata_json: dict | None = None,
    ) -> None:
        self.graph.add_edge(
            source_id,
            target_id,
            relation=relation,
            confidence=confidence,
            source_type=source_type,
            target_type=target_type,
            **(metadata_json or {}),
        )
        self.db.add(
            GraphRelation(
                source_id=source_id,
                target_id=target_id,
                source_type=source_type,
                target_type=target_type,
                relation=relation,
                confidence=confidence,
                metadata_json=metadata_json or {},
            )
        )
        self.db.commit()

    def add_supersession(self, new_doc_id: str, old_doc_id: str) -> None:
        self.add_relation(
            source_id=new_doc_id,
            target_id=old_doc_id,
            source_type="document",
            target_type="document",
            relation="supersedes",
        )

    def add_clarification(self, circular_id: str, clause_id: str) -> None:
        self.add_relation(
            source_id=circular_id,
            target_id=clause_id,
            source_type="document",
            target_type="chunk",
            relation="clarifies",
            confidence=0.9,
        )

    def get_related_chunks(self, chunk_ids: List[str]) -> List[Dict]:
        related_chunk_ids = set()
        for chunk_id in chunk_ids:
            if chunk_id not in self.graph:
                continue
            related_chunk_ids.update(self.graph.neighbors(chunk_id))
            related_chunk_ids.update(self.graph.predecessors(chunk_id))

        new_ids = related_chunk_ids - set(chunk_ids)
        if not new_ids:
            return []

        chunks = (
            self.db.query(Chunk)
            .filter(Chunk.id.in_(list(new_ids)[:10]), Chunk.is_superseded.is_(False))
            .all()
        )
        return [
            {
                "id": chunk.id,
                "content": chunk.content,
                "source_layer": chunk.source_layer,
                "document_id": chunk.document_id,
                "document_name": chunk.document.title if chunk.document else "",
                "section_no": chunk.section_no,
                "clause_no": chunk.clause_no,
                "paragraph_no": chunk.paragraph_no,
                "page_no": chunk.page_no,
                "heading": chunk.heading,
                "priority_rank": chunk.priority_rank,
                "fused_score": 0.5,
                "from_graph": True,
            }
            for chunk in chunks
        ]

    def get_document_lineage(self, doc_id: str) -> Dict:
        if doc_id not in self.graph:
            return {"doc_id": doc_id, "lineage": []}
        return {
            "doc_id": doc_id,
            "superseded_by": [
                node
                for node in self.graph.predecessors(doc_id)
                if self.graph[node][doc_id].get("relation") == "supersedes"
            ],
            "supersedes": [
                node
                for node in self.graph.successors(doc_id)
                if self.graph[doc_id][node].get("relation") == "supersedes"
            ],
            "clarified_by": [
                node
                for node in self.graph.predecessors(doc_id)
                if self.graph[node][doc_id].get("relation") == "clarifies"
            ],
            "is_active": not self.graph.nodes[doc_id].get("is_superseded", False),
        }

    def detect_conflicts_in_chunks(self, chunk_ids: List[str]) -> List[Dict]:
        conflicts = []
        for index, left in enumerate(chunk_ids):
            for right in chunk_ids[index + 1 :]:
                if self.graph.has_edge(left, right) and self.graph[left][right].get("relation") == "conflicts_with":
                    conflicts.append({"chunk_a": left, "chunk_b": right})
                if self.graph.has_edge(right, left) and self.graph[right][left].get("relation") == "conflicts_with":
                    conflicts.append({"chunk_a": right, "chunk_b": left})
        return conflicts

    def export_subgraph(self, limit: int = 100) -> dict:
        nodes = []
        edges = []
        for node_id, data in list(self.graph.nodes(data=True))[:limit]:
            nodes.append({"id": node_id, **data})
        for source, target, data in list(self.graph.edges(data=True))[:limit]:
            edges.append({"source": source, "target": target, **data})
        return {"nodes": nodes, "edges": edges}

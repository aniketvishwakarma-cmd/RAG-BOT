from __future__ import annotations

from app.graph.knowledge_graph import RegulatoryKnowledgeGraph


class GraphRetriever:
    def __init__(self, knowledge_graph: RegulatoryKnowledgeGraph):
        self.knowledge_graph = knowledge_graph

    def fetch_related(self, chunk_ids: list[str]) -> list[dict]:
        return self.knowledge_graph.get_related_chunks(chunk_ids)


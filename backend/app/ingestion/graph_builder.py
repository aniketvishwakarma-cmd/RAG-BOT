from __future__ import annotations

from app.graph.entity_extractor import EntityExtractor
from app.graph.knowledge_graph import RegulatoryKnowledgeGraph
from app.graph.relation_mapper import RelationMapper


class GraphBuilder:
    def __init__(self, knowledge_graph: RegulatoryKnowledgeGraph):
        self.knowledge_graph = knowledge_graph
        self.entity_extractor = EntityExtractor()
        self.relation_mapper = RelationMapper()

    def build_for_document(self, document_id: str, chunks: list[dict]) -> None:
        for chunk in chunks:
            self.knowledge_graph.add_chunk_node(chunk)
            entities = self.entity_extractor.extract(chunk["content"])
            relations = self.relation_mapper.map_relations(chunk, entities)
            for relation in relations:
                self.knowledge_graph.add_relation(**relation)


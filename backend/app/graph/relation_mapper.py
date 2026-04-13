from __future__ import annotations


class RelationMapper:
    def map_relations(self, chunk: dict, entities: list[dict]) -> list[dict]:
        relations = []
        labels = {entity["label"] for entity in entities}
        if "CONSUMER_PENALTY" in labels:
            relations.append(
                {
                    "source_id": chunk["id"],
                    "target_id": "entity:consumer_penalty",
                    "source_type": "chunk",
                    "target_type": "entity",
                    "relation": "references",
                    "confidence": 0.95,
                    "metadata_json": {"label": "consumer_penalty"},
                }
            )
        if "REGULATOR_PENALTY" in labels:
            relations.append(
                {
                    "source_id": chunk["id"],
                    "target_id": "entity:regulator_penalty",
                    "source_type": "chunk",
                    "target_type": "entity",
                    "relation": "references",
                    "confidence": 0.95,
                    "metadata_json": {"label": "regulator_penalty"},
                }
            )
        return relations


from __future__ import annotations


class Neo4jAdapter:
    def export_nodes(self, *args, **kwargs):
        raise NotImplementedError("Neo4j export is not implemented in the MVP.")

    def export_edges(self, *args, **kwargs):
        raise NotImplementedError("Neo4j export is not implemented in the MVP.")

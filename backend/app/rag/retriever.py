from __future__ import annotations

import math
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Chunk


class VectorRetriever:
    def __init__(self, db: Session):
        self.db = db

    def semantic_search(
        self,
        query_embedding: list[float],
        layer_filter: Optional[list[str]] = None,
        top_k: int = 50,
    ) -> list[dict]:
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            try:
                return self._postgres_vector_search(query_embedding, layer_filter, top_k)
            except Exception:
                pass
        return self._python_fallback(query_embedding, layer_filter, top_k)

    def _postgres_vector_search(
        self,
        embedding: list[float],
        layer_filter: Optional[list[str]],
        top_k: int,
    ) -> list[dict]:
        embedding_str = "[" + ",".join(str(value) for value in embedding) + "]"
        layer_clause = "AND c.source_layer = ANY(:layers)" if layer_filter else ""
        query = text(
            f"""
            SELECT
                c.id, c.content, c.source_layer, c.document_id, c.section_no, c.clause_no,
                c.paragraph_no, c.page_no, c.heading, c.priority_rank, c.token_count,
                d.title AS document_name,
                1 - (c.embedding <=> :embedding) AS similarity_score
            FROM chunks c
            LEFT JOIN documents d ON d.id = c.document_id
            WHERE c.is_superseded = false
            {layer_clause}
            ORDER BY c.embedding <=> :embedding
            LIMIT :top_k
            """
        )
        params = {"embedding": embedding_str, "top_k": top_k}
        if layer_filter:
            params["layers"] = layer_filter
        rows = self.db.execute(query, params).fetchall()
        return [{**dict(row._mapping), "search_type": "vector"} for row in rows]

    def _python_fallback(
        self,
        embedding: list[float],
        layer_filter: Optional[list[str]],
        top_k: int,
    ) -> list[dict]:
        query = self.db.query(Chunk).filter(Chunk.is_superseded.is_(False))
        if layer_filter:
            query = query.filter(Chunk.source_layer.in_(layer_filter))
        chunks = query.all()
        results = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            score = self._cosine_similarity(embedding, list(chunk.embedding))
            results.append(
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
                    "token_count": chunk.token_count,
                    "similarity_score": score,
                    "search_type": "vector",
                }
            )
        results.sort(key=lambda item: item["similarity_score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        dot = sum(left[index] * right[index] for index in range(size))
        left_norm = math.sqrt(sum(value * value for value in left[:size])) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right[:size])) or 1.0
        return dot / (left_norm * right_norm)


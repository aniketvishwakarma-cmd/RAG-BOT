from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Chunk
from app.rag.retriever import VectorRetriever


class HybridSearchEngine:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = VectorRetriever(db)
        self._bm25_index = None
        self._bm25_chunks: list[Chunk] = []
        self._build_bm25_index()

    def _build_bm25_index(self) -> None:
        chunks = self.db.query(Chunk).filter(Chunk.is_superseded.is_(False)).all()
        self._bm25_chunks = chunks
        tokenized = [chunk.bm25_text.split() for chunk in chunks if chunk.bm25_text]
        if tokenized and len(tokenized) == len(chunks):
            self._bm25_index = BM25Okapi(tokenized)

    def search(
        self,
        query_text: str,
        query_embedding: List[float],
        layer_filter: Optional[List[str]] = None,
        top_k: int = 50,
    ) -> List[Dict]:
        vector_results = self.retriever.semantic_search(query_embedding, layer_filter, top_k * 2)
        bm25_results = self._bm25_search(query_text, layer_filter, top_k * 2)
        return self._reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=settings.VECTOR_WEIGHT,
            bm25_weight=settings.BM25_WEIGHT,
            top_k=top_k,
        )

    def _bm25_search(self, query: str, layer_filter: Optional[List[str]], top_k: int) -> List[Dict]:
        if not self._bm25_index or not self._bm25_chunks:
            return []
        scores = self._bm25_index.get_scores(query.lower().split())
        indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in indices:
            score = float(scores[idx])
            if score <= 0:
                break
            chunk = self._bm25_chunks[idx]
            if layer_filter and chunk.source_layer not in layer_filter:
                continue
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
                    "similarity_score": score,
                    "search_type": "bm25",
                }
            )
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        vector_weight: float = 0.70,
        bm25_weight: float = 0.30,
        top_k: int = 50,
        k: int = 60,
    ) -> List[Dict]:
        scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict] = {}
        for rank, chunk in enumerate(vector_results):
            cid = chunk["id"]
            scores[cid] = scores.get(cid, 0.0) + vector_weight * (1.0 / (k + rank + 1))
            chunk_data[cid] = chunk
        for rank, chunk in enumerate(bm25_results):
            cid = chunk["id"]
            scores[cid] = scores.get(cid, 0.0) + bm25_weight * (1.0 / (k + rank + 1))
            chunk_data.setdefault(cid, chunk)
        results = []
        for cid in sorted(scores.keys(), key=lambda item: scores[item], reverse=True)[:top_k]:
            row = dict(chunk_data[cid])
            row["fused_score"] = scores[cid]
            results.append(row)
        return results

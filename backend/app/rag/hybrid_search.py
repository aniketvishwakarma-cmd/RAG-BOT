from __future__ import annotations

import re
from typing import Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Chunk
from app.rag.retriever import VectorRetriever

REGULATORY_TERMS = {
    "21",
    "9",
    "30",
    "100",
    "5000",
    "calendar",
    "day",
    "days",
    "dispute",
    "resolution",
    "timeline",
    "window",
    "credit",
    "institution",
    "information",
    "company",
    "ci",
    "cic",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "is",
    "of",
    "the",
    "to",
    "what",
    "when",
    "with",
}


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
        tokenized = [self._tokenize(chunk.bm25_text or chunk.content or "") for chunk in chunks]
        if tokenized and any(tokenized):
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
        fused = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=settings.VECTOR_WEIGHT,
            bm25_weight=settings.BM25_WEIGHT,
            top_k=top_k,
        )
        return self.apply_exact_match_boost(query_text, fused)

    def _bm25_search(self, query: str, layer_filter: Optional[List[str]], top_k: int) -> List[Dict]:
        if not self._bm25_index or not self._bm25_chunks:
            return []
        scores = self._bm25_index.get_scores(self._tokenize(query))
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
                    "relevance_score": score,
                    "search_type": "bm25",
                }
            )
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        vector_weight: float = 0.40,
        bm25_weight: float = 0.60,
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
            row["relevance_score"] = scores[cid]
            results.append(row)
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\b[\w]+\b", text.lower())

    def apply_exact_match_boost(self, query: str, chunks: List[Dict]) -> List[Dict]:
        query_numbers = set(re.findall(r"\b\d+\b", query))
        query_terms = {
            token
            for token in self._tokenize(query)
            if token not in STOP_WORDS and (len(token) > 2 or token in {"ci", "cic"} or token.isdigit())
        }
        regulatory_query_terms = query_terms & REGULATORY_TERMS

        for chunk in chunks:
            content = chunk.get("content") or chunk.get("text") or ""
            chunk_tokens = set(self._tokenize(content))
            chunk_numbers = set(re.findall(r"\b\d+\b", content))
            matched_numbers = query_numbers & chunk_numbers
            matched_terms = regulatory_query_terms & chunk_tokens

            boost = 0.0
            if matched_numbers:
                boost += 0.1 * len(matched_numbers)
                chunk["number_boost_applied"] = True
                chunk["matched_numbers"] = sorted(matched_numbers)
            if matched_terms:
                boost += 0.05 * len(matched_terms)
                chunk["keyword_boost_applied"] = True
                chunk["matched_keywords"] = sorted(matched_terms)

            if boost:
                exact_score = float(chunk.get("relevance_score", chunk.get("fused_score", 0.0))) + boost
                chunk["exact_match_score"] = exact_score
                chunk["relevance_score"] = min(exact_score, 1.0)
                chunk["fused_score"] = min(exact_score, 1.0)

        return sorted(
            chunks,
            key=lambda item: item.get("exact_match_score", item.get("relevance_score", item.get("fused_score", 0.0))),
            reverse=True,
        )

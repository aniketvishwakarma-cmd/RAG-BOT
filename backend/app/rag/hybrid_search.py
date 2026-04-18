from __future__ import annotations

import re
import threading
from typing import Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Chunk, Document
from app.ingestion.embedder import local_embeddings_available
from app.rag.retriever import VectorRetriever


STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "bureau",
    "context",
    "credit",
    "does",
    "explain",
    "for",
    "give",
    "how",
    "in",
    "information",
    "involved",
    "is",
    "key",
    "many",
    "of",
    "regulatory",
    "rules",
    "system",
    "the",
    "to",
    "what",
    "when",
    "which",
    "with",
}


class HybridSearchEngine:
    _shared_bm25_index = None
    _shared_bm25_chunks: list[dict] | None = None
    _bm25_build_lock = threading.Lock()

    def __init__(self, db: Session):
        self.db = db
        self.retriever = VectorRetriever(db)
        if HybridSearchEngine._shared_bm25_index is not None and HybridSearchEngine._shared_bm25_chunks is not None:
            self._bm25_index = HybridSearchEngine._shared_bm25_index
            self._bm25_chunks = HybridSearchEngine._shared_bm25_chunks
            return
        with HybridSearchEngine._bm25_build_lock:
            if HybridSearchEngine._shared_bm25_index is not None and HybridSearchEngine._shared_bm25_chunks is not None:
                self._bm25_index = HybridSearchEngine._shared_bm25_index
                self._bm25_chunks = HybridSearchEngine._shared_bm25_chunks
            else:
                self._bm25_index = None
                self._bm25_chunks: list[dict] = []
                self._build_bm25_index()
                HybridSearchEngine._shared_bm25_index = self._bm25_index
                HybridSearchEngine._shared_bm25_chunks = self._bm25_chunks

    @classmethod
    def invalidate_bm25_cache(cls) -> None:
        cls._shared_bm25_index = None
        cls._shared_bm25_chunks = None

    def _build_bm25_index(self) -> None:
        rows = (
            self.db.query(
                Chunk.id,
                Chunk.content,
                Chunk.bm25_text,
                Chunk.source_layer,
                Chunk.document_id,
                Document.title.label("document_name"),
                Chunk.section_no,
                Chunk.clause_no,
                Chunk.paragraph_no,
                Chunk.page_no,
                Chunk.heading,
                Chunk.priority_rank,
                Chunk.token_count,
            )
            .outerjoin(Document, Document.id == Chunk.document_id)
            .filter(Chunk.is_superseded.is_(False))
            .all()
        )
        self._bm25_chunks = [
            {
                "id": row.id,
                "content": row.content,
                "bm25_text": row.bm25_text,
                "source_layer": row.source_layer,
                "document_id": row.document_id,
                "document_name": row.document_name or "",
                "section_no": row.section_no,
                "clause_no": row.clause_no,
                "paragraph_no": row.paragraph_no,
                "page_no": row.page_no,
                "heading": row.heading,
                "priority_rank": row.priority_rank,
                "token_count": row.token_count,
            }
            for row in rows
        ]
        tokenized = [self._tokenize(chunk.get("bm25_text") or chunk.get("content") or "") for chunk in self._bm25_chunks]
        if tokenized and any(tokenized):
            self._bm25_index = BM25Okapi(tokenized)

    def search(
        self,
        query_text: str,
        query_embedding: List[float],
        layer_filter: Optional[List[str]] = None,
        top_k: int = 50,
        intent: Optional[dict] = None,
        metadata_filters: Optional[dict] = None,
    ) -> List[Dict]:
        effective_layers = self._apply_metadata_filters(layer_filter, metadata_filters or {})
        vector_results = []
        if query_embedding and local_embeddings_available():
            vector_results = self.retriever.semantic_search(query_embedding, effective_layers, top_k * 2)
        bm25_results = self._bm25_search(query_text, effective_layers, top_k * 2)
        fused = self._reciprocal_rank_fusion(vector_results, bm25_results, top_k=top_k)
        return self.apply_exact_match_boost(query_text, fused)

    def _bm25_search(self, query: str, layer_filter: Optional[List[str]], top_k: int) -> List[Dict]:
        if not self._bm25_index or not self._bm25_chunks:
            return []
        scores = self._bm25_index.get_scores(self._tokenize(query))
        indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for index in indices:
            score = float(scores[index])
            if score <= 0:
                break
            chunk = self._bm25_chunks[index]
            if layer_filter and chunk["source_layer"] not in layer_filter:
                continue
            row = dict(chunk)
            row["similarity_score"] = score
            row["relevance_score"] = min(score / 10.0, 1.0)
            row["search_type"] = "bm25"
            results.append(row)
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        top_k: int = 50,
        k: int = 60,
    ) -> List[Dict]:
        scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict] = {}
        for rank, chunk in enumerate(vector_results):
            cid = chunk["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            chunk_data[cid] = chunk
        for rank, chunk in enumerate(bm25_results):
            cid = chunk["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            chunk_data.setdefault(cid, chunk)

        results = []
        for cid, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]:
            row = dict(chunk_data[cid])
            row["rrf_score"] = score
            row["fused_score"] = score
            row["relevance_score"] = min(score * 10.0, 1.0)
            results.append(row)
        return results

    def fuse_ranked_lists(self, ranked_lists: List[List[Dict]], top_k: int = 50, k: int = 60) -> List[Dict]:
        scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict] = {}
        for ranked in ranked_lists:
            for rank, chunk in enumerate(ranked):
                cid = chunk["id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
                existing = chunk_data.get(cid)
                if not existing or self._score(chunk) > self._score(existing):
                    chunk_data[cid] = chunk

        output = []
        for cid, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]:
            row = dict(chunk_data[cid])
            row["multi_query_rrf_score"] = score
            row["relevance_score"] = min(max(score * 10.0, float(row.get("relevance_score", 0.0))), 1.0)
            output.append(row)
        return self._sort_chunks(output)

    def apply_exact_match_boost(self, query: str, chunks: List[Dict]) -> List[Dict]:
        query_tokens = {
            token
            for token in self._tokenize(query)
            if token not in STOP_WORDS and (len(token) > 2 or token.isdigit() or token in {"ci", "cic"})
        }
        query_numbers = {token for token in query_tokens if token.isdigit()}
        for chunk in chunks:
            content = chunk.get("content") or chunk.get("text") or ""
            heading = chunk.get("heading") or ""
            chunk_tokens = set(self._tokenize(content))
            heading_tokens = set(self._tokenize(heading))
            matched_terms = query_tokens & chunk_tokens
            heading_matches = query_tokens & heading_tokens
            matched_numbers = query_numbers & chunk_tokens
            lexical_score = len(matched_terms) / max(len(query_tokens), 1)
            heading_bonus = min(0.10 * len(heading_matches), 0.30)
            number_bonus = min(0.10 * len(matched_numbers), 0.30)
            if lexical_score or heading_bonus or number_bonus:
                base = float(chunk.get("relevance_score", chunk.get("fused_score", 0.0)))
                exact_score = min(base + min(lexical_score * 0.35, 0.35) + heading_bonus + number_bonus, 1.0)
                chunk["exact_match_score"] = exact_score
                chunk["relevance_score"] = exact_score
                chunk["matched_keywords"] = sorted(matched_terms)
                if heading_matches:
                    chunk["matched_heading_keywords"] = sorted(heading_matches)
                if matched_numbers:
                    chunk["matched_numbers"] = sorted(matched_numbers)
        return self._sort_chunks(chunks)

    def intent_aware_filter(self, chunks: List[Dict], intent: Optional[dict]) -> List[Dict]:
        return self._sort_chunks(chunks)

    @staticmethod
    def _apply_metadata_filters(layer_filter: Optional[List[str]], metadata_filters: dict) -> Optional[List[str]]:
        requested = list(layer_filter or [])
        source_type = metadata_filters.get("source_type")
        if not source_type:
            return requested or None
        if requested:
            return [layer for layer in requested if layer == source_type] or requested
        return [source_type]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = re.findall(r"\b[\w]+\b", text.lower())
        normalized: list[str] = []
        for token in tokens:
            normalized.append(token)
            if len(token) > 4 and token.endswith("s"):
                normalized.append(token[:-1])
        return normalized

    @staticmethod
    def _score(chunk: Dict) -> float:
        return max(
            float(chunk.get("exact_match_score", 0.0)),
            float(chunk.get("relevance_score", 0.0)),
            float(chunk.get("rerank_score", 0.0)),
            float(chunk.get("fused_score", 0.0)),
            float(chunk.get("similarity_score", 0.0)) if chunk.get("search_type") == "vector" else 0.0,
        )

    @staticmethod
    def _sort_chunks(chunks: List[Dict]) -> List[Dict]:
        return sorted(
            chunks,
            key=lambda item: (
                -HybridSearchEngine._score(item),
                settings.LAYER_PRIORITY.get(item.get("source_layer", "SOP"), 99),
                item.get("priority_rank", 99) or 99,
            ),
        )

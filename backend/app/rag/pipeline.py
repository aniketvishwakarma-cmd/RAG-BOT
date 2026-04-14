from __future__ import annotations

import hashlib
import json
import time

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.redis_client import get_cache, set_cache
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.query_repo import QueryRepository
from app.graph.knowledge_graph import RegulatoryKnowledgeGraph
from app.ingestion.embedder import EmbeddingService
from app.ingestion.pii_filter import PIIFilter
from app.rag.citation_builder import build_citation_cards
from app.rag.conflict_resolver import ConflictResolver
from app.rag.generator import (
    check_citation_faithfulness,
    expand_query,
    generate_cited_answer,
    source_citations_from_result,
)
from app.rag.groundedness_checker import GroundednessChecker
from app.rag.graph_retriever import GraphRetriever
from app.rag.hybrid_search import HybridSearchEngine
from app.rag.reranker import CohereReranker
from app.schemas.query import QueryRequest, QueryResponse

logger = structlog.get_logger()


class RAGPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.hybrid_search = HybridSearchEngine(db)
        self.reranker = CohereReranker()
        self.resolver = ConflictResolver()
        self.groundedness = GroundednessChecker()
        self.graph = RegulatoryKnowledgeGraph(db)
        self.graph_retriever = GraphRetriever(self.graph)
        self.pii_filter = PIIFilter()
        self.query_repo = QueryRepository(db)
        self.audit_repo = AuditRepository(db)
        self.embedder = EmbeddingService()

    async def run(self, request: QueryRequest, user_id: str | None = None) -> QueryResponse:
        started = time.time()
        cache_key = hashlib.md5(
            f"citation-v2:{request.query}:{sorted(request.layer_filter or [])}:{request.include_graph_context}".encode("utf-8")
        ).hexdigest()
        cached = await get_cache(cache_key)
        if cached and not request.bypass_cache:
            return QueryResponse(**json.loads(cached))

        clean_query = self.pii_filter.redact(request.query)
        expanded_queries = await expand_query(clean_query)
        all_chunks: list[dict] = []
        seen_ids: set[str] = set()
        layer_filter = [layer.value if hasattr(layer, "value") else layer for layer in (request.layer_filter or [])] or None

        for expanded in expanded_queries:
            embedding = await self.embedder.embed_text(expanded)
            for chunk in self.hybrid_search.search(
                query_text=expanded,
                query_embedding=embedding,
                layer_filter=layer_filter,
                top_k=settings.RETRIEVAL_TOP_K,
            ):
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    all_chunks.append(chunk)

        if request.include_graph_context and all_chunks:
            for chunk in self.graph_retriever.fetch_related([item["id"] for item in all_chunks[:10]]):
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    all_chunks.append(chunk)

        retrieval_query = " ".join(expanded_queries)
        all_chunks = self.hybrid_search.apply_exact_match_boost(retrieval_query, all_chunks)
        rerank_top_n = max(settings.RERANK_TOP_N * 3, settings.RERANK_TOP_N)
        reranked = await self.reranker.rerank(query=retrieval_query, chunks=all_chunks, top_n=rerank_top_n)
        reranked = self.hybrid_search.apply_exact_match_boost(retrieval_query, reranked)
        reranked = reranked[: settings.RERANK_TOP_N]
        resolved_chunks, resolution_note = self.resolver.resolve(reranked)
        llm_result = await generate_cited_answer(clean_query, resolved_chunks, resolution_note)

        if not self.groundedness.verify(llm_result.get("answer", ""), resolved_chunks):
            llm_result["confidence"] = min(float(llm_result.get("confidence", 0.0)), 0.60)

        cited_chunks = source_citations_from_result(llm_result)
        faithfulness = check_citation_faithfulness(llm_result.get("answer", ""), cited_chunks)
        llm_result["_citation_faithfulness_scores"] = {
            item["citation_id"]: item for item in faithfulness.get("scores", [])
        }
        citation_mismatch = not faithfulness["is_faithful"]
        if citation_mismatch:
            llm_result["confidence"] = min(float(llm_result.get("confidence", 0.0)), 0.25)

        citation_cards = build_citation_cards(llm_result, resolved_chunks)
        confidence = float(llm_result.get("confidence", 0.0))
        requires_review = confidence < settings.HITL_CONFIDENCE_TRIGGER
        latency_ms = int((time.time() - started) * 1000)

        query_record = self.query_repo.create(
            original_query=request.query,
            clean_query=clean_query,
            expanded_queries=expanded_queries,
            layer_filter=layer_filter or [],
            answer=llm_result.get("answer", ""),
            confidence=confidence,
            resolution_note=resolution_note,
            latency_ms=latency_ms,
            model_used=llm_result.get("_model_used", settings.OPENAI_LLM_MODEL if settings.OPENAI_API_KEY else "deterministic-fallback"),
            chunk_ids_used=[chunk["id"] for chunk in resolved_chunks],
            requires_review=requires_review,
            user_id=user_id,
        )

        if citation_mismatch:
            self.audit_repo.create(
                action="hallucination",
                entity_type="query",
                entity_id=query_record.id,
                user_id=user_id,
                status="failure",
                details={"type": "CITATION_MISMATCH", "detail": faithfulness},
            )

        response = QueryResponse(
            query_id=query_record.id,
            query=request.query,
            answer=llm_result.get("answer", ""),
            key_facts=llm_result.get("key_facts", []),
            confidence=confidence,
            resolution_note=resolution_note or llm_result.get("resolution_hierarchy", "") or "",
            citations=citation_cards,
            requires_human_review=requires_review,
            latency_ms=latency_ms,
            layer_sources_used=sorted({chunk.get("source_layer", "UNKNOWN") for chunk in resolved_chunks}),
            insufficient_evidence=bool(llm_result.get("insufficient_evidence", False)),
            citation_mismatch=citation_mismatch,
            citation_warning=faithfulness.get("warning"),
        )

        if confidence >= settings.HITL_CONFIDENCE_TRIGGER:
            await set_cache(cache_key, response.model_dump_json(), ttl=settings.CACHE_TTL_SECONDS)

        logger.info("pipeline_complete", latency_ms=latency_ms, confidence=confidence)
        return response

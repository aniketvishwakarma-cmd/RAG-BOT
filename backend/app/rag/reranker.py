from __future__ import annotations

from typing import List

import structlog

try:
    import cohere
except Exception:  # pragma: no cover
    cohere = None

from app.core.config import settings

logger = structlog.get_logger()


class CohereReranker:
    def __init__(self) -> None:
        self.client = cohere.Client(settings.COHERE_API_KEY) if cohere and settings.COHERE_API_KEY else None

    async def rerank(self, query: str, chunks: List[dict], top_n: int = 8) -> List[dict]:
        if not chunks:
            return []
        if self.client:
            try:
                response = self.client.rerank(
                    model=settings.COHERE_RERANK_MODEL,
                    query=query,
                    documents=[chunk["content"] for chunk in chunks],
                    top_n=min(top_n, len(chunks)),
                )
                reranked = []
                for result in response.results:
                    chunk = dict(chunks[result.index])
                    chunk["rerank_score"] = float(result.relevance_score)
                    reranked.append(chunk)
                return reranked
            except Exception as exc:
                logger.warning(
                    "rerank_fallback_enabled",
                    model=settings.COHERE_RERANK_MODEL,
                    error=str(exc),
                )

        query_terms = set(query.lower().split())
        scored = []
        for chunk in chunks:
            overlap = len(query_terms & set(chunk["content"].lower().split()))
            scored.append((overlap / max(len(query_terms), 1) + chunk.get("fused_score", 0.0), chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        output = []
        for score, chunk in scored[:top_n]:
            row = dict(chunk)
            row["rerank_score"] = score
            output.append(row)
        return output


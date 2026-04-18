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
    _disabled = False

    def __init__(self) -> None:
        self.client = (
            cohere.Client(settings.COHERE_API_KEY, timeout=min(settings.EXTERNAL_PROVIDER_TIMEOUT_SECONDS, 3.0))
            if cohere and settings.COHERE_API_KEY
            else None
        )

    async def rerank(self, query: str, chunks: List[dict], top_n: int = 8) -> List[dict]:
        if not chunks:
            return []
        if self.client and not self._disabled:
            try:
                response = self.client.rerank(
                    model=settings.COHERE_RERANK_MODEL,
                    query=query,
                    documents=[chunk["content"] for chunk in chunks],
                    top_n=min(top_n, len(chunks)),
                    request_options={
                        "timeout_in_seconds": int(min(settings.EXTERNAL_PROVIDER_TIMEOUT_SECONDS, 3.0)),
                        "max_retries": 0,
                    },
                )
                reranked = []
                for result in response.results:
                    chunk = dict(chunks[result.index])
                    chunk["rerank_score"] = float(result.relevance_score)
                    reranked.append(chunk)
                return reranked
            except Exception as exc:
                self.__class__._disabled = True
                logger.warning(
                    "rerank_fallback_enabled",
                    model=settings.COHERE_RERANK_MODEL,
                    error=str(exc),
                )

        output = []
        for chunk in chunks[:top_n]:
            row = dict(chunk)
            row["rerank_score"] = float(row.get("relevance_score", row.get("fused_score", 0.0)))
            output.append(row)
        return output


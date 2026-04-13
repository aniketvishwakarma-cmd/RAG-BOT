from __future__ import annotations

import hashlib
import math
from typing import Iterable

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def embed_text(self, text: str) -> list[float]:
        if self.client:
            try:
                response = await self.client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text,
                )
                return list(response.data[0].embedding)
            except Exception as exc:
                logger.warning(
                    "embedding_fallback_enabled",
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    error=str(exc),
                )
        return self._hash_embedding(text)

    async def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]

    def _hash_embedding(self, text: str) -> list[float]:
        dims = settings.OPENAI_EMBEDDING_DIMENSIONS
        vector = [0.0] * dims
        for token in text.lower().split():
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % dims
            vector[idx] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

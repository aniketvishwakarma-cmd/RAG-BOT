from __future__ import annotations

import asyncio
import hashlib
import math
import threading
from typing import Iterable

import structlog

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

from app.core.config import settings

logger = structlog.get_logger()


def local_embeddings_available() -> bool:
    return SentenceTransformer is not None


class LocalEmbedder:
    _instance: "LocalEmbedder | None" = None
    _model = None
    _model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LocalEmbedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed")
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    try:
                        self._model = SentenceTransformer(settings.LOCAL_EMBEDDING_MODEL, local_files_only=True)
                    except Exception as local_exc:
                        logger.warning(
                            "local_embedding_model_cache_miss",
                            model=settings.LOCAL_EMBEDDING_MODEL,
                            error=str(local_exc),
                        )
                        self._model = SentenceTransformer(settings.LOCAL_EMBEDDING_MODEL)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return self._match_configured_dimensions(embedding.tolist())

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [self._match_configured_dimensions(embedding.tolist()) for embedding in embeddings]

    @staticmethod
    def _match_configured_dimensions(vector: list[float]) -> list[float]:
        dims = settings.OPENAI_EMBEDDING_DIMENSIONS
        if len(vector) == dims:
            return vector
        if len(vector) > dims:
            return vector[:dims]
        return vector + [0.0] * (dims - len(vector))


class EmbeddingService:
    def __init__(self) -> None:
        self.local_embedder = LocalEmbedder.get_instance()

    async def embed_text(self, text: str) -> list[float]:
        try:
            return await asyncio.to_thread(self.local_embedder.embed_text, text)
        except Exception as exc:
            logger.warning(
                "local_embedding_fallback_enabled",
                model=settings.LOCAL_EMBEDDING_MODEL,
                error=str(exc),
            )
        return self._hash_embedding(text)

    async def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        text_list = list(texts)
        try:
            return await asyncio.to_thread(self.local_embedder.embed_batch, text_list)
        except Exception as exc:
            logger.warning(
                "local_embedding_batch_fallback_enabled",
                model=settings.LOCAL_EMBEDDING_MODEL,
                error=str(exc),
            )
        return [self._hash_embedding(text) for text in text_list]

    def _hash_embedding(self, text: str) -> list[float]:
        dims = settings.OPENAI_EMBEDDING_DIMENSIONS
        vector = [0.0] * dims
        for token in text.lower().split():
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % dims
            vector[idx] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

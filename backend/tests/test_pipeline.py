import pytest

from app.ingestion.embedder import EmbeddingService
from app.rag.generator import generate_cited_answer


@pytest.mark.asyncio
async def test_generator_fallback_refuses_without_chunks():
    result = await generate_cited_answer("late EMI penalty", [], None)
    assert result["insufficient_evidence"] is True


@pytest.mark.asyncio
async def test_embedding_service_fallback_runs():
    embedding = await EmbeddingService().embed_text("21 days plus 9 days")
    assert len(embedding) == 1536


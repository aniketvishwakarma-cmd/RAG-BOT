from app.ingestion.embedder import EmbeddingService


def test_hash_embedding_has_expected_dimension():
    service = EmbeddingService()
    embedding = service._hash_embedding("reporting delay compensation")
    assert len(embedding) == 1536


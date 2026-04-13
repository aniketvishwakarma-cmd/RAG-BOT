from app.rag.conflict_resolver import ConflictResolver


def test_conflict_resolver_prefers_higher_layer():
    resolver = ConflictResolver()
    chunks = [
        {"id": "1", "source_layer": "SOP", "section_no": "8.4", "fused_score": 0.9},
        {"id": "2", "source_layer": "RBI_MASTER", "section_no": "8.4", "fused_score": 0.8},
    ]
    resolved, note = resolver.resolve(chunks)
    assert resolved[0]["source_layer"] == "RBI_MASTER"
    assert "Regulatory source preferred" in note


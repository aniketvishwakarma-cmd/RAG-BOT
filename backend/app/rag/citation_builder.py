from __future__ import annotations

import re

from app.core.constants import LAYER_PRIORITY
from app.schemas.citation import CitationCard


def build_citation_cards(llm_result: dict, chunks: list[dict]) -> list[CitationCard]:
    chunk_map = llm_result.get("_chunk_map") or {}
    source_ids = []
    serialized = f"{llm_result.get('answer', '')} {' '.join(llm_result.get('key_facts', []))}"
    for match in re.findall(r"\[(SRC_\d+)\]", serialized):
        if match not in source_ids:
            source_ids.append(match)
    if not source_ids:
        source_ids = list(chunk_map.keys())[: min(3, len(chunk_map))]

    cards = []
    for source_id in source_ids:
        chunk = chunk_map.get(source_id)
        if not chunk:
            continue
        content = chunk.get("content", "")
        cards.append(
            CitationCard(
                source_name=chunk.get("document_name", "Unknown source"),
                source_layer=chunk.get("source_layer", "UNKNOWN"),
                layer_priority=LAYER_PRIORITY.get(chunk.get("source_layer", "SOP"), 99),
                section_no=chunk.get("section_no"),
                clause_no=chunk.get("clause_no"),
                paragraph_no=chunk.get("paragraph_no"),
                page_no=chunk.get("page_no"),
                excerpt=(content[:197] + "...") if len(content) > 200 else content,
                relevance_score=float(chunk.get("rerank_score", chunk.get("fused_score", 0.0))),
            )
        )
    return cards


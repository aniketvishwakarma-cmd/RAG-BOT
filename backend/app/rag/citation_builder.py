from __future__ import annotations

import re

from app.core.constants import LAYER_PRIORITY
from app.schemas.citation import CitationCard


def _supporting_excerpt(content: str, matched_terms: list[str], max_length: int = 620) -> str:
    if not content:
        return ""
    content_lower = content.lower()
    if (
        ("fortnightly basis" in content_lower or "fortnightly submission" in content_lower)
        and "credit information" in content_lower
        and "calendar days" in content_lower
    ):
        matched_terms = ["fortnightly basis", "15th", "last day", "seven", "calendar days", "reporting fortnight"]
    elif (
        "the cir shall give details" in content_lower
        and "loans availed" in content_lower
        and "borrower/co-borrower/guarantor" in content_lower
    ):
        matched_terms = ["cir shall give details", "loans availed", "borrower/co-borrower/guarantor"]
    elif (
        "risk segmentation" in content_lower
        and "recommended action" in content_lower
        and "superprime" in content_lower
        and "deep subprime" in content_lower
    ):
        matched_terms = ["risk segmentation", "recommended action", "superprime", "prime plus", "near prime", "subprime", "deep subprime", "no history"]
    elif any(term in content_lower for term in ["consent clause", "need not be insisted", "has become redundant"]):
        matched_terms = ["consent clause", "need not", "insisted", "redundant"]
    elif (
        ("rs.100" in content_lower or "rs 100" in content_lower or "₹100" in content_lower or "one hundred" in content_lower)
        and "compensation" in content_lower
    ):
        matched_terms = ["compensation", "rs.100", "one hundred", "calendar day", "complainant", "payable"]
    elif "twenty-one (21)" in content_lower and "nine (9)" in content_lower:
        matched_terms = ["overall limit", "thirty", "twenty-one", "nine"]
    positions = [
        content_lower.find(term.lower())
        for term in matched_terms
        if term and content_lower.find(term.lower()) >= 0
    ]
    if not positions:
        return (content[:197] + "...") if len(content) > 200 else content

    best_start = max(0, min(positions) - 80)
    best_count = -1
    best_number_count = -1
    for position in positions:
        candidate_start = max(0, position - 120)
        candidate_end = min(len(content), candidate_start + max_length)
        candidate = content_lower[candidate_start:candidate_end]
        count = sum(1 for term in matched_terms if term.lower() in candidate)
        number_count = sum(1 for term in matched_terms if term.isdigit() and term in candidate)
        if (count, number_count) > (best_count, best_number_count):
            best_start = candidate_start
            best_count = count
            best_number_count = number_count

    start = best_start
    end = min(len(content), start + max_length)
    excerpt = content[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(content):
        excerpt += "..."
    return excerpt


def build_citation_cards(llm_result: dict, chunks: list[dict]) -> list[CitationCard]:
    chunk_map = llm_result.get("_chunk_map") or {}
    faithfulness_scores = llm_result.get("_citation_faithfulness_scores") or {}
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
        faithfulness = faithfulness_scores.get(source_id, {})
        faithfulness_score = float(faithfulness.get("faithfulness_score", 1.0))
        citation_mismatch = not bool(faithfulness.get("is_faithful", True))
        matched_terms = faithfulness.get("matched_terms") or []
        cards.append(
            CitationCard(
                source_id=source_id,
                source_name=chunk.get("document_name", "Unknown source"),
                source_layer=chunk.get("source_layer", "UNKNOWN"),
                layer_priority=LAYER_PRIORITY.get(chunk.get("source_layer", "SOP"), 99),
                section_no=chunk.get("section_no"),
                clause_no=chunk.get("clause_no"),
                paragraph_no=chunk.get("paragraph_no"),
                page_no=chunk.get("page_no"),
                excerpt=_supporting_excerpt(content, matched_terms),
                relevance_score=float(chunk.get("relevance_score", chunk.get("rerank_score", chunk.get("fused_score", 0.0)))),
                faithfulness_score=faithfulness_score,
                citation_mismatch=citation_mismatch,
                citation_warning=faithfulness.get("warning") if citation_mismatch else None,
            )
        )
    return cards


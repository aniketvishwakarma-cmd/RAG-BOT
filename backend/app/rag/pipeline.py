from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.redis_client import get_cache, set_cache
from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.query_repo import QueryRepository
from app.graph.knowledge_graph import RegulatoryKnowledgeGraph
from app.ingestion.embedder import EmbeddingService, local_embeddings_available
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

QUERY_STOP_WORDS = {
    "a",
    "an",
    "and",
        "after",
        "about",
        "are",
    "as",
    "before",
    "for",
    "happen",
    "happens",
    "how",
    "in",
    "is",
    "guideline",
    "guidelines",
    "involved",
    "key",
    "many",
    "me",
    "must",
    "of",
    "on",
        "or",
        "performed",
        "give",
        "required",
        "rbi",
    "should",
    "tell",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "system",
    "bureau",
}

DOMAIN_QUERY_ALIASES = {
    "education": {"education", "educational", "student", "students", "study", "studies"},
    "loan": {"loan", "loans", "lending", "advance", "advances"},
    "loans": {"loan", "loans", "lending", "advance", "advances"},
    "student": {"education", "educational", "student", "students"},
    "collateral": {"collateral", "security", "guarantee", "guarantor"},
    "moratorium": {"moratorium", "repayment", "holiday"},
    "repayment": {"repayment", "repay", "moratorium"},
    "cbis": {"cbis", "credit bureau information system"},
    "api": {"api", "file / api", "file api"},
    "business": {"business", "business rule"},
    "cleansing": {"cleansing", "cleaning", "normalisation", "normalization"},
    "field": {"field", "field-level", "field level"},
    "field-level": {"field-level", "field level"},
    "file": {"file", "file / api", "file api"},
    "hdr": {"hdr", "header"},
    "mi": {"mi", "management information"},
    "ci": {"ci", "cis", "credit institution", "credit institutions"},
    "cis": {"ci", "cis", "credit institution", "credit institutions"},
    "cic": {"cic", "cics", "credit information company", "credit information companies"},
    "cics": {"cic", "cics", "credit information company", "credit information companies"},
    "cir": {"cir", "credit information report"},
    "co-borrowers": {"co-borrower", "co borrower", "co-borrowers", "borrower/co-borrower/guarantor"},
    "guarantors": {"guarantor", "guarantors", "borrower/co-borrower/guarantor"},
    "institutions": {"institution", "institutions", "ci", "cis", "credit institution", "credit institutions"},
    "submit": {"submit", "submits", "submitted", "submission", "report", "reporting", "furnish", "furnishing"},
    "submission": {"submit", "submitted", "submission", "report", "reporting", "furnish", "furnishing"},
    "completed": {"completed", "complete", "ensured", "within"},
    "audit": {"audit", "auditor", "auditing"},
    "internal": {"internal", "internal audit"},
    "mechanism": {"mechanism", "controls", "process"},
    "frequency": {"frequency", "basis", "fortnightly", "refresh frequency"},
    "refresh": {"refresh", "score refresh"},
    "score": {"score", "score refresh"},
    "risk": {"risk", "risk tier", "risk tiers", "risk segment", "risk segments", "risk segmentation"},
    "segments": {"segment", "segments", "tier", "tiers"},
    "lenders": {"lender", "lenders", "member institution", "member institutions"},
    "recommended": {"recommended", "action", "actions", "recommended action"},
    "sla": {"sla", "internal sla"},
    "stage": {"stage", "stages", "pipeline"},
    "stages": {"stage", "stages", "pipeline"},
    "structural": {"structural", "structure"},
    "tat": {"tat", "turnaround time"},
    "turnaround": {"turnaround", "turnaround time", "tat"},
    "normalisation": {"normalisation", "normalization", "cleansing"},
    "normalization": {"normalisation", "normalization", "cleansing"},
    "validation": {"validation", "validate", "checks", "pipeline"},
    "validations": {"validation", "validate", "checks", "pipeline"},
    "dispute": {"dispute", "complaint", "grievance"},
    "complaint": {"complaint", "complainant", "grievance", "dispute"},
    "compensation": {"compensation", "compensate", "payable", "entitled"},
    "consent": {"consent", "permission", "authorisation", "authorization"},
    "borrower": {"borrower", "consumer", "customer", "complainant"},
}


def classify_query_intent(query: str) -> dict:
    """
    Classify the answer shape before retrieval so related Section 11 topics
    do not collapse into the same evidence set.
    """
    query_lower = query.lower()

    def contains_term(term: str) -> bool:
        normalized_query = query_lower.replace("_", " ").replace("-", " ")
        normalized_term = term.lower().replace("_", " ").replace("-", " ")
        if len(normalized_term) <= 3 and normalized_term.isalnum():
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}\.?(?![a-z0-9])", normalized_query))
        if " " in normalized_term:
            return normalized_term in normalized_query
        return bool(re.search(rf"\b{re.escape(normalized_term)}\b", normalized_query))

    intent_patterns = {
        "cir_borrower_details": {
            "keywords": [
                "borrower-related details",
                "borrower related details",
                "co-borrowers",
                "co borrower",
                "co-borrower",
                "guarantors",
                "guarantor",
                "borrower/co-borrower/guarantor",
                "cir regarding",
                "cir details",
                "credit information report",
                "loans availed",
                "capacity as borrower",
                "multiple borrowings",
            ],
            "priority_terms": [
                "cir",
                "loans availed",
                "borrower",
                "co-borrower",
                "guarantor",
            ],
            "avoid_terms": ["compensation", "penalty", "delay", "rs", "payable"],
        },
        "risk_segmentation": {
            "keywords": [
                "risk segmentation",
                "risk segments",
                "risk segment",
                "risk tiers",
                "classify consumers",
                "classify consumer",
                "recommended action",
                "recommended actions",
                "actions recommended for lenders",
                "superprime",
                "prime plus",
                "near prime",
                "subprime",
                "deep subprime",
                "no history",
                "portfolio management",
            ],
            "priority_terms": [
                "risk segmentation",
                "superprime",
                "prime plus",
                "prime",
                "near prime",
                "subprime",
                "deep subprime",
                "no history",
            ],
            "avoid_terms": ["validation", "dispute", "compensation", "data cleansing"],
        },
        "credit_data_submission": {
            "keywords": [
                "submit credit information",
                "submission of credit information",
                "submission of data",
                "reporting of credit information",
                "credit information to cics",
                "credit information to cic",
                "cis to cics",
                "ci to cic",
                "fortnightly submission",
                "fortnightly basis",
                "reporting fortnight",
                "relevant reporting fortnight",
                "15th and last day",
                "15th",
                "last day of the respective month",
                "seven (7) calendar days",
                "seven calendar days",
            ],
            "priority_terms": [
                "fortnightly basis",
                "15th",
                "last day",
                "seven (7) calendar days",
                "reporting fortnight",
            ],
            "avoid_terms": ["dispute", "complaint", "compensation", "score refresh", "tat"],
        },
        "timeline": {
            "keywords": [
                "timeline",
                "how many days",
                "how long",
                "time limit",
                "window",
                "duration",
                "period",
                "deadline",
                "within how many",
            ],
            "priority_terms": ["21", "9", "30 days"],
            "avoid_terms": ["compensation", "penalty", "entitled", "payable", "rs", "rupee", "₹"],
        },
        "compensation": {
            "keywords": [
                "compensation",
                "entitled",
                "payable",
                "penalty",
                "amount",
                "how much",
                "money",
                "rupees",
                "rs",
                "₹",
                "customer get",
                "consumer get",
                "customer receive",
                "complainant receive",
                "not resolved",
                "delayed resolution",
                "delay",
            ],
            "priority_terms": ["100", "per day", "rs.100", "compensation"],
            "avoid_terms": ["timeline", "window", "how long"],
        },
        "obligation": {
            "keywords": [
                "must",
                "shall",
                "obligation",
                "required",
                "responsibility",
                "duty",
                "what should",
                "what must",
                "needs to",
            ],
            "priority_terms": ["ci shall", "cic shall"],
            "avoid_terms": [],
        },
        "data_validation": {
            "keywords": [
                "data validation",
                "validation pipeline",
                "validation stages",
                "key stages",
                "stage 1",
                "stage 2",
                "stage 3",
                "stage one",
                "stage two",
                "stage three",
                "structural validation",
                "structural",
                "field-level",
                "field-level validation",
                "field level",
                "business rule",
                "business rule validation",
                "error rate",
                "quarantine",
                "reject file",
                "alert mi",
                "file api",
                "file / api",
                "pan format",
                "dpd range",
            ],
            "priority_terms": ["stage 1", "stage 2", "stage 3", "structural", "field-level", "business rule"],
            "avoid_terms": [],
        },
        "data_cleansing": {
            "keywords": [
                "data cleansing",
                "data cleansing rules",
                "cleansing rules",
                "name normalisation",
                "name normalization",
                "address normalisation",
                "address normalization",
                "financial data cleansing",
                "honorifics",
                "pincode",
                "dpd",
                "negative balances",
                "outstanding balance",
            ],
            "priority_terms": [
                "data cleansing rules",
                "name normalisation",
                "address normalisation",
                "financial data cleansing",
            ],
            "avoid_terms": [],
        },
        "internal_audit_mechanism": {
            "keywords": [
                "internal audit mechanism",
                "audit mechanism",
                "internal audit",
                "automated controls",
                "privileged access monitoring",
                "tamper-proof ledger",
                "tamper proof ledger",
                "data integrity checks",
                "api abuse detection",
                "periodic audit schedule",
            ],
            "priority_terms": [
                "internal audit mechanism",
                "automated controls",
                "privileged access monitoring",
                "data integrity checks",
                "api abuse detection",
            ],
            "avoid_terms": [],
        },
        "score_refresh_frequency": {
            "keywords": [
                "score refresh frequency",
                "refresh frequency",
                "standard refresh",
                "event-triggered refresh",
                "event triggered refresh",
                "consumer-requested refresh",
                "consumer requested refresh",
                "lender-triggered pull",
                "lender triggered pull",
                "monthly refresh",
                "score computed real-time",
            ],
            "priority_terms": [
                "score refresh frequency",
                "standard refresh",
                "monthly",
                "event-triggered",
                "consumer-requested",
                "lender-triggered",
                "500ms",
            ],
            "avoid_terms": ["tat", "turnaround time", "internal sla", "breach action", "cdo notification"],
        },
        "tat": {
            "keywords": [
                "record correction and score refresh",
                "record correction",
                "tat",
                "turnaround time",
                "internal sla",
                "breach action",
                "cdo notification",
                "consumer final notification",
            ],
            "priority_terms": ["record correction", "30 days", "28 calendar days", "cdo notification"],
            "avoid_terms": [],
        },
        "definition": {
            "keywords": ["what is", "define", "meaning", "explain", "describe"],
            "priority_terms": [],
            "avoid_terms": [],
        },
    }

    detected_intent = "general"
    max_score = 0
    for intent, patterns in intent_patterns.items():
        score = sum(2 for keyword in patterns["keywords"] if contains_term(keyword))
        score -= sum(1 for term in patterns["avoid_terms"] if contains_term(term))
        if score > max_score:
            max_score = score
            detected_intent = intent

    return {
        "intent": detected_intent,
        "confidence": min(max(max_score, 0) / 4, 1.0),
        "priority_terms": intent_patterns.get(detected_intent, {}).get("priority_terms", []),
    }


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]*\b", query.lower())
        if token not in QUERY_STOP_WORDS and len(token) > 2
    }


def _expanded_term_group(term: str) -> set[str]:
    return DOMAIN_QUERY_ALIASES.get(term, {term})


def extract_query_metadata(query: str) -> dict:
    """Light self-querying metadata extraction for source filters."""
    filters = {}
    query_lower = query.lower()
    source_signals = {
        "RBI_MASTER": [
            "master direction",
            "rbi direction",
            "rbi master",
            "master circular",
        ],
        "SOP": [
            "sop",
            "cbis",
            "internal process",
            "procedure",
            "protocol",
            "our system",
        ],
        "CICRA": [
            "cicra",
            "cicra 2005",
            "section 21",
            "section 17",
            "act",
        ],
        "RBI_CIRCULAR": [
            "circular",
            "notification",
            "rbi says",
        ],
    }

    def has_signal(signal: str) -> bool:
        if len(signal) <= 3 and signal.isalnum():
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(signal)}(?![a-z0-9])", query_lower))
        return signal in query_lower

    for source_type, signals in source_signals.items():
        if any(has_signal(signal) for signal in signals):
            filters["source_type"] = source_type
            break
    section_match = re.search(r"\bsection\s+(\d+(?:\.\d+)*)\b", query_lower)
    if section_match:
        filters["section_no"] = section_match.group(1)
    return filters


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?<=;)\s+|\n+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size])) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right[:size])) or 1.0
    return dot / (left_norm * right_norm)


def check_query_source_relevance(query: str, chunks: list[dict]) -> dict:
    terms = _query_terms(query)
    if not terms:
        return {"is_relevant": True, "score": 1.0, "matched_terms": [], "missing_terms": []}

    combined = " ".join(
        " ".join(
            [
                chunk.get("document_name") or "",
                chunk.get("heading") or "",
                chunk.get("content") or chunk.get("text") or "",
            ]
        ).lower()
        for chunk in chunks[: settings.RERANK_TOP_N]
    )
    normalized_combined = combined.replace("_", " ").replace("-", " ")
    matched_terms = []
    missing_terms = []
    for term in sorted(terms):
        aliases = _expanded_term_group(term)
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized_combined) for alias in aliases):
            matched_terms.append(term)
        else:
            missing_terms.append(term)

    score = len(matched_terms) / len(terms)
    has_any_core_term = bool(matched_terms)
    top_evidence_score = max(
        [
            float(
                chunk.get(
                    "rerank_score",
                    chunk.get("exact_match_score", chunk.get("relevance_score", chunk.get("similarity_score", 0.0))),
                )
            )
            for chunk in chunks[: settings.RERANK_TOP_N]
        ]
        or [0.0]
    )
    is_relevant = (
        score >= 0.30
        or (len(terms) <= 2 and has_any_core_term)
        or (has_any_core_term and top_evidence_score >= 0.45)
    )
    if {"education", "loan"}.issubset(terms) or {"education", "loans"}.issubset(terms):
        has_education = any(re.search(rf"\b{re.escape(alias)}\b", normalized_combined) for alias in _expanded_term_group("education"))
        has_loan = any(re.search(rf"\b{re.escape(alias)}\b", normalized_combined) for alias in _expanded_term_group("loan"))
        is_relevant = has_education and has_loan
    if "cbis" in terms and "validation" in terms:
        has_cbis = any(re.search(rf"\b{re.escape(alias)}\b", normalized_combined) for alias in _expanded_term_group("cbis"))
        has_validation = bool(re.search(r"\bvalidation\b", normalized_combined))
        has_stage = any(re.search(rf"\b{re.escape(alias)}\b", normalized_combined) for alias in _expanded_term_group("stages"))
        is_relevant = has_cbis and has_validation and has_stage
    sop_validation_signals = {
        "stage",
        "structural",
        "field-level",
        "field",
        "business",
        "validation",
        "api",
        "file",
        "quarantine",
        "reject",
        "pan",
        "dpd",
        "hdr",
    }
    if terms & sop_validation_signals:
        has_sop_validation = (
            ("cbis" in normalized_combined or "three stage validation pipeline" in normalized_combined)
            and "validation" in normalized_combined
            and (
                "stage 1" in normalized_combined
                or "stage 2" in normalized_combined
                or "stage 3" in normalized_combined
                or "field level" in normalized_combined
                or "business rule" in normalized_combined
            )
        )
        if has_sop_validation:
            is_relevant = True
            if "sop-validation" not in matched_terms:
                matched_terms.append("sop-validation")
    sop_tat_signals = {"score", "refresh", "tat", "turnaround", "sla"}
    data_submission_signals = {"submit", "submission", "frequency", "cis", "cics", "institutions"}
    if terms & data_submission_signals:
        has_data_submission = (
            ("fortnightly basis" in normalized_combined or "fortnightly submission" in normalized_combined)
            and (
                ("seven" in normalized_combined and "(7)" in normalized_combined and "calendar days" in normalized_combined)
                or "seven calendar days" in normalized_combined
                or "7 calendar days" in normalized_combined
            )
            and ("credit information" in normalized_combined)
            and ("cis" in normalized_combined or "credit institutions" in normalized_combined)
            and ("cics" in normalized_combined or "credit information companies" in normalized_combined)
        )
        if has_data_submission:
            is_relevant = True
            if "rbi-credit-data-submission" not in matched_terms:
                matched_terms.append("rbi-credit-data-submission")
    risk_segmentation_signals = {"risk", "segments", "lenders", "recommended"}
    if terms & risk_segmentation_signals:
        has_risk_segmentation = (
            ("risk segmentation" in normalized_combined or "risk tiers" in normalized_combined)
            and ("recommended action" in normalized_combined or "recommended action for lenders" in normalized_combined)
            and ("superprime" in normalized_combined)
            and ("deep subprime" in normalized_combined)
            and ("no history" in normalized_combined or "nh" in normalized_combined)
        )
        if has_risk_segmentation:
            is_relevant = True
            if "sop-risk-segmentation" not in matched_terms:
                matched_terms.append("sop-risk-segmentation")
    cir_borrower_signals = {"cir", "borrower-related", "co-borrowers", "guarantors", "borrower"}
    if terms & cir_borrower_signals:
        has_cir_borrower_details = (
            ("cir" in normalized_combined or "credit information report" in normalized_combined)
            and ("loans availed" in normalized_combined or "loan" in normalized_combined)
            and ("borrower" in normalized_combined)
            and ("co borrower" in normalized_combined or "co-borrower" in combined)
            and ("guarantor" in normalized_combined)
        )
        if has_cir_borrower_details:
            is_relevant = True
            if "rbi-cir-borrower-details" not in matched_terms:
                matched_terms.append("rbi-cir-borrower-details")
    if {"internal", "audit", "mechanism"}.issubset(terms) or {"audit", "mechanism"}.issubset(terms):
        has_internal_audit_mechanism = (
            "internal audit mechanism" in normalized_combined
            and (
                "automated controls" in normalized_combined
                or "privileged access monitoring" in normalized_combined
                or "tamper proof ledger" in normalized_combined
                or "data integrity checks" in normalized_combined
                or "api abuse detection" in normalized_combined
            )
        )
        if has_internal_audit_mechanism:
            is_relevant = True
            if "sop-internal-audit-mechanism" not in matched_terms:
                matched_terms.append("sop-internal-audit-mechanism")
    if {"score", "refresh", "frequency"}.issubset(terms) or {"refresh", "frequency"}.issubset(terms):
        has_score_refresh_frequency = (
            "score refresh frequency" in normalized_combined
            and (
                "standard refresh" in normalized_combined
                or "event triggered refresh" in normalized_combined
                or "consumer requested refresh" in normalized_combined
                or "lender triggered pull" in normalized_combined
                or "500ms" in normalized_combined
            )
        )
        if has_score_refresh_frequency:
            is_relevant = True
            if "sop-score-refresh-frequency" not in matched_terms:
                matched_terms.append("sop-score-refresh-frequency")
    if terms & sop_tat_signals:
        has_sop_tat = (
            ("cbis" in normalized_combined or "tat" in normalized_combined or "turnaround time" in normalized_combined)
            and ("score refresh" in normalized_combined or "record correction" in normalized_combined)
            and ("30 days" in normalized_combined or "28 calendar days" in normalized_combined)
        )
        if has_sop_tat:
            is_relevant = True
            if "sop-tat" not in matched_terms:
                matched_terms.append("sop-tat")
    sop_cleansing_signals = {"cleansing", "normalisation", "normalization", "pincode", "dpd"}
    if terms & sop_cleansing_signals:
        has_sop_cleansing = (
            ("data cleansing rules" in normalized_combined or "name normalisation" in normalized_combined)
            and ("address normalisation" in normalized_combined or "financial data cleansing" in normalized_combined)
        )
        if has_sop_cleansing:
            is_relevant = True
            if "sop-data-cleansing" not in matched_terms:
                matched_terms.append("sop-data-cleansing")
    return {
        "is_relevant": is_relevant,
        "score": round(score, 2),
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
    }


def calculate_confidence(citations: list, faithfulness: dict, retrieval_scores: list[float]) -> float:
    if not citations:
        return 0.0

    bounded_scores = [min(max(float(score), 0.0), 1.0) for score in retrieval_scores if score is not None]
    avg_retrieval = sum(bounded_scores) / len(bounded_scores) if bounded_scores else 0.0

    faithfulness_bonus = 0.1 if faithfulness.get("is_faithful") else -0.2
    citation_bonus = min(len(citations) * 0.05, 0.15)

    source_bonus = 0.0
    for citation in citations:
        source_layer = getattr(citation, "source_layer", None)
        if source_layer is None and isinstance(citation, dict):
            source_layer = citation.get("source_layer")
        if source_layer == "RBI_MASTER":
            source_bonus += 0.1
        elif source_layer == "CICRA":
            source_bonus += 0.05
        elif source_layer == "RBI_CIRCULAR":
            source_bonus += 0.03
    source_bonus = min(source_bonus, 0.15)

    confidence = avg_retrieval + faithfulness_bonus + citation_bonus + source_bonus
    return round(min(max(confidence, 0.0), 1.0), 2)


class RAGPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.hybrid_search = HybridSearchEngine(db)
        self.reranker = CohereReranker()
        self.resolver = ConflictResolver()
        self.groundedness = GroundednessChecker()
        self.graph_retriever: GraphRetriever | None = None
        self.pii_filter = PIIFilter()
        self.query_repo = QueryRepository(db)
        self.audit_repo = AuditRepository(db)
        self.embedder = EmbeddingService()

    async def _compress_chunks(self, query: str, chunks: list[dict], sentences_per_chunk: int = 3) -> list[dict]:
        query_embedding = (await self.embedder.embed_many([query]))[0] if chunks else []
        compressed: list[dict] = []
        for chunk in chunks:
            original_text = chunk.get("content") or chunk.get("text") or ""
            sentences = _split_sentences(original_text)[:24]
            if len(sentences) <= sentences_per_chunk:
                row = dict(chunk)
                row["full_content"] = original_text
                compressed.append(row)
                continue

            sentence_embeddings = await self.embedder.embed_many(sentences)
            scored = [
                (_cosine_similarity(query_embedding, sentence_embedding), index, sentence)
                for index, (sentence, sentence_embedding) in enumerate(zip(sentences, sentence_embeddings))
            ]
            scored.sort(key=lambda item: item[0], reverse=True)
            selected_indexes = sorted(index for _, index, _ in scored[:sentences_per_chunk])
            selected_sentences = [sentences[index] for index in selected_indexes]
            row = dict(chunk)
            row["full_content"] = original_text
            row["content"] = " ".join(selected_sentences)
            row["context_compressed"] = True
            row["compression_sentence_count"] = len(selected_sentences)
            compressed.append(row)
        return compressed

    async def _compute_grounding_score(self, answer: str, chunks: list[dict]) -> float:
        if not answer or "Insufficient evidence" in answer:
            return 1.0
        answer_sentences = [
            re.sub(r"\[SRC_\d+\]", "", sentence).strip()
            for sentence in _split_sentences(answer)
            if sentence.strip()
        ]
        source_text = " ".join(chunk.get("content", "") for chunk in chunks[: settings.RERANK_TOP_N])
        if not answer_sentences or not source_text:
            return 0.0
        embeddings = await self.embedder.embed_many(answer_sentences + [source_text])
        source_embedding = embeddings[-1]
        scores = [_cosine_similarity(sentence_embedding, source_embedding) for sentence_embedding in embeddings[:-1]]
        return round(sum(scores) / len(scores), 2)

    async def run(self, request: QueryRequest, user_id: str | None = None) -> QueryResponse:
        started = time.time()
        clean_query = self.pii_filter.redact(request.query)
        metadata_filters = extract_query_metadata(clean_query)
        logger.info("query_metadata_extracted", filters=metadata_filters)
        cache_key = hashlib.md5(
            (
                "citation-v6-rrf-cache:"
                f"{user_id or 'anonymous'}:"
                f"{metadata_filters}:"
                f"{clean_query}:"
                f"{sorted(request.layer_filter or [])}:"
                f"{request.include_graph_context}"
            ).encode("utf-8")
        ).hexdigest()
        cached = await get_cache(cache_key)
        if cached and not request.bypass_cache:
            return QueryResponse(**json.loads(cached))

        expanded_queries = await expand_query(clean_query)
        layer_filter = [layer.value if hasattr(layer, "value") else layer for layer in (request.layer_filter or [])] or None
        embeddings = await self.embedder.embed_many(expanded_queries) if local_embeddings_available() else [[] for _ in expanded_queries]

        ranked_lists: list[list[dict]] = []
        seen_ids: set[str] = set()
        for expanded, embedding in zip(expanded_queries, embeddings):
            ranked = self.hybrid_search.search(
                query_text=expanded,
                query_embedding=embedding,
                layer_filter=layer_filter,
                top_k=settings.RETRIEVAL_TOP_K,
                metadata_filters=metadata_filters,
            )
            ranked_lists.append(ranked)
            seen_ids.update(chunk["id"] for chunk in ranked)

        all_chunks = self.hybrid_search.fuse_ranked_lists(ranked_lists, top_k=settings.RETRIEVAL_TOP_K)

        if request.include_graph_context and all_chunks:
            if self.graph_retriever is None:
                self.graph_retriever = GraphRetriever(RegulatoryKnowledgeGraph(self.db))
            for chunk in self.graph_retriever.fetch_related([item["id"] for item in all_chunks[:10]]):
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    all_chunks.append(chunk)
            all_chunks = self.hybrid_search.fuse_ranked_lists([all_chunks], top_k=settings.RETRIEVAL_TOP_K)

        if self.reranker.client and not self.reranker.__class__._disabled:
            reranked = await self.reranker.rerank(
                query=clean_query,
                chunks=all_chunks,
                top_n=max(settings.RERANK_TOP_N * 2, settings.RERANK_TOP_N),
            )
        else:
            reranked = all_chunks[: max(settings.RERANK_TOP_N * 2, settings.RERANK_TOP_N)]
        resolved_chunks, resolution_note = self.resolver.resolve(reranked[: settings.RERANK_TOP_N])
        source_relevance = check_query_source_relevance(clean_query, resolved_chunks)

        if not source_relevance["is_relevant"]:
            compressed_chunks: list[dict] = []
            llm_result = {
                "answer": "Insufficient evidence in provided regulatory sources.",
                "key_facts": ["No retrieved source sufficiently matched the important terms in the question."],
                "resolution_hierarchy": resolution_note or "",
                "confidence": 0.0,
                "insufficient_evidence": True,
                "refusal_reason": "Retrieved sources are not relevant to the query.",
                "_model_used": "query-source-relevance-gate",
                "_chunk_map": {},
            }
        else:
            compressed_chunks = await self._compress_chunks(clean_query, resolved_chunks)
            llm_result = await generate_cited_answer(clean_query, compressed_chunks, resolution_note, intent=None)

        grounding_score = await self._compute_grounding_score(llm_result.get("answer", ""), compressed_chunks)
        llm_result["_grounding_score"] = grounding_score
        if grounding_score < 0.60:
            llm_result["confidence"] = min(float(llm_result.get("confidence", 0.0)), 0.45)

        if not self.groundedness.verify(llm_result.get("answer", ""), compressed_chunks):
            llm_result["confidence"] = min(float(llm_result.get("confidence", 0.0)), 0.60)

        cited_chunks = source_citations_from_result(llm_result)
        cited_source_relevance = check_query_source_relevance(clean_query, cited_chunks)
        if cited_chunks and not cited_source_relevance["is_relevant"]:
            source_relevance = cited_source_relevance
            llm_result = {
                "answer": "Insufficient evidence in provided regulatory sources.",
                "key_facts": ["The retrieved citation did not sufficiently match the question topic."],
                "resolution_hierarchy": resolution_note or "",
                "confidence": 0.0,
                "insufficient_evidence": True,
                "refusal_reason": "Cited source is not relevant to the query.",
                "_model_used": "query-source-relevance-gate",
                "_chunk_map": {},
                "_grounding_score": grounding_score,
            }
            cited_chunks = []

        faithfulness = check_citation_faithfulness(llm_result.get("answer", ""), cited_chunks)
        llm_result["_citation_faithfulness_scores"] = {
            item["citation_id"]: item for item in faithfulness.get("scores", [])
        }
        citation_mismatch = not faithfulness["is_faithful"]
        citation_cards = build_citation_cards(llm_result, compressed_chunks)
        confidence = calculate_confidence(
            citations=citation_cards,
            faithfulness=faithfulness,
            retrieval_scores=[citation.relevance_score for citation in citation_cards],
        )
        confidence = min(confidence, float(llm_result.get("confidence", confidence)))
        if bool(llm_result.get("insufficient_evidence", False)):
            confidence = min(confidence, 0.2)
        if citation_mismatch:
            confidence = min(confidence, 0.25)
        if grounding_score < 0.60:
            confidence = min(confidence, 0.45)

        requires_review = confidence < settings.HITL_CONFIDENCE_TRIGGER
        latency_ms = int((time.time() - started) * 1000)
        query_payload = dict(
            original_query=request.query,
            clean_query=clean_query,
            expanded_queries=expanded_queries,
            layer_filter=layer_filter or [],
            answer=llm_result.get("answer", ""),
            confidence=confidence,
            resolution_note=resolution_note,
            latency_ms=latency_ms,
            model_used=llm_result.get("_model_used", "generic-rag"),
            chunk_ids_used=[chunk["id"] for chunk in resolved_chunks],
            requires_review=requires_review,
            user_id=user_id,
        )
        query_record = self.query_repo.get_recent_duplicate(
            original_query=request.query,
            user_id=user_id,
            minutes=5,
        )
        if query_record is None:
            query_record = self.query_repo.create(**query_payload)

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
            source_relevance_score=source_relevance.get("score"),
            source_relevance_warning=(
                "Retrieved sources do not sufficiently match the question topic."
                if not source_relevance.get("is_relevant")
                else None
            ),
            grounding_score=grounding_score,
        )

        if confidence >= settings.HITL_CONFIDENCE_TRIGGER:
            await set_cache(cache_key, response.model_dump_json(), ttl=settings.CACHE_TTL_SECONDS)

        logger.info("pipeline_complete", latency_ms=latency_ms, confidence=confidence, grounding_score=grounding_score)
        return response

        expanded_queries = await expand_query(clean_query)
        all_chunks: list[dict] = []
        seen_ids: set[str] = set()
        layer_filter = [layer.value if hasattr(layer, "value") else layer for layer in (request.layer_filter or [])] or None

        exact_keyword_intents = {
            "timeline",
            "compensation",
            "cir_borrower_details",
            "risk_segmentation",
            "credit_data_submission",
            "data_validation",
            "data_cleansing",
            "internal_audit_mechanism",
            "score_refresh_frequency",
            "tat",
        }

        # Exact regulatory/SOP intents are faster and safer with BM25 + boosts.
        if intent["intent"] in exact_keyword_intents:
            embeddings = [[] for _ in expanded_queries]
        elif local_embeddings_available():
            embeddings = await self.embedder.embed_many(expanded_queries)
        else:
            embeddings = [[] for _ in expanded_queries]

        for expanded, embedding in zip(expanded_queries, embeddings):
            for chunk in self.hybrid_search.search(
                query_text=expanded,
                query_embedding=embedding,
                layer_filter=layer_filter,
                top_k=settings.RETRIEVAL_TOP_K,
                intent=intent,
            ):
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    all_chunks.append(chunk)

        retrieval_query = " ".join(expanded_queries)
        all_chunks = self.hybrid_search.apply_exact_match_boost(retrieval_query, all_chunks)
        all_chunks = self.hybrid_search.intent_aware_filter(all_chunks, intent)
        exact_intent_evidence = any(
            chunk.get("timeline_rule_match")
            or chunk.get("compensation_rule_match")
            or chunk.get("cir_borrower_details_match")
            or chunk.get("risk_segmentation_match")
            or chunk.get("credit_data_submission_match")
            or chunk.get("consent_clause_match")
            or chunk.get("cbis_validation_pipeline_match")
            or chunk.get("internal_audit_mechanism_match")
            or chunk.get("score_refresh_tat_match")
            or chunk.get("score_refresh_frequency_match")
            for chunk in all_chunks
        )

        if request.include_graph_context and all_chunks and not exact_intent_evidence:
            if self.graph_retriever is None:
                self.graph_retriever = GraphRetriever(RegulatoryKnowledgeGraph(self.db))
            for chunk in self.graph_retriever.fetch_related([item["id"] for item in all_chunks[:10]]):
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    all_chunks.append(chunk)
            all_chunks = self.hybrid_search.apply_exact_match_boost(retrieval_query, all_chunks)
            all_chunks = self.hybrid_search.intent_aware_filter(all_chunks, intent)

        query_lower = clean_query.lower()
        preferred_cluster_key = None
        if intent["intent"] == "compensation":
            preferred_cluster_key = "compensation_rule_match"
        elif intent["intent"] == "cir_borrower_details":
            preferred_cluster_key = "cir_borrower_details_match"
        elif intent["intent"] == "risk_segmentation":
            preferred_cluster_key = "risk_segmentation_match"
        elif intent["intent"] == "credit_data_submission":
            preferred_cluster_key = "credit_data_submission_match"
        elif intent["intent"] == "timeline" or (
            "dispute" in query_lower and ("timeline" in query_lower or "resolution" in query_lower)
        ):
            preferred_cluster_key = "dispute_cluster_match"
        elif "consent" in query_lower or "borrower" in query_lower:
            preferred_cluster_key = "consent_clause_match"
        elif intent["intent"] == "data_validation":
            preferred_cluster_key = "cbis_validation_pipeline_match"
        elif intent["intent"] == "data_cleansing":
            preferred_cluster_key = "data_cleansing_rule_match"
        elif intent["intent"] == "internal_audit_mechanism":
            preferred_cluster_key = "internal_audit_mechanism_match"
        elif intent["intent"] == "score_refresh_frequency":
            preferred_cluster_key = "score_refresh_frequency_match"
        elif intent["intent"] == "tat":
            preferred_cluster_key = "score_refresh_tat_match"

        has_preferred_cluster = False
        if preferred_cluster_key:
            if preferred_cluster_key == "dispute_cluster_match":
                preferred = [
                    chunk
                    for chunk in all_chunks
                    if chunk.get("timeline_rule_match")
                ]
            elif preferred_cluster_key == "compensation_rule_match":
                preferred = [
                    chunk
                    for chunk in all_chunks
                    if chunk.get("compensation_rule_match")
                ]
            else:
                preferred = [chunk for chunk in all_chunks if chunk.get(preferred_cluster_key)]
            if preferred:
                has_preferred_cluster = True
                if preferred_cluster_key in {
                    "cbis_validation_pipeline_match",
                    "cir_borrower_details_match",
                    "risk_segmentation_match",
                    "credit_data_submission_match",
                    "data_cleansing_rule_match",
                    "internal_audit_mechanism_match",
                    "score_refresh_frequency_match",
                    "score_refresh_tat_match",
                }:
                    all_chunks = preferred
                else:
                    all_chunks = preferred + [chunk for chunk in all_chunks if not chunk.get(preferred_cluster_key)]

        top_score = float(all_chunks[0].get("exact_match_score", all_chunks[0].get("relevance_score", 0.0))) if all_chunks else 0.0
        if has_preferred_cluster or (not preferred_cluster_key and top_score >= 1.0) or top_score >= 0.8:
            reranked = all_chunks[: settings.RERANK_TOP_N]
        else:
            rerank_top_n = max(settings.RERANK_TOP_N * 2, settings.RERANK_TOP_N)
            reranked = await self.reranker.rerank(query=retrieval_query, chunks=all_chunks, top_n=rerank_top_n)
            reranked = self.hybrid_search.apply_exact_match_boost(retrieval_query, reranked)
            reranked = self.hybrid_search.intent_aware_filter(reranked, intent)
            reranked = reranked[: settings.RERANK_TOP_N]
        resolved_chunks, resolution_note = self.resolver.resolve(reranked)
        source_relevance = check_query_source_relevance(clean_query, resolved_chunks)
        if not source_relevance["is_relevant"]:
            resolved_chunks = []
            llm_result = {
                "answer": "Insufficient evidence in provided regulatory sources.",
                "key_facts": [
                    "No retrieved source sufficiently matched the important terms in the question."
                ],
                "resolution_hierarchy": resolution_note or "",
                "confidence": 0.0,
                "insufficient_evidence": True,
                "refusal_reason": "Retrieved sources are not relevant to the query.",
                "_model_used": "query-source-relevance-gate",
                "_chunk_map": {},
            }
        else:
            llm_result = await generate_cited_answer(clean_query, resolved_chunks, resolution_note, intent=intent)
        llm_result["_query_source_relevance"] = source_relevance

        if not self.groundedness.verify(llm_result.get("answer", ""), resolved_chunks):
            llm_result["confidence"] = min(float(llm_result.get("confidence", 0.0)), 0.60)

        cited_chunks = source_citations_from_result(llm_result)
        cited_source_relevance = check_query_source_relevance(clean_query, cited_chunks)
        if not cited_source_relevance["is_relevant"]:
            source_relevance = cited_source_relevance
            llm_result = {
                "answer": "Insufficient evidence in provided regulatory sources.",
                "key_facts": [
                    "The retrieved citation did not sufficiently match the question topic."
                ],
                "resolution_hierarchy": resolution_note or "",
                "confidence": 0.0,
                "insufficient_evidence": True,
                "refusal_reason": "Cited source is not relevant to the query.",
                "_model_used": "query-source-relevance-gate",
                "_chunk_map": {},
                "_query_source_relevance": source_relevance,
            }
            cited_chunks = []
        faithfulness = check_citation_faithfulness(llm_result.get("answer", ""), cited_chunks)
        llm_result["_citation_faithfulness_scores"] = {
            item["citation_id"]: item for item in faithfulness.get("scores", [])
        }
        citation_mismatch = not faithfulness["is_faithful"]
        citation_cards = build_citation_cards(llm_result, resolved_chunks)
        confidence = calculate_confidence(
            citations=citation_cards,
            faithfulness=faithfulness,
            retrieval_scores=[citation.relevance_score for citation in citation_cards],
        )
        if bool(llm_result.get("insufficient_evidence", False)):
            confidence = min(confidence, 0.2)
        if citation_mismatch:
            confidence = min(confidence, 0.25)
        requires_review = confidence < settings.HITL_CONFIDENCE_TRIGGER
        latency_ms = int((time.time() - started) * 1000)

        query_payload = dict(
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
        query_record = self.query_repo.get_recent_duplicate(
            original_query=request.query,
            user_id=user_id,
            minutes=5,
        )
        if query_record is None:
            query_record = self.query_repo.create(**query_payload)

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
            source_relevance_score=source_relevance.get("score"),
            source_relevance_warning=(
                "Retrieved sources do not sufficiently match the question topic."
                if not source_relevance.get("is_relevant")
                else None
            ),
        )

        if confidence >= settings.HITL_CONFIDENCE_TRIGGER:
            await set_cache(cache_key, response.model_dump_json(), ttl=settings.CACHE_TTL_SECONDS)

        logger.info("pipeline_complete", latency_ms=latency_ms, confidence=confidence)
        return response

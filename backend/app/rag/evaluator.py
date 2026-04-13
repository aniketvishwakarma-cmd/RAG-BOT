from __future__ import annotations

from app.core.constants import HIGH_CONFIDENCE_THRESHOLD, MEDIUM_CONFIDENCE_THRESHOLD


class ResponseEvaluator:
    def label_confidence(self, score: float) -> str:
        if score >= HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        if score >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "medium"
        return "low"

    def summarize(self, score: float, citation_count: int) -> dict:
        return {
            "confidence_score": score,
            "confidence_label": self.label_confidence(score),
            "citation_count": citation_count,
        }

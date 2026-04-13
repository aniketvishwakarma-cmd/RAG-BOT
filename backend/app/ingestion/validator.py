from __future__ import annotations


class HITLValidator:
    def needs_review(self, confidence: float) -> bool:
        return confidence < 0.75

    def build_review_payload(self, query_id: str, confidence: float, reason: str) -> dict:
        return {
            "query_id": query_id,
            "confidence": confidence,
            "reason": reason,
            "status": "pending",
        }


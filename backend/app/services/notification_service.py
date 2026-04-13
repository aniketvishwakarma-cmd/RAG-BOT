from __future__ import annotations


class NotificationService:
    def low_confidence_alert(self, query_id: str, confidence: float) -> dict:
        return {
            "type": "low_confidence",
            "query_id": query_id,
            "confidence": confidence,
            "message": "Response requires auditor review before operational reliance.",
        }


from __future__ import annotations

import re


class GroundednessChecker:
    def verify(self, answer: str, chunks: list[dict]) -> bool:
        if "Insufficient evidence" in answer:
            return True
        if not re.findall(r"\[SRC_\d+\]", answer):
            return False
        combined = " ".join(chunk.get("content", "").lower() for chunk in chunks[:8])
        for sentence in [part.strip() for part in re.split(r"(?<=[.!?])\s+", answer) if part.strip()]:
            normalized = re.sub(r"\[SRC_\d+\]", "", sentence).strip().lower()
            if not normalized or normalized.startswith("insufficient"):
                continue
            anchors = normalized.split()[:5]
            if anchors and not any(anchor in combined for anchor in anchors):
                return False
        return True


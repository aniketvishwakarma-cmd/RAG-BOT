from __future__ import annotations

import re

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None


class EntityExtractor:
    def __init__(self) -> None:
        self.nlp = None
        if spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                self.nlp = None

    def extract(self, text: str) -> list[dict]:
        entities = []
        patterns = {
            "TIMELINE": r"\b(21|9|30)\s+(?:calendar\s+)?days?\b",
            "CONSUMER_PENALTY": r"₹\s?100\s*/?\s*day",
            "REGULATOR_PENALTY": r"₹\s?5,?000\s*/?\s*day",
            "SOURCE": r"\b(RBI|CICRA|SOP|circular)\b",
        }
        for label, pattern in patterns.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                entities.append({"text": match.group(0), "label": label})
        if self.nlp:
            doc = self.nlp(text)
            entities.extend({"text": ent.text, "label": ent.label_} for ent in doc.ents[:20])
        return entities


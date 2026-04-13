from __future__ import annotations

import re

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
except Exception:  # pragma: no cover
    AnalyzerEngine = None
    AnonymizerEngine = None


class PIIFilter:
    def __init__(self) -> None:
        self.analyzer = AnalyzerEngine() if AnalyzerEngine else None
        self.anonymizer = AnonymizerEngine() if AnonymizerEngine else None

    def redact(self, text: str) -> str:
        if self.analyzer and self.anonymizer:
            results = self.analyzer.analyze(text=text, language="en")
            if results:
                return self.anonymizer.anonymize(text=text, analyzer_results=results).text
        text = re.sub(r"\b\d{12}\b", "[REDACTED_ID]", text)
        text = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[REDACTED_PAN]", text, flags=re.IGNORECASE)
        text = re.sub(r"\b\d{10}\b", "[REDACTED_PHONE]", text)
        return text


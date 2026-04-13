from __future__ import annotations

import re


class StructureExtractor:
    CHAPTER_RE = re.compile(r"^(Chapter\s+[IVXLC]+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
    SECTION_RE = re.compile(r"^((?:Section\s+)?\d+(?:\.\d+)*)\s*[:\-]?\s*(.*)$", re.IGNORECASE)

    def summarize(self, text: str) -> dict:
        chapters = []
        sections = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if match := self.CHAPTER_RE.match(stripped):
                chapters.append({"chapter": match.group(1), "heading": match.group(2)})
            elif match := self.SECTION_RE.match(stripped):
                sections.append({"section": match.group(1), "heading": match.group(2)})
        return {
            "chapter_count": len(chapters),
            "section_count": len(sections),
            "chapters": chapters[:20],
            "sections": sections[:50],
        }


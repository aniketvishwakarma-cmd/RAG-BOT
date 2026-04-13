from __future__ import annotations

import re
import uuid
from typing import Dict, List

from app.core.config import settings


class RegulatoryChunker:
    SECTION_PATTERNS = [
        r"^(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)\s+(.+)$",
        r"^(Chapter\s+[IVXLC]+)\s*[:\-]?\s*(.+)$",
        r"^(Section\s+\d+)\s*[:\-]?\s*(.+)$",
        r"^([A-Z]\.\d+)\s+(.+)$",
    ]

    def chunk(self, text: str, doc_meta: dict) -> List[Dict]:
        chunks = []
        for section in self._split_into_sections(text):
            chunks.extend(self._chunk_section(section, doc_meta))
        return chunks

    def _split_into_sections(self, text: str) -> List[Dict]:
        sections = []
        current = {"heading": None, "section_no": None, "text": "", "page_no": None, "chapter": None}

        for line in text.split("\n"):
            matched = False
            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line.strip(), re.IGNORECASE)
                if match:
                    if current["text"].strip():
                        sections.append(dict(current))
                    current = {
                        "section_no": match.group(1),
                        "heading": match.group(2).strip(),
                        "text": line + "\n",
                        "page_no": current.get("page_no"),
                        "chapter": match.group(1) if str(match.group(1)).lower().startswith("chapter") else current.get("chapter"),
                    }
                    matched = True
                    break
            if not matched:
                page_match = re.match(r"^\s*[-–]\s*(\d+)\s*[-–]\s*$", line)
                if page_match:
                    current["page_no"] = int(page_match.group(1))
                else:
                    current["text"] += line + "\n"

        if current["text"].strip():
            sections.append(current)
        return sections

    def _chunk_section(self, section: Dict, doc_meta: dict) -> List[Dict]:
        text = section["text"].strip()
        if len(text.split()) <= settings.CHUNK_MAX_TOKENS:
            return [self._build_chunk(text, section, doc_meta)]

        result = []
        current_text = ""
        current_words = 0
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            size = len(sentence.split())
            if current_words + size > settings.CHUNK_MAX_TOKENS and current_text:
                result.append(self._build_chunk(current_text.strip(), section, doc_meta))
                current_text = sentence + " "
                current_words = size
            else:
                current_text += sentence + " "
                current_words += size
        if current_text.strip():
            result.append(self._build_chunk(current_text.strip(), section, doc_meta))
        return result

    def _build_chunk(self, text: str, section: Dict, doc_meta: dict) -> Dict:
        section_no = section.get("section_no", "")
        clause_parts = section_no.split(".") if section_no else []
        return {
            "id": str(uuid.uuid4()),
            "content": text,
            "bm25_text": text.lower(),
            "token_count": len(text.split()),
            "source_layer": doc_meta.get("source_layer", "UNKNOWN"),
            "document_id": doc_meta.get("document_id"),
            "section_no": section_no,
            "clause_no": ".".join(clause_parts[:3]) if len(clause_parts) >= 3 else section_no,
            "paragraph_no": clause_parts[3] if len(clause_parts) > 3 else None,
            "chapter": section.get("chapter"),
            "heading": section.get("heading"),
            "page_no": section.get("page_no"),
            "effective_date": doc_meta.get("effective_date"),
            "priority_rank": doc_meta.get("priority_rank", 4),
            "is_superseded": False,
        }

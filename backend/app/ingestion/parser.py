from __future__ import annotations

from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup
from docx import Document as DocxDocument


class DocumentParser:
    def parse_file(self, file_path: str) -> tuple[str, int]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path)
        if suffix in {".docx", ".doc"}:
            return self._parse_docx(path)
        if suffix in {".html", ".htm"}:
            return self._parse_html(path)
        return path.read_text(encoding="utf-8", errors="ignore"), 1

    def _parse_pdf(self, path: Path) -> tuple[str, int]:
        pages: list[str] = []
        with pdfplumber.open(path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(f"\n- {index} -\n{text}")
        return "\n".join(pages), len(pages)

    def _parse_docx(self, path: Path) -> tuple[str, int]:
        doc = DocxDocument(path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs), 1

    def _parse_html(self, path: Path) -> tuple[str, int]:
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text("\n"), 1


from __future__ import annotations

import re


class TextCleaner:
    def clean(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ ]+\n", "\n", text)
        return text.strip()

    def deduplicate_lines(self, text: str) -> str:
        seen = set()
        output = []
        for line in text.splitlines():
            normalized = line.strip().lower()
            if normalized and normalized in seen:
                continue
            if normalized:
                seen.add(normalized)
            output.append(line)
        return "\n".join(output)


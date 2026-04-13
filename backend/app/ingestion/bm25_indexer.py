from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.db.models import Chunk


class BM25Indexer:
    def rebuild(self, chunks: list[Chunk]) -> str:
        payload = [
            {
                "id": chunk.id,
                "bm25_text": chunk.bm25_text,
                "source_layer": chunk.source_layer,
            }
            for chunk in chunks
        ]
        path = Path(settings.BM25_INDEX_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)


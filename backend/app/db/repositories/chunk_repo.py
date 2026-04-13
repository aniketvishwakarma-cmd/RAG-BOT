from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import Chunk


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, chunks: Iterable[dict]) -> list[Chunk]:
        items = [Chunk(**chunk) for chunk in chunks]
        self.db.add_all(items)
        self.db.commit()
        for item in items:
            self.db.refresh(item)
        return items

    def list_active(self) -> list[Chunk]:
        return self.db.query(Chunk).filter(Chunk.is_superseded.is_(False)).all()

    def get(self, chunk_id: str) -> Optional[Chunk]:
        return self.db.query(Chunk).filter(Chunk.id == chunk_id).first()


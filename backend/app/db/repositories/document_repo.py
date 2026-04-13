from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Document:
        document = Document(**kwargs)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def list(self) -> list[Document]:
        return self.db.query(Document).order_by(Document.created_at.desc()).all()

    def get(self, document_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def delete(self, document_id: str) -> bool:
        document = self.get(document_id)
        if not document:
            return False
        self.db.delete(document)
        self.db.commit()
        return True

    def update_chunk_count(self, document_id: str, chunk_count: int) -> None:
        document = self.get(document_id)
        if not document:
            return
        document.chunk_count = chunk_count
        self.db.add(document)
        self.db.commit()

    def mark_superseded(self, document_id: str, superseded_by: str) -> None:
        document = self.get(document_id)
        if not document:
            return
        document.is_superseded = True
        document.is_active = False
        document.superseded_by = superseded_by
        self.db.add(document)
        self.db.commit()


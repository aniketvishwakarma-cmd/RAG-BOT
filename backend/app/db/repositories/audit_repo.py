from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> AuditLog:
        record = AuditLog(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list(self, page: int = 1, limit: int = 50) -> list[AuditLog]:
        offset = max(page - 1, 0) * max(limit, 1)
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )


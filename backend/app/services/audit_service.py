from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.audit_repo import AuditRepository
from app.db.repositories.query_repo import QueryRepository


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditRepository(db)
        self.query_repo = QueryRepository(db)

    def list_logs(self, page: int = 1, limit: int = 50):
        return self.audit_repo.list(page=page, limit=limit)

    def validate_query(self, query_id: str, status: str, reviewer_id: str | None = None, notes: str | None = None) -> dict:
        query = self.query_repo.get_by_id(query_id)
        if not query:
            raise ValueError("Query not found")
        query.review_status = status
        query.reviewed_by = reviewer_id
        self.db.add(query)
        self.db.commit()
        self.audit_repo.create(
            action="validate",
            entity_type="query",
            entity_id=query_id,
            user_id=reviewer_id,
            status="success",
            details={"status": status, "notes": notes or ""},
        )
        return {"query_id": query_id, "status": status, "notes": notes or ""}


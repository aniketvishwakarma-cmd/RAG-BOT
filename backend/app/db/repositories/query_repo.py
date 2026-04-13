from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Query


class QueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Query:
        query = Query(**kwargs)
        self.db.add(query)
        self.db.commit()
        self.db.refresh(query)
        return query

    def get_by_id(self, query_id: str) -> Optional[Query]:
        return self.db.query(Query).filter(Query.id == query_id).first()

    def get_paginated(self, page: int = 1, limit: int = 20) -> list[Query]:
        offset = max(page - 1, 0) * max(limit, 1)
        return (
            self.db.query(Query)
            .order_by(Query.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )


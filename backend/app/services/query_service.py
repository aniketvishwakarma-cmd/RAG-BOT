from __future__ import annotations

from sqlalchemy.orm import Session

from app.rag.pipeline import RAGPipeline
from app.schemas.query import QueryRequest, QueryResponse


class QueryService:
    def __init__(self, db: Session):
        self.pipeline = RAGPipeline(db)

    async def process(self, request: QueryRequest, user_id: str | None = None) -> QueryResponse:
        return await self.pipeline.run(request, user_id=user_id)


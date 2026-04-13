from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.repositories.query_repo import QueryRepository
from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_service import QueryService

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest, http_request: Request, db: Session = Depends(get_db)):
    if len(request.query.strip()) < 5:
        raise HTTPException(status_code=400, detail="Query too short")
    user = getattr(http_request.state, "user", None) or {}
    service = QueryService(db)
    try:
        return await service.process(request, user_id=user.get("id"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc


@router.get("/history")
async def get_query_history(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    repo = QueryRepository(db)
    return {"queries": repo.get_paginated(page=page, limit=limit), "page": page, "limit": limit}


@router.get("/{query_id}")
async def get_query_result(query_id: str, db: Session = Depends(get_db)):
    repo = QueryRepository(db)
    query = repo.get_by_id(query_id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    return query


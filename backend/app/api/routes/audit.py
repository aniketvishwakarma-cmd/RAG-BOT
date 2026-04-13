from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.audit import AuditValidationRequest
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/")
async def list_audit_logs(page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    service = AuditService(db)
    return {"logs": service.list_logs(page=page, limit=limit), "page": page, "limit": limit}


@router.post("/validate")
async def validate_query(payload: AuditValidationRequest, db: Session = Depends(get_db)):
    try:
        return AuditService(db).validate_query(
            query_id=payload.query_id,
            status=payload.status,
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


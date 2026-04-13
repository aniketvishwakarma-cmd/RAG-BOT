from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.repositories.document_repo import DocumentRepository
from app.db.session import get_db

router = APIRouter()


@router.get("/")
async def list_documents(db: Session = Depends(get_db)):
    return {"documents": DocumentRepository(db).list()}


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    if not DocumentRepository(db).delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "document_id": document_id}


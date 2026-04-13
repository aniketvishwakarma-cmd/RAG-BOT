from __future__ import annotations

from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("/")
async def ingest_existing_file(
    file_path: str = Form(...),
    title: str = Form(...),
    source_layer: str = Form(...),
    effective_date: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    service = IngestionService(db)
    return await service.ingest_file(
        file_path=file_path,
        title=title,
        source_layer=source_layer,
        effective_date=effective_date,
    )


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    source_layer: str = Form(...),
    effective_date: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    service = IngestionService(db)
    responses = []
    for file in files:
        destination = upload_dir / file.filename
        with destination.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        responses.append(
            await service.ingest_file(
                file_path=str(destination),
                title=destination.stem,
                source_layer=source_layer,
                effective_date=effective_date,
            )
        )
    return {"documents": responses}


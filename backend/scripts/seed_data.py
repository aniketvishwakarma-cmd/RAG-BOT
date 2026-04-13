from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.services.ingestion_service import IngestionService

SAMPLE_TEXT = """8.4 Reporting Delay
Delayed dispute resolution beyond 30 calendar days attracts compensation of Rs.100 per calendar day payable to the consumer.
The Credit Institution has 21 calendar days to respond and the Credit Information Company has 9 calendar days to close the dispute.
Reporting violations may separately attract supervisory action of Rs.5,000 per day.
"""


async def main() -> None:
    init_db()
    sample_dir = Path(settings.SAMPLE_DATA_DIR)
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_file = sample_dir / "sample_rbi_master.txt"
    if not sample_file.exists():
        sample_file.write_text(SAMPLE_TEXT, encoding="utf-8")

    db = SessionLocal()
    try:
        service = IngestionService(db)
        await service.ingest_file(
            file_path=str(sample_file),
            title="Sample RBI Master Direction",
            source_layer="RBI_MASTER",
            document_type="master_direction",
        )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
    print("Sample RBI seed data loaded.")

from app.db.repositories.chunk_repo import ChunkRepository
from app.db.session import SessionLocal, init_db
from app.ingestion.bm25_indexer import BM25Indexer


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        index_path = BM25Indexer().rebuild(ChunkRepository(db).list_active())
        print(f"BM25 index rebuilt at {index_path}")
    finally:
        db.close()


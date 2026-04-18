from __future__ import annotations

from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.constants import LAYER_PRIORITY
from app.core.exceptions import IngestionError
from app.db.repositories.chunk_repo import ChunkRepository
from app.db.repositories.document_repo import DocumentRepository
from app.graph.knowledge_graph import RegulatoryKnowledgeGraph
from app.ingestion.bm25_indexer import BM25Indexer
from app.ingestion.chunker import RegulatoryChunker
from app.ingestion.cleaner import TextCleaner
from app.ingestion.embedder import EmbeddingService
from app.ingestion.graph_builder import GraphBuilder
from app.ingestion.parser import DocumentParser
from app.ingestion.structure_extractor import StructureExtractor
from app.rag.hybrid_search import HybridSearchEngine


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.parser = DocumentParser()
        self.cleaner = TextCleaner()
        self.structure_extractor = StructureExtractor()
        self.chunker = RegulatoryChunker()
        self.embedder = EmbeddingService()
        self.bm25_indexer = BM25Indexer()
        self.knowledge_graph = RegulatoryKnowledgeGraph(db)
        self.graph_builder = GraphBuilder(self.knowledge_graph)

    async def ingest_file(
        self,
        file_path: str,
        title: str,
        source_layer: str,
        uploaded_by: str | None = "system",
        effective_date=None,
        document_type: str | None = "circular",
        source_url: str | None = None,
    ) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise IngestionError(f"File not found: {file_path}")

        raw_text, page_count = self.parser.parse_file(str(path))
        cleaned_text = self.cleaner.deduplicate_lines(self.cleaner.clean(raw_text))
        structure = self.structure_extractor.summarize(cleaned_text)

        parsed_effective_date = effective_date
        if isinstance(effective_date, str) and effective_date:
            try:
                parsed_effective_date = datetime.fromisoformat(effective_date)
            except ValueError:
                parsed_effective_date = None

        document = self.document_repo.create(
            title=title,
            source_layer=source_layer,
            regulator="RBI" if "RBI" in source_layer else "CICRA",
            document_type=document_type,
            effective_date=parsed_effective_date,
            source_url=source_url,
            file_path=str(path),
            raw_text=cleaned_text,
            page_count=page_count,
            uploaded_by=uploaded_by,
            metadata_json=structure,
        )
        self.knowledge_graph.add_document_node(document)

        chunk_dicts = self.chunker.chunk(
            cleaned_text,
            {
                "document_id": document.id,
                "title": document.title,
                "source_layer": source_layer,
                "effective_date": parsed_effective_date,
                "priority_rank": LAYER_PRIORITY.get(source_layer, 4),
            },
        )
        embeddings = await self.embedder.embed_many([chunk["content"] for chunk in chunk_dicts])
        for chunk, embedding in zip(chunk_dicts, embeddings):
            chunk["embedding"] = embedding
        stored_chunks = self.chunk_repo.bulk_create(chunk_dicts)
        self.document_repo.update_chunk_count(document.id, len(stored_chunks))
        self.bm25_indexer.rebuild(self.chunk_repo.list_active())
        HybridSearchEngine.invalidate_bm25_cache()
        self.graph_builder.build_for_document(document.id, chunk_dicts)

        return {
            "document_id": document.id,
            "title": document.title,
            "chunk_count": len(stored_chunks),
            "status": "processed",
        }

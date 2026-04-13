from __future__ import annotations

from datetime import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    source_layer = Column(String(50), nullable=False)
    regulator = Column(String(200))
    document_type = Column(String(100))
    effective_date = Column(DateTime, nullable=True)
    version = Column(String(50), default="1.0")
    source_url = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superseded = Column(Boolean, default=False)
    superseded_by = Column(String, ForeignKey("documents.id"), nullable=True)
    raw_text = Column(Text)
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    uploaded_by = Column(String(200), nullable=True)
    validated_by = Column(String(200), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    source_layer = Column(String(50))
    chapter = Column(String(200), nullable=True)
    section_no = Column(String(100), nullable=True)
    clause_no = Column(String(100), nullable=True)
    paragraph_no = Column(String(100), nullable=True)
    page_no = Column(Integer, nullable=True)
    heading = Column(String(500), nullable=True)
    effective_date = Column(DateTime, nullable=True)
    priority_rank = Column(Integer, default=4)
    bm25_text = Column(Text)
    token_count = Column(Integer, default=0)
    is_superseded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class Query(Base):
    __tablename__ = "queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String(200), nullable=True)
    original_query = Column(Text, nullable=False)
    clean_query = Column(Text, nullable=True)
    expanded_queries = Column(JSON, default=list)
    layer_filter = Column(JSON, default=list)
    answer = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    resolution_note = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0)
    model_used = Column(String(100), nullable=True)
    chunk_ids_used = Column(JSON, default=list)
    requires_review = Column(Boolean, default=False)
    reviewed_by = Column(String(200), nullable=True)
    review_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    citations = relationship("Citation", back_populates="query", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(String, primary_key=True, default=generate_uuid)
    query_id = Column(String, ForeignKey("queries.id"), nullable=False)
    chunk_id = Column(String, ForeignKey("chunks.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    source_name = Column(String(500))
    source_layer = Column(String(50))
    section_no = Column(String(100), nullable=True)
    clause_no = Column(String(100), nullable=True)
    paragraph_no = Column(String(100), nullable=True)
    page_no = Column(Integer, nullable=True)
    excerpt = Column(Text)
    relevance_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", back_populates="citations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    action = Column(String(200))
    entity_type = Column(String(100))
    entity_id = Column(String)
    user_id = Column(String(200), nullable=True)
    ip_address = Column(String(50), nullable=True)
    status = Column(String(50))
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class GraphRelation(Base):
    __tablename__ = "graph_relations"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    source_type = Column(String(50))
    target_type = Column(String(50))
    relation = Column(String(100))
    confidence = Column(Float, default=1.0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


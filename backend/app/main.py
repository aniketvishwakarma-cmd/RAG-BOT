from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.auth import AuthContextMiddleware
from app.api.middleware.rate_limiter import RateLimitMiddleware
from app.api.middleware.request_logger import AuditRequestLoggerMiddleware
from app.api.routes import audit, documents, graph, health, ingest, query
from app.core.config import settings
from app.core.logger import configure_logging
from app.db.session import init_db
from app.db.session import SessionLocal
from app.ingestion.embedder import LocalEmbedder, local_embeddings_available
from app.rag.hybrid_search import HybridSearchEngine

configure_logging()
logger = structlog.get_logger()


def _warm_retrieval_assets() -> None:
    if local_embeddings_available():
        try:
            LocalEmbedder.get_instance().embed_text("warm up local regulatory retrieval model")
            logger.info("local_embedding_model_warmed", model=settings.LOCAL_EMBEDDING_MODEL)
        except Exception as exc:
            logger.warning("local_embedding_model_warmup_failed", error=str(exc))
    db = SessionLocal()
    try:
        HybridSearchEngine(db)
        logger.info("bm25_index_warmed")
    except Exception as exc:
        logger.warning("bm25_index_warmup_failed", error=str(exc))
    finally:
        db.close()


async def _warm_retrieval_assets_background() -> None:
    await asyncio.to_thread(_warm_retrieval_assets)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION)
    init_db()
    asyncio.create_task(_warm_retrieval_assets_background())
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Knowledge-Graph Enhanced Regulatory Compliance RAG System",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditRequestLoggerMiddleware)

app.include_router(query.router, prefix="/api/v1/query", tags=["Query"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Ingestion"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Knowledge Graph"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

from __future__ import annotations

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

configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, version=settings.APP_VERSION)
    init_db()
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

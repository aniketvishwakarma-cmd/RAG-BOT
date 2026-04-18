from __future__ import annotations

import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.repositories.audit_repo import AuditRepository
from app.db.session import SessionLocal

logger = structlog.get_logger()


class AuditRequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.time()
        if request.url.path.startswith("/api/v1/query"):
            logger.info("request_logger_passthrough", path=request.url.path)
        response = await call_next(request)
        latency_ms = int((time.time() - started) * 1000)
        if request.url.path.startswith("/api/v1/query"):
            return response

        db = SessionLocal()
        try:
            try:
                AuditRepository(db).create(
                    action="request",
                    entity_type="http_request",
                    entity_id=request.url.path,
                    user_id=(getattr(request.state, "user", {}) or {}).get("id"),
                    ip_address=request.client.host if request.client else None,
                    status="success" if response.status_code < 400 else "failure",
                    details={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                    },
                )
            except Exception as exc:
                db.rollback()
                logger.warning("request_audit_log_failed", path=request.url.path, error=str(exc))
        finally:
            db.close()

        return response


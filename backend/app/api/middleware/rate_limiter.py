from __future__ import annotations

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.db.redis_client import increment_rate_limit

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/query"):
            logger.info("rate_limit_skipped", path=request.url.path)
            return await call_next(request)
        client_ip = request.client.host if request.client else "anonymous"
        user = getattr(request.state, "user", None) or {}
        subject = user.get("id") if isinstance(user, dict) else None
        key = f"ratelimit:{subject or client_ip}"
        current = await increment_rate_limit(key, ttl=60)
        if current > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
            )
        return await call_next(request)


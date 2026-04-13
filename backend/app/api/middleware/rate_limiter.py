from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.db.redis_client import increment_rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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


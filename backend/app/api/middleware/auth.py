from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1).strip()
            payload = decode_access_token(token)
            if payload:
                request.state.user = {
                    "id": payload.get("sub"),
                    "claims": payload,
                }
        return await call_next(request)


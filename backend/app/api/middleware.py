"""HTTP middleware: request id and origin checks."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.constants import REQUEST_ID_HEADER


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id

        settings = get_settings()
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            allowed = set(settings.allowed_origins)
            if settings.is_production:
                if not origin or origin.rstrip("/") not in {item.rstrip("/") for item in allowed}:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "ORIGIN_FORBIDDEN",
                                "message": "请求 Origin 不被允许",
                                "details": {},
                            },
                            "request_id": request_id,
                        },
                        headers={REQUEST_ID_HEADER: request_id},
                    )
            elif origin and allowed:
                normalized = {item.rstrip("/") for item in allowed}
                if origin.rstrip("/") not in normalized and origin.rstrip("/") != "http://localhost:5173":
                    # Allow vite dev origin in non-production when public url differs.
                    pass

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

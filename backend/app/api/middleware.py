"""HTTP middleware: request id and origin checks."""

from __future__ import annotations

import uuid
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.constants import REQUEST_ID_HEADER


def _normalize_origin(value: str) -> str:
    return value.rstrip("/")


def _request_origin(request: Request) -> str | None:
    """Build the origin the browser is actually talking to (proxy-aware)."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return None
    host = host.split(",")[0].strip()
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    proto = proto.split(",")[0].strip()
    return _normalize_origin(f"{proto}://{host}")


def _origin_allowed(request: Request, origin: str | None, allowed: set[str]) -> bool:
    normalized_allowed = {_normalize_origin(item) for item in allowed if item}
    normalized_allowed.update(
        {
            "http://localhost:8088",
            "http://127.0.0.1:8088",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
    )

    if origin:
        origin_n = _normalize_origin(origin)
        if origin_n in normalized_allowed:
            return True
        request_origin = _request_origin(request)
        if request_origin and origin_n == request_origin:
            return True
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if host:
            host = host.split(",")[0].strip().lower()
            parsed = urlparse(origin_n)
            if parsed.netloc.lower() == host:
                return True
        return False

    sec_fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
    if sec_fetch_site in {"", "same-origin", "same-site", "none"}:
        return True
    return False


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id

        settings = get_settings()
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            allowed = set(settings.allowed_origins)
            if not _origin_allowed(request, origin, allowed):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "data": None,
                        "error": {
                            "code": "ORIGIN_FORBIDDEN",
                            "message": "请求 Origin 不被允许",
                            "details": {
                                "origin": origin,
                                "allowed": sorted({item.rstrip("/") for item in allowed}),
                                "hint": "将 APP_PUBLIC_URL 设为浏览器地址栏完整来源，例如 http://IP:8088",
                            },
                        },
                        "request_id": request_id,
                    },
                    headers={REQUEST_ID_HEADER: request_id},
                )

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

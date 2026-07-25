"""Response helpers."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.schemas.common import APIResponse, ErrorBody


def success_response(data: Any, request_id: str, *, status_code: int = 200) -> JSONResponse:
    payload: APIResponse[Any] = APIResponse(success=True, data=data, error=None, request_id=request_id)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def error_response(
    *,
    request_id: str,
    code: str,
    message: str,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: APIResponse[Any] = APIResponse(
        success=False,
        data=None,
        error=ErrorBody(code=code, message=message, details=details or {}),
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

"""Application error codes and exception types."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with stable error code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", *, details: dict[str, Any] | None = None) -> None:
        super().__init__("NOT_FOUND", message, status_code=404, details=details)


class ConflictError(AppError):
    def __init__(self, message: str, *, code: str = "CONFLICT", details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, status_code=409, details=details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或会话已失效") -> None:
        super().__init__("UNAUTHORIZED", message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权执行该操作") -> None:
        super().__init__("FORBIDDEN", message, status_code=403)


class ValidationAppError(AppError):
    def __init__(self, message: str, *, code: str = "VALIDATION_ERROR", details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, status_code=422, details=details)


class SetupRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "SETUP_REQUIRED",
            "系统尚未初始化，请先完成管理员创建",
            status_code=409,
        )


class SetupAlreadyCompletedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "SETUP_ALREADY_COMPLETED",
            "系统已完成初始化，不能重复执行 setup",
            status_code=409,
        )

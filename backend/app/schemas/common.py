"""Common API response envelopes and pagination schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorBody | None = None
    request_id: str


class PageMeta(BaseModel):
    items: list[Any]
    page: int
    page_size: int
    total: int
    total_pages: int


class HealthData(BaseModel):
    status: str = "ok"
    service: str = "LottoPilot"


class ReadyData(BaseModel):
    status: str
    database: str
    migrations: str
    detail: str | None = None


class SystemInfoData(BaseModel):
    app_name: str
    version: str
    git_commit: str
    build_time: str | None = None
    env: str
    latest_draws: dict[str, str | None] = Field(default_factory=dict)

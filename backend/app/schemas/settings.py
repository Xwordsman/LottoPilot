"""Backtest and AI configuration schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

LotteryType = Literal["ssq", "dlt"]


class BacktestCreateRequest(BaseModel):
    lottery_type: LotteryType
    start_issue: str
    end_issue: str
    seed: int | None = None
    baseline_trials: int = Field(default=20, ge=5, le=200)
    candidate_count: int = Field(default=2000, ge=500, le=50000)


class BacktestRunPublic(BaseModel):
    id: UUID
    job_id: UUID
    lottery_type: str
    strategy_profile_id: UUID
    start_issue: str
    end_issue: str
    seed: int | None
    baseline_trials: int
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BacktestListData(BaseModel):
    items: list[BacktestRunPublic]
    page: int
    page_size: int
    total: int
    total_pages: int


class AIConfigCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = "openai_compatible"
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
    is_default: bool = False


class AIConfigUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    is_default: bool | None = None
    is_active: bool | None = None


class AIConfigPublic(BaseModel):
    id: UUID
    name: str
    provider: str
    base_url: str
    model: str
    has_api_key: bool
    api_key_masked: str
    timeout_seconds: int
    max_tokens: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AITestResult(BaseModel):
    status: str
    model: str
    latency_ms: int

class SystemSettingsPublic(BaseModel):
    timezone: str = "Asia/Shanghai"
    recommendation_count: int = 5
    ai_weight_cap: float = 0.10
    candidate_pool_max: int = 50000
    scheduler_enabled: bool = True
    sync_cron: str = "5 21 * * 1,3,6"
    swagger_public: bool = True
    default_window: int = 50


class SystemSettingsUpdateRequest(BaseModel):
    timezone: str | None = None
    recommendation_count: int | None = Field(default=None, ge=1, le=20)
    ai_weight_cap: float | None = Field(default=None, ge=0, le=0.10)
    candidate_pool_max: int | None = Field(default=None, ge=500, le=100000)
    scheduler_enabled: bool | None = None
    sync_cron: str | None = None
    swagger_public: bool | None = None
    default_window: int | None = Field(default=None, ge=5, le=5000)

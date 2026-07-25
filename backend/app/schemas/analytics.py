"""Analytics API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LotteryType = Literal["ssq", "dlt"]


class AnalyticsQuery(BaseModel):
    lottery_type: LotteryType = "ssq"
    window: int | None = Field(default=50, ge=1, le=5000)


class NumberStat(BaseModel):
    number: int
    count: int
    ratio: float | None = None
    missing: int | None = None
    last_issue: str | None = None


class AnalyticsOverviewData(BaseModel):
    lottery_type: LotteryType
    metrics: dict[str, Any]
    hot_cold: dict[str, Any]
    frequency_primary: list[dict[str, Any]]
    missing_primary: list[dict[str, Any]]
    sum_span: list[dict[str, Any]]
    zones: list[dict[str, Any]]
    cooccurrence: list[dict[str, Any]]

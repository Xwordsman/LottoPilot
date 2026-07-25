"""Recommendation API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

LotteryType = Literal["ssq", "dlt"]


class RecommendationCreateRequest(BaseModel):
    lottery_type: LotteryType
    target_issue: str | None = None
    strategy_profile_id: UUID | None = None
    seed: int | None = None
    candidate_count: int | None = Field(default=None, ge=1000, le=200000)
    enable_ai: bool = True


class RecommendationTicketPublic(BaseModel):
    id: UUID
    rank: int
    primary_numbers: list[int]
    secondary_numbers: list[int]
    statistical_score: float
    ai_score: float | None = None
    final_score: float
    feature_summary: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = None
    primary_hits: int | None = None
    secondary_hits: int | None = None
    prize_level: str | None = None

    model_config = {"from_attributes": True}


class RecommendationEvaluationSummary(BaseModel):
    draw_issue: str | None = None
    best_rank: int | None = None
    best_primary_hits: int | None = None
    best_secondary_hits: int | None = None
    any_prize: bool = False
    prize_rule_version: str | None = None


class RecommendationRunPublic(BaseModel):
    id: UUID
    job_id: UUID
    lottery_type: str
    target_issue: str | None
    strategy_profile_id: UUID
    data_cutoff_issue: str | None
    data_snapshot_hash: str | None
    seed: int | None
    candidate_count: int
    ai_status: str
    ai_provider: str | None = None
    ai_model: str | None = None
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    evaluation: RecommendationEvaluationSummary | None = None
    created_at: datetime
    finished_at: datetime | None = None
    tickets: list[RecommendationTicketPublic] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RecommendationRunListData(BaseModel):
    items: list[RecommendationRunPublic]
    page: int
    page_size: int
    total: int
    total_pages: int
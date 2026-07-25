"""Recommendation models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import GUID, IntArray, JSONDoc


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    target_issue: Mapped[str | None] = mapped_column(String(20), nullable=True)
    strategy_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("strategy_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    data_cutoff_issue: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_config_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True
    )
    ai_status: Mapped[str] = mapped_column(String(20), nullable=False, default="skipped")
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ai_response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_metrics: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tickets: Mapped[list[RecommendationTicket]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RecommendationTicket(Base):
    __tablename__ = "recommendation_tickets"
    __table_args__ = (UniqueConstraint("run_id", "rank", name="uq_recommendation_ticket_rank"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    primary_numbers: Mapped[list[int]] = mapped_column(IntArray(), nullable=False)
    secondary_numbers: Mapped[list[int]] = mapped_column(IntArray(), nullable=False)
    statistical_score: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    ai_score: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    final_score: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    feature_summary: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    tags: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[RecommendationRun] = relationship(back_populates="tickets")


class RecommendationResult(Base):
    __tablename__ = "recommendation_results"
    __table_args__ = (UniqueConstraint("ticket_id", "draw_id", name="uq_recommendation_result_ticket_draw"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("recommendation_tickets.id", ondelete="CASCADE"), nullable=False
    )
    draw_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("draws.id", ondelete="CASCADE"), nullable=False
    )
    primary_hits: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    secondary_hits: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    prize_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    prize_rule_set_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("prize_rule_sets.id", ondelete="SET NULL"), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

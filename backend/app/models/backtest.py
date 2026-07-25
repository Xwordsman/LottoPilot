"""Backtest models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from app.db.types import GUID, JSONDoc
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    strategy_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("strategy_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    start_issue: Mapped[str] = mapped_column(String(20), nullable=False)
    end_issue: Mapped[str] = mapped_column(String(20), nullable=False)
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    baseline_trials: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BacktestIssueResult(Base):
    __tablename__ = "backtest_issue_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_draw_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("draws.id", ondelete="RESTRICT"), nullable=False
    )
    training_cutoff_draw_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("draws.id", ondelete="RESTRICT"), nullable=False
    )
    tickets: Mapped[list[dict[str, Any]]] = mapped_column(JSONDoc, nullable=False, default=list)
    hit_metrics: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    baseline_metrics: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    runtime_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

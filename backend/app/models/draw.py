"""Draw and ingestion models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from app.db.types import GUID, IntArray, JSONDoc
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Draw(Base):
    __tablename__ = "draws"
    __table_args__ = (UniqueConstraint("lottery_type", "issue", name="uq_draws_lottery_issue"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    issue: Mapped[str] = mapped_column(String(20), nullable=False)
    draw_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    primary_numbers: Mapped[list[int]] = mapped_column(IntArray(), nullable=False)
    secondary_numbers: Mapped[list[int]] = mapped_column(IntArray(), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="official")
    source_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONDoc, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cursor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestionError(Base):
    __tablename__ = "ingestion_errors"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_item_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONDoc, nullable=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

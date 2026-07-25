"""Strategy profile model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID, JSONDoc


class StrategyProfile(Base):
    __tablename__ = "strategy_profiles"
    __table_args__ = (UniqueConstraint("name", "version", "lottery_type", name="uq_strategy_name_ver_lottery"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

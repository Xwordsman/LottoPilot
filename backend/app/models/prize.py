"""Prize rule set model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import GUID, JSONDoc


class PrizeRuleSet(Base):
    __tablename__ = "prize_rule_sets"
    __table_args__ = (
        UniqueConstraint("lottery_type", "version", name="uq_prize_rule_lottery_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    lottery_type: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    effective_from_issue: Mapped[str | None] = mapped_column(String(20), nullable=True)
    effective_to_issue: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rules: Mapped[dict[str, Any]] = mapped_column(JSONDoc, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

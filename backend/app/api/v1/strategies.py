"""Strategy profile routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep
from app.api.response import success_response
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.models.backtest import BacktestRun
from app.models.recommendation import RecommendationRun
from app.models.strategy import StrategyProfile
from app.services.audit import write_audit
from app.services.recommendation.engine import ensure_default_strategy
from app.services.recommendation.strategy import merge_strategy_config

router = APIRouter(prefix="/strategies", tags=["strategies"])


class StrategyCreateRequest(BaseModel):
    lottery_type: str
    name: str = "custom"
    version: str = "v-exp"
    source_id: UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class StrategyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    version: str | None = Field(default=None, min_length=1, max_length=40)
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class StrategySetDefaultRequest(BaseModel):
    backtest_summary: dict[str, Any] = Field(default_factory=dict)
    backtest_run_id: UUID | None = None


def _public(row: StrategyProfile) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "version": row.version,
        "lottery_type": row.lottery_type,
        "config": row.config or {},
        "is_default": row.is_default,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _is_frozen(db: DbSession, strategy_id: UUID) -> bool:
    rec_count = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationRun)
            .where(RecommendationRun.strategy_profile_id == strategy_id)
        )
        or 0
    )
    if rec_count > 0:
        return True
    bt_count = int(
        db.scalar(
            select(func.count()).select_from(BacktestRun).where(BacktestRun.strategy_profile_id == strategy_id)
        )
        or 0
    )
    return bt_count > 0


@router.get("")
def list_strategies(
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
    lottery_type: str | None = Query(default=None, pattern="^(ssq|dlt)$"),
    include_inactive: bool = Query(default=False),
):
    _ = user
    for lt in ("ssq", "dlt"):
        if lottery_type is None or lottery_type == lt:
            ensure_default_strategy(db, lt)
    db.commit()
    stmt = select(StrategyProfile)
    if not include_inactive:
        stmt = stmt.where(StrategyProfile.is_active.is_(True))
    if lottery_type:
        stmt = stmt.where(StrategyProfile.lottery_type == lottery_type)
    rows = db.scalars(
        stmt.order_by(StrategyProfile.lottery_type.asc(), StrategyProfile.created_at.desc())
    ).all()
    return success_response({"items": [_public(r) for r in rows]}, request_id)


@router.get("/{strategy_id}")
def get_strategy(strategy_id: UUID, db: DbSession, user: CurrentUserDep, request_id: RequestIdDep):
    _ = user
    row = db.get(StrategyProfile, strategy_id)
    if row is None:
        raise NotFoundError("策略不存在")
    data = _public(row)
    data["frozen"] = _is_frozen(db, strategy_id)
    return success_response(data, request_id)


@router.post("")
def create_strategy_version(
    payload: StrategyCreateRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    if payload.lottery_type not in {"ssq", "dlt"}:
        raise ValidationAppError("不支持的彩种", code="UNSUPPORTED_LOTTERY")
    if payload.source_id:
        source = db.get(StrategyProfile, payload.source_id)
        if source is None or source.lottery_type != payload.lottery_type:
            raise ValidationAppError("源策略不存在", code="STRATEGY_NOT_FOUND")
        base_cfg = source.config if isinstance(source.config, dict) else {}
        config = merge_strategy_config({**base_cfg, **(payload.config or {})})
    else:
        config = merge_strategy_config(payload.config if payload.config else None)
    row = StrategyProfile(
        name=payload.name,
        version=payload.version,
        lottery_type=payload.lottery_type,
        config=config,
        is_default=False,
        is_active=True,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        actor_id=user.id,
        action="strategy.create",
        resource_type="strategy_profile",
        resource_id=str(row.id),
        metadata={"name": row.name, "version": row.version, "lottery_type": row.lottery_type},
        request_id=request_id,
    )
    db.commit()
    db.refresh(row)
    return success_response(_public(row), request_id, status_code=201)


@router.patch("/{strategy_id}")
def patch_strategy(
    strategy_id: UUID,
    payload: StrategyUpdateRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    row = db.get(StrategyProfile, strategy_id)
    if row is None:
        raise NotFoundError("策略不存在")
    if _is_frozen(db, strategy_id):
        raise ConflictError("策略版本已被引用，不可修改", code="STRATEGY_IMMUTABLE")
    if payload.name is not None:
        row.name = payload.name
    if payload.version is not None:
        row.version = payload.version
    if payload.config is not None:
        base = row.config if isinstance(row.config, dict) else {}
        row.config = merge_strategy_config({**base, **payload.config})
    if payload.is_active is not None:
        row.is_active = payload.is_active
    db.add(row)
    write_audit(
        db,
        actor_id=user.id,
        action="strategy.patch",
        resource_type="strategy_profile",
        resource_id=str(row.id),
        metadata={"fields": [k for k, v in payload.model_dump().items() if v is not None]},
        request_id=request_id,
    )
    db.commit()
    db.refresh(row)
    return success_response(_public(row), request_id)


@router.post("/{strategy_id}/activate")
def activate_strategy(
    strategy_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    row = db.get(StrategyProfile, strategy_id)
    if row is None:
        raise NotFoundError("策略不存在")
    row.is_active = True
    db.add(row)
    write_audit(
        db,
        actor_id=user.id,
        action="strategy.activate",
        resource_type="strategy_profile",
        resource_id=str(row.id),
        metadata={},
        request_id=request_id,
    )
    db.commit()
    db.refresh(row)
    return success_response(_public(row), request_id)


@router.post("/{strategy_id}/set-default")
def set_default_strategy(
    strategy_id: UUID,
    payload: StrategySetDefaultRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    row = db.get(StrategyProfile, strategy_id)
    if row is None:
        raise NotFoundError("策略不存在")
    if not row.is_active:
        raise ValidationAppError("只能将启用中的策略设为默认", code="STRATEGY_INACTIVE")

    summary = dict(payload.backtest_summary or {})
    if payload.backtest_run_id is not None:
        bt = db.get(BacktestRun, payload.backtest_run_id)
        if bt is None or bt.strategy_profile_id != strategy_id:
            raise ValidationAppError("回测记录不存在或不属于该策略", code="BACKTEST_NOT_FOUND")
        if bt.status != "succeeded":
            raise ValidationAppError("回测尚未成功完成", code="BACKTEST_NOT_READY")
        summary = {
            "backtest_run_id": str(bt.id),
            "status": bt.status,
            "summary": bt.summary or {},
            **summary,
        }
    elif not summary:
        latest_bt = db.scalar(
            select(BacktestRun)
            .where(
                BacktestRun.strategy_profile_id == strategy_id,
                BacktestRun.status == "succeeded",
            )
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
        if latest_bt is None:
            raise ValidationAppError(
                "设为默认需要提供 backtest_summary 或已有成功回测",
                code="BACKTEST_SUMMARY_REQUIRED",
            )
        summary = {
            "backtest_run_id": str(latest_bt.id),
            "status": latest_bt.status,
            "summary": latest_bt.summary or {},
        }

    db.execute(
        update(StrategyProfile)
        .where(StrategyProfile.lottery_type == row.lottery_type)
        .values(is_default=False)
    )
    row.is_default = True
    row.is_active = True
    db.add(row)
    write_audit(
        db,
        actor_id=user.id,
        action="strategy.set_default",
        resource_type="strategy_profile",
        resource_id=str(row.id),
        metadata={"backtest_summary": summary},
        request_id=request_id,
    )
    db.commit()
    db.refresh(row)
    data = _public(row)
    data["backtest_summary"] = summary
    return success_response(data, request_id)
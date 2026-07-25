"""AI config, system settings and audit log routes."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep, SettingsDep
from app.api.response import success_response
from app.core.errors import NotFoundError, ValidationAppError
from app.models.ai import AIConfig
from app.models.recommendation import RecommendationRun
from app.models.system import AuditLog
from app.schemas.settings import (
    AIConfigCreateRequest,
    AIConfigPublic,
    AIConfigUpdateRequest,
    AITestResult,
    SystemSettingsPublic,
    SystemSettingsUpdateRequest,
)
from app.services.ai.client import (
    OpenAICompatibleClient,
    decrypt_api_key,
    encrypt_api_key,
    public_key_mask,
)
from app.services.audit import write_audit
from app.services.system_settings import get_system_settings, update_system_settings
from app.utils.time import utcnow

router = APIRouter(tags=["settings"])


def _to_public(cfg: AIConfig, app_secret: str) -> AIConfigPublic:
    plain = ""
    try:
        plain = decrypt_api_key(cfg.api_key_encrypted, app_secret) if cfg.api_key_encrypted else ""
    except Exception:  # noqa: BLE001
        plain = ""
    return AIConfigPublic(
        id=cfg.id,
        name=cfg.name,
        provider=cfg.provider,
        base_url=cfg.base_url,
        model=cfg.model,
        has_api_key=bool(cfg.api_key_encrypted),
        api_key_masked=public_key_mask(plain) if plain else ("****" if cfg.api_key_encrypted else ""),
        timeout_seconds=cfg.timeout_seconds,
        max_tokens=cfg.max_tokens,
        is_default=cfg.is_default,
        is_active=cfg.is_active,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.get("/settings/ai")
def list_ai_configs(db: DbSession, settings: SettingsDep, user: CurrentUserDep, request_id: RequestIdDep):
    _ = user
    rows = db.scalars(select(AIConfig).order_by(AIConfig.created_at.desc())).all()
    data = [_to_public(row, settings.app_secret_key).model_dump(mode="json") for row in rows]
    return success_response({"items": data}, request_id)


@router.post("/settings/ai")
def create_ai_config(
    payload: AIConfigCreateRequest,
    db: DbSession,
    settings: SettingsDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    if payload.is_default:
        db.execute(update(AIConfig).values(is_default=False))
    cfg = AIConfig(
        name=payload.name,
        provider=payload.provider,
        base_url=payload.base_url.rstrip("/"),
        model=payload.model,
        api_key_encrypted=encrypt_api_key(payload.api_key, settings.app_secret_key),
        timeout_seconds=payload.timeout_seconds,
        max_tokens=payload.max_tokens,
        is_default=payload.is_default,
        is_active=True,
        extra={},
    )
    db.add(cfg)
    db.flush()
    write_audit(
        db,
        actor_id=user.id,
        action="ai_config.create",
        resource_type="ai_config",
        resource_id=str(cfg.id),
        metadata={"name": payload.name, "model": payload.model},
        request_id=request_id,
    )
    db.commit()
    db.refresh(cfg)
    return success_response(_to_public(cfg, settings.app_secret_key).model_dump(mode="json"), request_id, status_code=201)


@router.patch("/settings/ai/{config_id}")
def update_ai_config(
    config_id: UUID,
    payload: AIConfigUpdateRequest,
    db: DbSession,
    settings: SettingsDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    cfg = db.get(AIConfig, config_id)
    if cfg is None:
        raise NotFoundError("AI 配置不存在")
    if payload.name is not None:
        cfg.name = payload.name
    if payload.provider is not None:
        cfg.provider = payload.provider
    if payload.base_url is not None:
        cfg.base_url = payload.base_url.rstrip("/")
    if payload.model is not None:
        cfg.model = payload.model
    if payload.timeout_seconds is not None:
        cfg.timeout_seconds = payload.timeout_seconds
    if payload.max_tokens is not None:
        cfg.max_tokens = payload.max_tokens
    if payload.is_active is not None:
        cfg.is_active = payload.is_active
    if payload.is_default is True:
        db.execute(update(AIConfig).values(is_default=False))
        cfg.is_default = True
    elif payload.is_default is False:
        cfg.is_default = False
    if payload.clear_api_key:
        cfg.api_key_encrypted = ""
    elif payload.api_key:
        cfg.api_key_encrypted = encrypt_api_key(payload.api_key, settings.app_secret_key)
    cfg.updated_at = utcnow()
    db.add(cfg)
    write_audit(
        db,
        actor_id=user.id,
        action="ai_config.update",
        resource_type="ai_config",
        resource_id=str(cfg.id),
        metadata={"fields": [k for k, v in payload.model_dump().items() if v is not None]},
        request_id=request_id,
    )
    db.commit()
    db.refresh(cfg)
    return success_response(_to_public(cfg, settings.app_secret_key).model_dump(mode="json"), request_id)


@router.delete("/settings/ai/{config_id}")
def delete_ai_config(
    config_id: UUID,
    db: DbSession,
    settings: SettingsDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    cfg = db.get(AIConfig, config_id)
    if cfg is None:
        raise NotFoundError("AI 配置不存在")
    referenced = int(
        db.scalar(
            select(func.count()).select_from(RecommendationRun).where(RecommendationRun.ai_config_id == config_id)
        )
        or 0
    )
    soft = referenced > 0
    if soft:
        cfg.is_active = False
        cfg.is_default = False
        cfg.updated_at = utcnow()
        db.add(cfg)
        mode = "soft"
    else:
        db.delete(cfg)
        mode = "hard"
    write_audit(
        db,
        actor_id=user.id,
        action="ai_config.delete",
        resource_type="ai_config",
        resource_id=str(config_id),
        metadata={"mode": mode, "referenced": referenced},
        request_id=request_id,
    )
    db.commit()
    if soft:
        return success_response(
            {
                "id": str(config_id),
                "deleted": True,
                "mode": mode,
                "config": _to_public(cfg, settings.app_secret_key).model_dump(mode="json"),
            },
            request_id,
        )
    return success_response({"id": str(config_id), "deleted": True, "mode": mode}, request_id)


@router.post("/settings/ai/{config_id}/set-default")
def set_default_ai_config(
    config_id: UUID,
    db: DbSession,
    settings: SettingsDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    cfg = db.get(AIConfig, config_id)
    if cfg is None:
        raise NotFoundError("AI 配置不存在")
    if not cfg.is_active:
        raise ValidationAppError("只能将启用中的 AI 配置设为默认", code="AI_CONFIG_INACTIVE")
    db.execute(update(AIConfig).values(is_default=False))
    cfg.is_default = True
    cfg.updated_at = utcnow()
    db.add(cfg)
    write_audit(
        db,
        actor_id=user.id,
        action="ai_config.set_default",
        resource_type="ai_config",
        resource_id=str(cfg.id),
        metadata={},
        request_id=request_id,
    )
    db.commit()
    db.refresh(cfg)
    return success_response(_to_public(cfg, settings.app_secret_key).model_dump(mode="json"), request_id)


@router.post("/settings/ai/{config_id}/test")
async def test_ai_config(
    config_id: UUID,
    db: DbSession,
    settings: SettingsDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    _ = user
    cfg = db.get(AIConfig, config_id)
    if cfg is None:
        raise NotFoundError("AI 配置不存在")
    if not cfg.api_key_encrypted:
        raise ValidationAppError("未配置 API Key", code="AI_KEY_MISSING")
    api_key = decrypt_api_key(cfg.api_key_encrypted, settings.app_secret_key)
    client = OpenAICompatibleClient(
        base_url=cfg.base_url,
        api_key=api_key,
        model=cfg.model,
        timeout_seconds=cfg.timeout_seconds,
        max_tokens=cfg.max_tokens,
    )
    info = await client.test_connection()
    data = AITestResult(status=info.status, model=info.model, latency_ms=info.latency_ms)
    return success_response(data.model_dump(), request_id)


@router.get("/settings/system")
def get_system_settings_route(db: DbSession, user: CurrentUserDep, request_id: RequestIdDep):
    _ = user
    data = SystemSettingsPublic(**get_system_settings(db))
    return success_response(data.model_dump(mode="json"), request_id)


@router.patch("/settings/system")
def patch_system_settings_route(
    payload: SystemSettingsUpdateRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    patch = payload.model_dump(exclude_unset=True)
    try:
        merged = update_system_settings(db, patch)
    except ValueError as exc:
        raise ValidationAppError(str(exc), code="SYSTEM_SETTINGS_INVALID") from exc
    write_audit(
        db,
        actor_id=user.id,
        action="system_settings.update",
        resource_type="app_setting",
        resource_id="system",
        metadata={"fields": list(patch.keys())},
        request_id=request_id,
    )
    db.commit()
    return success_response(SystemSettingsPublic(**merged).model_dump(mode="json"), request_id)


@router.get("/audit-logs")
def list_audit_logs(
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
):
    _ = user
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": str(row.id),
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "metadata": row.metadata_json or {},
                "request_id": row.request_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    return success_response(
        {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        request_id,
    )
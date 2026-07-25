"""System settings stored in app_settings."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from app.models.system import AppSetting
from app.utils.time import utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

SYSTEM_SETTING_KEY = "system"

DEFAULT_SYSTEM_SETTINGS: dict[str, Any] = {
    "timezone": "Asia/Shanghai",
    "recommendation_count": 5,
    "ai_weight_cap": 0.10,
    "candidate_pool_max": 50000,
    "scheduler_enabled": True,
    "sync_cron": "5 21 * * 1,3,6",
    "swagger_public": True,
    "default_window": 50,
}


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if value is None:
            continue
        out[key] = value
    return out


def validate_system_settings_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a settings patch without DB access."""
    allowed = set(DEFAULT_SYSTEM_SETTINGS.keys())
    clean: dict[str, Any] = {k: v for k, v in patch.items() if k in allowed and v is not None}
    if "ai_weight_cap" in clean:
        cap = float(clean["ai_weight_cap"])
        if cap < 0 or cap > 0.10:
            raise ValueError("ai_weight_cap must be between 0 and 0.10")
        clean["ai_weight_cap"] = cap
    if "recommendation_count" in clean:
        clean["recommendation_count"] = int(clean["recommendation_count"])
        if clean["recommendation_count"] < 1 or clean["recommendation_count"] > 20:
            raise ValueError("recommendation_count must be 1..20")
    if "candidate_pool_max" in clean:
        clean["candidate_pool_max"] = int(clean["candidate_pool_max"])
        if clean["candidate_pool_max"] < 500 or clean["candidate_pool_max"] > 100000:
            raise ValueError("candidate_pool_max must be 500..100000")
    if "default_window" in clean:
        clean["default_window"] = int(clean["default_window"])
        if clean["default_window"] < 5 or clean["default_window"] > 5000:
            raise ValueError("default_window must be 5..5000")
    if "scheduler_enabled" in clean:
        clean["scheduler_enabled"] = bool(clean["scheduler_enabled"])
    if "swagger_public" in clean:
        clean["swagger_public"] = bool(clean["swagger_public"])
    if "timezone" in clean:
        clean["timezone"] = str(clean["timezone"]).strip() or DEFAULT_SYSTEM_SETTINGS["timezone"]
    if "sync_cron" in clean:
        clean["sync_cron"] = str(clean["sync_cron"]).strip()
    return clean


def get_system_settings(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, SYSTEM_SETTING_KEY)
    current = row.value if row and isinstance(row.value, dict) else {}
    return _merge(DEFAULT_SYSTEM_SETTINGS, current)


def update_system_settings(db: Session, patch: dict[str, Any]) -> dict[str, Any]:
    clean = validate_system_settings_patch(patch)
    merged = _merge(get_system_settings(db), clean)
    row = db.get(AppSetting, SYSTEM_SETTING_KEY)
    if row is None:
        row = AppSetting(key=SYSTEM_SETTING_KEY, value=merged)
    else:
        row.value = merged
        row.updated_at = utcnow()
    db.add(row)
    return merged
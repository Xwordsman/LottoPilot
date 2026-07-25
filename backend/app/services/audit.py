"""Audit log helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.models.system import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def write_audit(
    db: Session,
    *,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
        request_id=request_id,
    )
    db.add(row)
    return row
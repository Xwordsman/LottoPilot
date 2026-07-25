"""API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import SetupRequiredError, UnauthorizedError
from app.core.security import hash_session_token
from app.db.session import get_db
from app.models.user import User, UserSession
from app.utils.time import utcnow


def get_settings_dep() -> Settings:
    return get_settings()


DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


RequestIdDep = Annotated[str, Depends(get_request_id)]


def get_current_user_optional(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> User | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None

    token_hash = hash_session_token(token)
    now = utcnow()
    stmt = (
        select(UserSession)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .limit(1)
    )
    session = db.scalar(stmt)
    if session is None:
        return None

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None

    session.last_seen_at = now
    db.add(session)
    db.commit()
    return user


OptionalUserDep = Annotated[User | None, Depends(get_current_user_optional)]


def get_current_user(user: OptionalUserDep) -> User:
    if user is None:
        raise UnauthorizedError()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_initialized(db: DbSession) -> None:
    exists = db.scalar(select(User.id).limit(1))
    if exists is None:
        raise SetupRequiredError()


InitializedDep = Annotated[None, Depends(require_initialized)]

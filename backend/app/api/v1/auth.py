"""Setup and auth routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbSession, OptionalUserDep, RequestIdDep, SettingsDep
from app.api.response import success_response
from app.core.errors import SetupAlreadyCompletedError, UnauthorizedError, ValidationAppError
from app.core.security import generate_session_token, hash_password, hash_session_token, verify_password
from app.models.system import AppSetting, AuditLog
from app.models.user import User, UserSession
from app.schemas.auth import LoginData, LoginRequest, SetupRequest, SetupStatusData, UserPublic
from app.utils.time import utcnow

router = APIRouter(tags=["auth"])


@router.get("/setup/status")
def setup_status(db: DbSession, request_id: RequestIdDep):
    count = db.scalar(select(func.count()).select_from(User)) or 0
    return success_response(SetupStatusData(initialized=count > 0).model_dump(), request_id)


@router.post("/setup")
def setup(
    payload: SetupRequest,
    response: Response,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    request_id: RequestIdDep,
):
    existing = db.scalar(select(User.id).limit(1))
    if existing is not None:
        raise SetupAlreadyCompletedError()

    if len(payload.password) < 8:
        raise ValidationAppError("密码长度至少 8 位", code="WEAK_PASSWORD")

    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.merge(
        AppSetting(
            key="initialized",
            value={"at": utcnow().isoformat(), "by": str(user.id)},
        )
    )
    db.merge(
        AppSetting(
            key="defaults",
            value={
                "recommendation_count": 5,
                "ai_weight_cap": 0.10,
                "timezone": settings.tz,
            },
        )
    )

    token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        last_seen_at=utcnow(),
    )
    db.add(session)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="setup.complete",
            resource_type="system",
            resource_id="initialized",
            metadata_json={"email": user.email},
            request_id=request_id,
        )
    )
    db.commit()
    db.refresh(user)

    data = LoginData(user=UserPublic.model_validate(user))
    resp = success_response(data.model_dump(mode="json"), request_id, status_code=201)
    resp.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return resp


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    request_id: RequestIdDep,
):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()).limit(1))
    if user is None or not verify_password(user.password_hash, payload.password):
        raise UnauthorizedError("邮箱或密码错误")
    if not user.is_active:
        raise UnauthorizedError("账号已停用")

    # Rotate session token on each login.
    token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        last_seen_at=utcnow(),
    )
    db.add(session)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            metadata_json={},
            request_id=request_id,
        )
    )
    db.commit()

    data = LoginData(user=UserPublic.model_validate(user))
    resp = success_response(data.model_dump(mode="json"), request_id)
    resp.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return resp


@router.post("/auth/logout")
def logout(
    response: Response,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    user: OptionalUserDep,
    request_id: RequestIdDep,
):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        token_hash = hash_session_token(token)
        session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash).limit(1))
        if session and session.revoked_at is None:
            session.revoked_at = utcnow()
            db.add(session)
            if user is not None:
                db.add(
                    AuditLog(
                        actor_id=user.id,
                        action="auth.logout",
                        resource_type="user",
                        resource_id=str(user.id),
                        metadata_json={},
                        request_id=request_id,
                    )
                )
            db.commit()

    resp = success_response({"logged_out": True}, request_id)
    resp.delete_cookie(key=settings.session_cookie_name, path="/")
    return resp


@router.get("/auth/me")
def me(user: CurrentUserDep, request_id: RequestIdDep):
    return success_response(UserPublic.model_validate(user).model_dump(mode="json"), request_id)

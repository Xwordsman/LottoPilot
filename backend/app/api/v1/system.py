"""System health, info, jobs and lottery catalog routes."""

from __future__ import annotations

from uuid import UUID
import math

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep, SettingsDep
from app.api.response import success_response
from app.core.errors import NotFoundError
from app.models.draw import Draw
from app.models.system import Job
from app.schemas.common import HealthData, ReadyData, SystemInfoData

router = APIRouter(tags=["system"])

LOTTERY_CATALOG = [
    {
        "lottery_type": "ssq",
        "name": "双色球",
        "primary_count": 6,
        "primary_max": 33,
        "secondary_count": 1,
        "secondary_max": 16,
        "draw_weekdays": [2, 4, 7],
        "notes": "历史分析用途；不承诺中奖",
    },
    {
        "lottery_type": "dlt",
        "name": "大乐透",
        "primary_count": 5,
        "primary_max": 35,
        "secondary_count": 2,
        "secondary_max": 12,
        "draw_weekdays": [1, 3, 6],
        "notes": "历史分析用途；不承诺中奖",
    },
]


def _job_public(row: Job) -> dict:
    return {
        "id": str(row.id),
        "job_type": row.job_type,
        "status": row.status,
        "progress_current": row.progress_current,
        "progress_total": row.progress_total,
        "resource_type": row.resource_type,
        "resource_id": str(row.resource_id) if row.resource_id else None,
        "payload_summary": row.payload_summary,
        "error_code": row.error_code,
        "error_summary": row.error_summary,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


@router.get("/health")
def health(request_id: RequestIdDep):
    return success_response(HealthData().model_dump(), request_id)


@router.get("/system/ready")
def ready(db: DbSession, request_id: RequestIdDep):
    """DB ping is independent from alembic_version presence (SQLite local e2e / pre-migrate)."""
    database = "ok"
    migrations = "ok"
    detail = None
    status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database = "error"
        migrations = "unknown"
        status = "error"
        detail = str(exc)
        data = ReadyData(status=status, database=database, migrations=migrations, detail=detail)
        return success_response(data.model_dump(), request_id)

    try:
        row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        if row is None:
            migrations = "pending"
            status = "degraded"
            detail = "alembic_version is empty"
    except Exception as exc:  # noqa: BLE001
        # Missing alembic_version table (create_all / fresh SQLite) is degraded, not DB down.
        migrations = "pending"
        status = "degraded"
        detail = f"alembic_version unavailable: {exc}"
    data = ReadyData(status=status, database=database, migrations=migrations, detail=detail)
    return success_response(data.model_dump(), request_id)


@router.get("/system/info")
def system_info(db: DbSession, settings: SettingsDep, request_id: RequestIdDep):
    latest: dict[str, str | None] = {"ssq": None, "dlt": None}
    counts: dict[str, int] = {"ssq": 0, "dlt": 0}
    for lottery in ("ssq", "dlt"):
        issue = db.scalar(
            select(Draw.issue)
            .where(Draw.lottery_type == lottery)
            .order_by(Draw.draw_date.desc(), Draw.issue.desc())
            .limit(1)
        )
        latest[lottery] = issue
        counts[lottery] = int(
            db.scalar(select(func.count()).select_from(Draw).where(Draw.lottery_type == lottery)) or 0
        )
    data = SystemInfoData(
        app_name=settings.app_name,
        version=settings.app_version,
        git_commit=settings.app_git_commit,
        build_time=settings.app_build_time or None,
        env=settings.app_env,
        latest_draws=latest,
    )
    payload = data.model_dump()
    payload["draw_counts"] = counts
    return success_response(payload, request_id)


@router.get("/lotteries")
def list_lotteries(db: DbSession, request_id: RequestIdDep, user: CurrentUserDep):
    _ = user
    items = []
    for item in LOTTERY_CATALOG:
        latest = db.scalar(
            select(Draw.issue)
            .where(Draw.lottery_type == item["lottery_type"])
            .order_by(Draw.draw_date.desc(), Draw.issue.desc())
            .limit(1)
        )
        count = int(
            db.scalar(
                select(func.count()).select_from(Draw).where(Draw.lottery_type == item["lottery_type"])
            )
            or 0
        )
        items.append({**item, "latest_issue": latest, "draw_count": count})
    return success_response({"items": items}, request_id)


@router.get("/system/jobs")
def list_jobs(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    _ = user
    total = int(db.scalar(select(func.count()).select_from(Job)) or 0)
    rows = db.scalars(
        select(Job).order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    return success_response(
        {
            "items": [_job_public(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        request_id,
    )


@router.get("/system/jobs/{job_id}")
def get_job(job_id: UUID, db: DbSession, request_id: RequestIdDep, user: CurrentUserDep):
    _ = user
    row = db.get(Job, job_id)
    if row is None:
        raise NotFoundError("任务不存在")
    return success_response(_job_public(row), request_id)

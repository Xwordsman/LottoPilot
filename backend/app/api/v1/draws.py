"""Draw query, sync and import routes."""

from __future__ import annotations

import asyncio
import math
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep
from app.api.response import success_response
from app.core.errors import NotFoundError, ValidationAppError
from app.db.session import SessionLocal
from app.models.draw import Draw, IngestionRun
from app.models.system import Job
from app.schemas.draws import (
    DrawDetail,
    DrawListData,
    DrawPublic,
    ImportCommitData,
    ImportCommitRequest,
    ImportPreviewData,
    IngestionRunListData,
    IngestionRunPublic,
    LatestDrawsData,
    SyncAcceptedData,
    SyncRequest,
)
from app.services.ingestion.adapters import get_adapter
from app.services.ingestion.import_csv import commit_import_rows, parse_csv_text, preview_import_rows
from app.services.ingestion.sync import create_sync_run, run_sync_job
from app.services.jobs import create_job

router = APIRouter(prefix="/draws", tags=["draws"])


def _page_meta(total: int, page: int, page_size: int) -> tuple[int, int]:
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    return total, total_pages


def _run_sync_in_background(
    *,
    job_id: UUID,
    run_id: UUID,
    lottery_type: str,
    mode: str,
    page_size: int,
) -> None:
    async def _runner() -> None:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            run = db.get(IngestionRun, run_id)
            if job is None or run is None:
                return
            await run_sync_job(
                db,
                job=job,
                run=run,
                lottery_type=lottery_type,
                mode=mode,  # type: ignore[arg-type]
                page_size=page_size,
            )
        finally:
            db.close()

    asyncio.run(_runner())


@router.get("")
def list_draws(
    db: DbSession,
    request_id: RequestIdDep,
    lottery_type: Literal["ssq", "dlt"] | None = None,
    issue: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Draw)
    count_stmt = select(func.count()).select_from(Draw)
    if lottery_type:
        stmt = stmt.where(Draw.lottery_type == lottery_type)
        count_stmt = count_stmt.where(Draw.lottery_type == lottery_type)
    if issue:
        stmt = stmt.where(Draw.issue == issue)
        count_stmt = count_stmt.where(Draw.issue == issue)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(Draw.draw_date.desc(), Draw.issue.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    _, total_pages = _page_meta(total, page, page_size)
    data = DrawListData(
        items=[DrawPublic.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/latest")
def latest_draws(db: DbSession, request_id: RequestIdDep):
    result: dict[str, DrawPublic | None] = {"ssq": None, "dlt": None}
    for lottery in ("ssq", "dlt"):
        row = db.scalar(
            select(Draw)
            .where(Draw.lottery_type == lottery)
            .order_by(Draw.draw_date.desc(), Draw.issue.desc())
            .limit(1)
        )
        result[lottery] = DrawPublic.model_validate(row) if row else None
    data = LatestDrawsData(ssq=result["ssq"], dlt=result["dlt"])
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/sync-runs")
def list_sync_runs(
    db: DbSession,
    request_id: RequestIdDep,
    lottery_type: Literal["ssq", "dlt"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(IngestionRun)
    count_stmt = select(func.count()).select_from(IngestionRun)
    if lottery_type:
        stmt = stmt.where(IngestionRun.lottery_type == lottery_type)
        count_stmt = count_stmt.where(IngestionRun.lottery_type == lottery_type)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(IngestionRun.started_at.desc().nullslast(), IngestionRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    _, total_pages = _page_meta(total, page, page_size)
    data = IngestionRunListData(
        items=[IngestionRunPublic.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/{lottery_type}/{issue}")
def get_draw(
    lottery_type: Literal["ssq", "dlt"],
    issue: str,
    db: DbSession,
    request_id: RequestIdDep,
):
    row = db.scalar(
        select(Draw).where(Draw.lottery_type == lottery_type, Draw.issue == issue).limit(1)
    )
    if row is None:
        raise NotFoundError("开奖记录不存在")
    data = DrawDetail.model_validate(row)
    return success_response(data.model_dump(mode="json"), request_id)


@router.post("/sync")
def create_sync(
    payload: SyncRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    adapter = get_adapter(payload.lottery_type)
    job = create_job(
        db,
        job_type="draw_sync",
        payload_summary={
            "lottery_type": payload.lottery_type,
            "mode": payload.mode,
            "page_size": payload.page_size,
        },
        created_by=user.id,
        resource_type="draw_sync",
    )
    run = create_sync_run(
        db,
        job=job,
        lottery_type=payload.lottery_type,
        mode=payload.mode,
        source_name=adapter.source_name,
    )
    db.commit()

    background_tasks.add_task(
        _run_sync_in_background,
        job_id=job.id,
        run_id=run.id,
        lottery_type=payload.lottery_type,
        mode=payload.mode,
        page_size=payload.page_size,
    )

    data = SyncAcceptedData(
        job_id=job.id,
        run_id=run.id,
        lottery_type=payload.lottery_type,
        mode=payload.mode,
        status="queued",
    )
    return success_response(data.model_dump(mode="json"), request_id, status_code=202)


@router.post("/import/preview")
async def import_preview(
    request_id: RequestIdDep,
    user: CurrentUserDep,
    file: UploadFile = File(...),
):
    _ = user
    if not file.filename:
        raise ValidationAppError("请上传文件", code="IMPORT_INVALID")
    lower = file.filename.lower()
    if not (lower.endswith(".csv") or lower.endswith(".txt")):
        raise ValidationAppError("当前仅支持 CSV 导入", code="IMPORT_INVALID")
    content = (await file.read()).decode("utf-8-sig")
    raw_rows = parse_csv_text(content)
    preview = preview_import_rows(raw_rows)
    data = ImportPreviewData.model_validate(preview)
    return success_response(data.model_dump(mode="json"), request_id)


@router.post("/import/commit")
def import_commit(
    payload: ImportCommitRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    _ = user
    if not payload.rows:
        raise ValidationAppError("没有可导入的数据", code="IMPORT_INVALID")
    result = commit_import_rows(db, payload.rows)
    data = ImportCommitData.model_validate(result)
    return success_response(data.model_dump(mode="json"), request_id)

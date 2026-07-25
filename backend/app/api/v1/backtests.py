"""Backtest routes."""

from __future__ import annotations

import csv
import io
import json
import math
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep
from app.api.response import success_response
from app.core.errors import NotFoundError, ValidationAppError
from app.models.backtest import BacktestIssueResult, BacktestRun
from app.models.draw import Draw
from app.models.system import Job
from app.schemas.settings import BacktestCreateRequest, BacktestListData, BacktestRunPublic
from app.services.backtest import run_backtest
from app.services.jobs import mark_job_failed
from app.utils.time import utcnow

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("")
def create_backtest(
    payload: BacktestCreateRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    run = run_backtest(
        db,
        lottery_type=payload.lottery_type,
        start_issue=payload.start_issue,
        end_issue=payload.end_issue,
        seed=payload.seed,
        baseline_trials=payload.baseline_trials,
        candidate_count=payload.candidate_count,
        created_by=user.id,
    )
    return success_response(BacktestRunPublic.model_validate(run).model_dump(mode="json"), request_id, status_code=201)


@router.get("")
def list_backtests(
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
    lottery_type: str | None = Query(default=None, pattern="^(ssq|dlt)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    _ = user
    stmt = select(BacktestRun)
    count_stmt = select(func.count()).select_from(BacktestRun)
    if lottery_type:
        stmt = stmt.where(BacktestRun.lottery_type == lottery_type)
        count_stmt = count_stmt.where(BacktestRun.lottery_type == lottery_type)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(BacktestRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    data = BacktestListData(
        items=[BacktestRunPublic.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/{run_id}")
def get_backtest(run_id: UUID, db: DbSession, user: CurrentUserDep, request_id: RequestIdDep):
    _ = user
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise NotFoundError("回测记录不存在")
    return success_response(BacktestRunPublic.model_validate(run).model_dump(mode="json"), request_id)


@router.get("/{run_id}/issues")
def list_backtest_issues(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    _ = user
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise NotFoundError("回测记录不存在")
    total = int(
        db.scalar(
            select(func.count()).select_from(BacktestIssueResult).where(
                BacktestIssueResult.backtest_run_id == run_id
            )
        )
        or 0
    )
    rows = db.scalars(
        select(BacktestIssueResult)
        .where(BacktestIssueResult.backtest_run_id == run_id)
        .order_by(BacktestIssueResult.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    draw_ids = {r.target_draw_id for r in rows} | {r.training_cutoff_draw_id for r in rows}
    draws = {}
    if draw_ids:
        for d in db.scalars(select(Draw).where(Draw.id.in_(list(draw_ids)))).all():
            draws[d.id] = d
    items = []
    for r in rows:
        target = draws.get(r.target_draw_id)
        cutoff = draws.get(r.training_cutoff_draw_id)
        hit = dict(r.hit_metrics or {})
        if target is not None and "target_issue" not in hit:
            hit["target_issue"] = target.issue
        items.append(
            {
                "id": str(r.id),
                "target_draw_id": str(r.target_draw_id),
                "training_cutoff_draw_id": str(r.training_cutoff_draw_id),
                "target_issue": target.issue if target else None,
                "training_cutoff_issue": cutoff.issue if cutoff else None,
                "tickets": r.tickets or [],
                "hit_metrics": hit,
                "baseline_metrics": r.baseline_metrics or {},
                "runtime_ms": r.runtime_ms,
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
            "run_id": str(run_id),
        },
        request_id,
    )


@router.get("/{run_id}/export")
def export_backtest(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
):
    _ = user
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise NotFoundError("回测记录不存在")
    issues = db.scalars(
        select(BacktestIssueResult)
        .where(BacktestIssueResult.backtest_run_id == run_id)
        .order_by(BacktestIssueResult.id.asc())
    ).all()
    payload = {
        "id": str(run.id),
        "lottery_type": run.lottery_type,
        "start_issue": run.start_issue,
        "end_issue": run.end_issue,
        "seed": run.seed,
        "baseline_trials": run.baseline_trials,
        "status": run.status,
        "summary": run.summary or {},
        "disclaimer": "回测指标仅为历史拟合观察，不代表未来收益或中奖承诺。",
        "issues": [
            {
                "target_draw_id": str(i.target_draw_id),
                "hit_metrics": i.hit_metrics or {},
                "baseline_metrics": i.baseline_metrics or {},
                "tickets": i.tickets or [],
                "runtime_ms": i.runtime_ms,
            }
            for i in issues
        ],
    }
    safe = f"{run.lottery_type}-{run.start_issue}-{run.end_issue}"
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "target_draw_id",
            "best_primary_hits",
            "best_secondary_hits",
            "baseline_avg_primary_hits",
            "runtime_ms",
        ])
        for item in payload["issues"]:
            hm = item["hit_metrics"] or {}
            bm = item["baseline_metrics"] or {}
            writer.writerow([
                item["target_draw_id"],
                hm.get("best_primary_hits", ""),
                hm.get("best_secondary_hits", ""),
                bm.get("avg_primary_hits", ""),
                item["runtime_ms"],
            ])
        content = buf.getvalue()
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="lottopilot-backtest-{safe}.csv"'},
        )
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="lottopilot-backtest-{safe}.json"'},
    )


@router.post("/{run_id}/cancel")
def cancel_backtest(run_id: UUID, db: DbSession, user: CurrentUserDep, request_id: RequestIdDep):
    _ = user
    run = db.get(BacktestRun, run_id)
    if run is None:
        raise NotFoundError("回测记录不存在")
    if run.status in {"succeeded", "failed", "cancelled"}:
        raise ValidationAppError("回测已结束，无法取消", code="BACKTEST_NOT_CANCELLABLE")
    run.status = "cancelled"
    run.finished_at = utcnow()
    summary = dict(run.summary or {})
    summary["cancelled"] = True
    run.summary = summary
    job = db.get(Job, run.job_id)
    if job is not None:
        mark_job_failed(db, job, code="CANCELLED", summary="cancelled by user")
    db.add(run)
    db.commit()
    return success_response(BacktestRunPublic.model_validate(run).model_dump(mode="json"), request_id)

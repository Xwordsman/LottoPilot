"""Recommendation routes."""

from __future__ import annotations

from uuid import UUID
import math

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep
from app.api.response import success_response
from app.core.errors import NotFoundError
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.system import Job
from app.schemas.recommendations import (
    RecommendationCreateRequest,
    RecommendationEvaluationSummary,
    RecommendationRunListData,
    RecommendationRunPublic,
    RecommendationTicketPublic,
)
from app.services.ai.explain import build_statistical_explanation
from app.services.recommendation.engine import run_recommendation
from app.services.recommendation.evaluate import build_run_export, evaluate_recommendation_run

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _run_to_public(db, run: RecommendationRun) -> RecommendationRunPublic:
    tickets = sorted(run.tickets, key=lambda t: t.rank)
    results_by_ticket: dict[UUID, RecommendationResult] = {}
    ticket_ids = [t.id for t in tickets]
    if ticket_ids:
        for row in db.scalars(
            select(RecommendationResult).where(RecommendationResult.ticket_id.in_(ticket_ids))
        ).all():
            results_by_ticket[row.ticket_id] = row

    public_tickets: list[RecommendationTicketPublic] = []
    for t in tickets:
        result = results_by_ticket.get(t.id)
        public_tickets.append(
            RecommendationTicketPublic(
                id=t.id,
                rank=t.rank,
                primary_numbers=list(t.primary_numbers),
                secondary_numbers=list(t.secondary_numbers),
                statistical_score=float(t.statistical_score),
                ai_score=float(t.ai_score) if t.ai_score is not None else None,
                final_score=float(t.final_score),
                feature_summary=t.feature_summary or {},
                tags=t.tags or {},
                explanation=t.explanation,
                primary_hits=result.primary_hits if result else None,
                secondary_hits=result.secondary_hits if result else None,
                prize_level=result.prize_level if result else None,
            )
        )

    eval_raw = (run.metrics or {}).get("evaluation") if isinstance(run.metrics, dict) else None
    evaluation = None
    if isinstance(eval_raw, dict):
        evaluation = RecommendationEvaluationSummary(
            draw_issue=eval_raw.get("draw_issue"),
            best_rank=eval_raw.get("best_rank"),
            best_primary_hits=eval_raw.get("best_primary_hits"),
            best_secondary_hits=eval_raw.get("best_secondary_hits"),
            any_prize=bool(eval_raw.get("any_prize")),
            prize_rule_version=eval_raw.get("prize_rule_version"),
        )

    return RecommendationRunPublic(
        id=run.id,
        job_id=run.job_id,
        lottery_type=run.lottery_type,
        target_issue=run.target_issue,
        strategy_profile_id=run.strategy_profile_id,
        data_cutoff_issue=run.data_cutoff_issue,
        data_snapshot_hash=run.data_snapshot_hash,
        seed=run.seed,
        candidate_count=run.candidate_count,
        ai_status=run.ai_status,
        ai_provider=run.ai_provider,
        ai_model=run.ai_model,
        status=run.status,
        metrics=run.metrics or {},
        evaluation=evaluation,
        created_at=run.created_at,
        finished_at=run.finished_at,
        tickets=public_tickets,
    )


@router.post("")
def create_recommendation(
    payload: RecommendationCreateRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    run = run_recommendation(
        db,
        lottery_type=payload.lottery_type,
        target_issue=payload.target_issue,
        strategy_profile_id=payload.strategy_profile_id,
        seed=payload.seed,
        created_by=user.id,
        candidate_count=payload.candidate_count or 5000,
        enable_ai=payload.enable_ai,
    )
    loaded = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run.id)
        .options(selectinload(RecommendationRun.tickets))
    )
    assert loaded is not None
    return success_response(_run_to_public(db, loaded).model_dump(mode="json"), request_id, status_code=201)


@router.get("")
def list_recommendations(
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    lottery_type: str | None = Query(default=None, pattern="^(ssq|dlt)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    _ = user
    stmt = select(RecommendationRun).options(selectinload(RecommendationRun.tickets))
    count_stmt = select(func.count()).select_from(RecommendationRun)
    if lottery_type:
        stmt = stmt.where(RecommendationRun.lottery_type == lottery_type)
        count_stmt = count_stmt.where(RecommendationRun.lottery_type == lottery_type)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(RecommendationRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    data = RecommendationRunListData(
        items=[_run_to_public(db, row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
    return success_response(data.model_dump(mode="json"), request_id)


@router.get("/{run_id}")
def get_recommendation(
    run_id: UUID,
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
):
    _ = user
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")
    return success_response(_run_to_public(db, run).model_dump(mode="json"), request_id)




@router.delete("/{run_id}")
def delete_recommendation(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    """Delete one recommendation run and its tickets/results."""
    run = db.get(RecommendationRun, run_id)
    if run is None:
        raise NotFoundError("推荐记录不存在")
    job_id = run.job_id
    db.delete(run)
    job = db.get(Job, job_id)
    if job is not None:
        db.delete(job)
    db.commit()
    return success_response({"deleted": True, "id": str(run_id)}, request_id)



@router.post("/{run_id}/evaluate")
def evaluate_recommendation(
    run_id: UUID,
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
):
    _ = user
    summary = evaluate_recommendation_run(db, run_id=run_id)
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")
    payload = {
        "summary": summary,
        "run": _run_to_public(db, run).model_dump(mode="json"),
    }
    return success_response(payload, request_id)


@router.get("/{run_id}/export")
def export_recommendation(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
):
    _ = user
    filename, media_type, content = build_run_export(db, run_id=run_id, fmt=fmt)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/{run_id}/explanations")
def regenerate_explanations(
    run_id: UUID,
    db: DbSession,
    request_id: RequestIdDep,
    user: CurrentUserDep,
):
    """Regenerate statistical explanations for an existing run (AI optional later)."""
    _ = user
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")
    if run.status != "succeeded":
        from app.core.errors import ValidationAppError

        raise ValidationAppError("仅成功推荐可生成解释", code="RUN_NOT_READY")
    for ticket in run.tickets:
        ticket.explanation = build_statistical_explanation(
            lottery_type=run.lottery_type,
            primary_numbers=list(ticket.primary_numbers),
            secondary_numbers=list(ticket.secondary_numbers),
            feature_summary=ticket.feature_summary or {},
            rank=ticket.rank,
        )
        db.add(ticket)
    db.add(run)
    db.commit()
    db.refresh(run)
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    assert run is not None
    return success_response(_run_to_public(db, run).model_dump(mode="json"), request_id)

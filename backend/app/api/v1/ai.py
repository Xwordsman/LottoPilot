"""AI utility routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, DbSession, RequestIdDep, SettingsDep
from app.api.response import success_response
from app.core.errors import NotFoundError, ValidationAppError
from app.models.recommendation import RecommendationRun
from app.services.ai.explain import build_statistical_explanation, merge_ai_explanation
from app.services.ai.rerank_pipeline import maybe_apply_ai

router = APIRouter(prefix="/ai", tags=["ai"])


class TicketExplainRequest(BaseModel):
    lottery_type: str = Field(pattern="^(ssq|dlt)$")
    primary_numbers: list[int]
    secondary_numbers: list[int]
    feature_summary: dict[str, Any] = Field(default_factory=dict)
    rank: int | None = None
    enable_ai: bool = False


@router.post("/explain-ticket")
def explain_ticket(
    payload: TicketExplainRequest,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
    settings: SettingsDep,
):
    _ = user
    base = build_statistical_explanation(
        lottery_type=payload.lottery_type,
        primary_numbers=payload.primary_numbers,
        secondary_numbers=payload.secondary_numbers,
        feature_summary=payload.feature_summary,
        rank=payload.rank,
    )
    ai_status = "skipped"
    ai_provider = None
    ai_model = None
    explanation = base
    if payload.enable_ai:
        tickets = [
            {
                "rank": payload.rank or 1,
                "primary_numbers": payload.primary_numbers,
                "secondary_numbers": payload.secondary_numbers,
                "statistical_score": 50.0,
                "final_score": 50.0,
                "feature_summary": payload.feature_summary,
                "explanation": base,
            }
        ]
        ranked, meta = maybe_apply_ai(
            db,
            settings=settings,
            lottery_type=payload.lottery_type,
            target_issue="manual",
            tickets=tickets,
            enable_ai=True,
        )
        ai_status = str(meta.get("ai_status") or "failed")
        ai_provider = meta.get("ai_provider")
        ai_model = meta.get("ai_model")
        if ranked and ranked[0].get("explanation"):
            explanation = merge_ai_explanation(base, str(ranked[0].get("explanation")))
    return success_response(
        {
            "explanation": explanation,
            "ai_status": ai_status,
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            "disclaimer": "模型评分/历史分析，不承诺中奖",
        },
        request_id,
    )


@router.post("/explain-run/{run_id}")
def explain_recommendation_run(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    _ = user
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")
    if run.status != "succeeded":
        raise ValidationAppError("仅成功推荐可生成解释", code="RUN_NOT_READY")
    items = []
    for ticket in sorted(run.tickets, key=lambda t: t.rank):
        text = ticket.explanation or build_statistical_explanation(
            lottery_type=run.lottery_type,
            primary_numbers=list(ticket.primary_numbers),
            secondary_numbers=list(ticket.secondary_numbers),
            feature_summary=ticket.feature_summary or {},
            rank=ticket.rank,
        )
        items.append(
            {
                "ticket_id": str(ticket.id),
                "rank": ticket.rank,
                "explanation": text,
            }
        )
    return success_response(
        {
            "run_id": str(run.id),
            "ai_status": run.ai_status,
            "items": items,
            "disclaimer": "模型评分/历史分析，不承诺中奖",
        },
        request_id,
    )
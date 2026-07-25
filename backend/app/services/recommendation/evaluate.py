"""Recommendation post-draw evaluation (hits + prize level)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, ValidationAppError
from app.models.draw import Draw
from app.models.prize import PrizeRuleSet
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.services.recommendation.prize_rules import (
    default_prize_rules,
    evaluate_ticket_against_draw,
    map_prize_level,
)
from app.utils.time import utcnow

# Re-export pure helpers for convenience.
__all__ = [
    "build_run_export",
    "default_prize_rules",
    "evaluate_for_draw",
    "evaluate_recent_upserts",
    "evaluate_recommendation_run",
    "evaluate_ticket_against_draw",
    "map_prize_level",
]


def ensure_default_prize_rule_set(db: Session, lottery_type: str) -> PrizeRuleSet:
    existing = db.scalar(
        select(PrizeRuleSet)
        .where(
            PrizeRuleSet.lottery_type == lottery_type,
            PrizeRuleSet.version == "v1",
        )
        .limit(1)
    )
    if existing:
        return existing
    row = PrizeRuleSet(
        lottery_type=lottery_type,
        version="v1",
        effective_from_issue=None,
        effective_to_issue=None,
        rules=default_prize_rules(lottery_type),
    )
    db.add(row)
    db.flush()
    return row



def _load_draw_for_run(db: Session, run: RecommendationRun) -> Draw | None:
    if not run.target_issue:
        return None
    return db.scalar(
        select(Draw).where(
            Draw.lottery_type == run.lottery_type,
            Draw.issue == run.target_issue,
        )
    )

def evaluate_recommendation_run(
    db: Session,
    *,
    run_id: UUID,
    draw_id: UUID | None = None,
) -> dict[str, Any]:
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")
    if run.status != "succeeded":
        raise ValidationAppError("仅成功推荐可复盘", code="RUN_NOT_READY")

    draw: Draw | None
    if draw_id is not None:
        draw = db.get(Draw, draw_id)
        if draw is None:
            raise NotFoundError("开奖记录不存在")
        if draw.lottery_type != run.lottery_type:
            raise ValidationAppError("开奖记录彩种不匹配", code="LOTTERY_MISMATCH")
    else:
        draw = _load_draw_for_run(db, run)
        if draw is None:
            raise ValidationAppError(
                "目标期开奖尚未入库，无法复盘",
                code="DRAW_NOT_READY",
                details={"target_issue": run.target_issue},
            )

    rule_set = ensure_default_prize_rule_set(db, run.lottery_type)
    rules = rule_set.rules if isinstance(rule_set.rules, dict) else None
    tickets = sorted(run.tickets, key=lambda t: t.rank)
    results: list[dict[str, Any]] = []
    best_primary = -1
    best_secondary = -1
    best_rank: int | None = None

    for ticket in tickets:
        scored = evaluate_ticket_against_draw(
            lottery_type=run.lottery_type,
            ticket_primary=list(ticket.primary_numbers),
            ticket_secondary=list(ticket.secondary_numbers),
            draw_primary=list(draw.primary_numbers),
            draw_secondary=list(draw.secondary_numbers),
            rules=rules,
        )
        existing = db.scalar(
            select(RecommendationResult).where(
                RecommendationResult.ticket_id == ticket.id,
                RecommendationResult.draw_id == draw.id,
            )
        )
        if existing is None:
            existing = RecommendationResult(
                ticket_id=ticket.id,
                draw_id=draw.id,
                primary_hits=scored["primary_hits"],
                secondary_hits=scored["secondary_hits"],
                prize_level=scored["prize_level"],
                prize_rule_set_id=rule_set.id,
                evaluated_at=utcnow(),
            )
            db.add(existing)
        else:
            existing.primary_hits = scored["primary_hits"]
            existing.secondary_hits = scored["secondary_hits"]
            existing.prize_level = scored["prize_level"]
            existing.prize_rule_set_id = rule_set.id
            existing.evaluated_at = utcnow()
            db.add(existing)

        item = {
            "ticket_id": str(ticket.id),
            "rank": ticket.rank,
            "primary_numbers": list(ticket.primary_numbers),
            "secondary_numbers": list(ticket.secondary_numbers),
            "primary_hits": scored["primary_hits"],
            "secondary_hits": scored["secondary_hits"],
            "prize_level": scored["prize_level"],
        }
        results.append(item)
        if scored["primary_hits"] > best_primary or (
            scored["primary_hits"] == best_primary and scored["secondary_hits"] > best_secondary
        ):
            best_primary = scored["primary_hits"]
            best_secondary = scored["secondary_hits"]
            best_rank = ticket.rank

    summary = {
        "draw_id": str(draw.id),
        "draw_issue": draw.issue,
        "lottery_type": run.lottery_type,
        "ticket_count": len(results),
        "best_rank": best_rank,
        "best_primary_hits": max(best_primary, 0),
        "best_secondary_hits": max(best_secondary, 0),
        "any_prize": any(r["prize_level"] is not None for r in results),
        "prize_rule_set_id": str(rule_set.id),
        "prize_rule_version": rule_set.version,
        "evaluated_at": utcnow().isoformat(),
        "tickets": results,
    }
    metrics = dict(run.metrics or {})
    metrics["evaluation"] = {
        "draw_issue": draw.issue,
        "best_rank": best_rank,
        "best_primary_hits": summary["best_primary_hits"],
        "best_secondary_hits": summary["best_secondary_hits"],
        "any_prize": summary["any_prize"],
        "prize_rule_version": rule_set.version,
    }
    run.metrics = metrics
    db.add(run)
    db.commit()
    return summary


def evaluate_for_draw(db: Session, *, lottery_type: str, issue: str) -> list[dict[str, Any]]:
    """Auto-evaluate all succeeded recommendation runs targeting this issue."""
    draw = db.scalar(
        select(Draw).where(Draw.lottery_type == lottery_type, Draw.issue == issue)
    )
    if draw is None:
        return []
    runs = db.scalars(
        select(RecommendationRun).where(
            RecommendationRun.lottery_type == lottery_type,
            RecommendationRun.target_issue == issue,
            RecommendationRun.status == "succeeded",
        )
    ).all()
    out: list[dict[str, Any]] = []
    for run in runs:
        try:
            out.append(evaluate_recommendation_run(db, run_id=run.id, draw_id=draw.id))
        except Exception:  # noqa: BLE001 - fail-open per run during bulk evaluate
            db.rollback()
            continue
    return out


def evaluate_recent_upserts(
    db: Session,
    *,
    lottery_type: str,
    issues: list[str],
) -> int:
    count = 0
    for issue in sorted(set(issues)):
        if not issue:
            continue
        results = evaluate_for_draw(db, lottery_type=lottery_type, issue=issue)
        count += len(results)
    return count


def build_run_export(
    db: Session,
    *,
    run_id: UUID,
    fmt: str = "json",
) -> tuple[str, str, str]:
    """Return (filename, media_type, content)."""
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.id == run_id)
        .options(selectinload(RecommendationRun.tickets))
    )
    if run is None:
        raise NotFoundError("推荐记录不存在")

    tickets = sorted(run.tickets, key=lambda t: t.rank)
    ticket_ids = [t.id for t in tickets]
    results_by_ticket: dict[UUID, RecommendationResult] = {}
    if ticket_ids:
        for row in db.scalars(
            select(RecommendationResult).where(RecommendationResult.ticket_id.in_(ticket_ids))
        ).all():
            results_by_ticket[row.ticket_id] = row

    payload = {
        "id": str(run.id),
        "lottery_type": run.lottery_type,
        "target_issue": run.target_issue,
        "data_cutoff_issue": run.data_cutoff_issue,
        "data_snapshot_hash": run.data_snapshot_hash,
        "seed": run.seed,
        "candidate_count": run.candidate_count,
        "ai_status": run.ai_status,
        "ai_provider": run.ai_provider,
        "ai_model": run.ai_model,
        "status": run.status,
        "metrics": run.metrics or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "disclaimer": "模型评分/历史分析，不承诺中奖",
        "tickets": [
            {
                "rank": t.rank,
                "primary_numbers": list(t.primary_numbers),
                "secondary_numbers": list(t.secondary_numbers),
                "statistical_score": float(t.statistical_score),
                "ai_score": float(t.ai_score) if t.ai_score is not None else None,
                "final_score": float(t.final_score),
                "explanation": t.explanation,
                "primary_hits": (
                    results_by_ticket[t.id].primary_hits if t.id in results_by_ticket else None
                ),
                "secondary_hits": (
                    results_by_ticket[t.id].secondary_hits if t.id in results_by_ticket else None
                ),
                "prize_level": (
                    results_by_ticket[t.id].prize_level if t.id in results_by_ticket else None
                ),
            }
            for t in tickets
        ],
    }

    safe_issue = (run.target_issue or "unknown").replace("/", "-")
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "rank",
                "primary_numbers",
                "secondary_numbers",
                "statistical_score",
                "ai_score",
                "final_score",
                "primary_hits",
                "secondary_hits",
                "prize_level",
                "explanation",
            ]
        )
        for item in payload["tickets"]:
            writer.writerow(
                [
                    item["rank"],
                    " ".join(f"{n:02d}" for n in item["primary_numbers"]),
                    " ".join(f"{n:02d}" for n in item["secondary_numbers"]),
                    item["statistical_score"],
                    item["ai_score"] if item["ai_score"] is not None else "",
                    item["final_score"],
                    item["primary_hits"] if item["primary_hits"] is not None else "",
                    item["secondary_hits"] if item["secondary_hits"] is not None else "",
                    item["prize_level"] or "",
                    item["explanation"] or "",
                ]
            )
        content = buf.getvalue()
        return (
            f"lottopilot-{run.lottery_type}-{safe_issue}.csv",
            "text/csv; charset=utf-8",
            content,
        )

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        f"lottopilot-{run.lottery_type}-{safe_issue}.json",
        "application/json; charset=utf-8",
        content,
    )

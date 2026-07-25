"""Recommendation engine orchestration."""

from __future__ import annotations

from typing import Any
from uuid import UUID
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ValidationAppError
from app.models.draw import Draw
from app.models.recommendation import RecommendationRun, RecommendationTicket
from app.models.strategy import StrategyProfile
from app.models.system import Job
from app.services.ai.rerank_pipeline import maybe_apply_ai
from app.services.jobs import create_job, mark_job_failed, mark_job_running, mark_job_succeeded
from app.services.recommendation.candidates import generate_candidates
from app.services.recommendation.features import (
    HistoryDraw,
    historical_structure_baselines,
    number_stats,
)
from app.services.recommendation.scoring import score_candidate, select_diverse
from app.services.recommendation.seed import derive_seed, make_rng, snapshot_hash
from app.services.recommendation.strategy import merge_strategy_config
from app.utils.lottery import next_issue_guess
from app.utils.time import utcnow


def _load_history(db: Session, lottery_type: str) -> list[HistoryDraw]:
    rows = db.scalars(
        select(Draw)
        .where(Draw.lottery_type == lottery_type)
        .order_by(Draw.draw_date.desc(), Draw.issue.desc())
    ).all()
    return [
        HistoryDraw(
            issue=row.issue,
            draw_date=row.draw_date,
            primary_numbers=tuple(row.primary_numbers),
            secondary_numbers=tuple(row.secondary_numbers),
        )
        for row in rows
    ]


def ensure_default_strategy(db: Session, lottery_type: str) -> StrategyProfile:
    existing = db.scalar(
        select(StrategyProfile)
        .where(
            StrategyProfile.lottery_type == lottery_type,
            StrategyProfile.is_default.is_(True),
            StrategyProfile.is_active.is_(True),
        )
        .limit(1)
    )
    if existing:
        return existing
    profile = StrategyProfile(
        name="default",
        version="v1",
        lottery_type=lottery_type,
        config=merge_strategy_config(),
        is_default=True,
        is_active=True,
    )
    db.add(profile)
    db.flush()
    return profile



def run_recommendation(
    db: Session,
    *,
    lottery_type: str,
    target_issue: str | None = None,
    strategy_profile_id: UUID | None = None,
    seed: int | None = None,
    created_by: UUID | None = None,
    candidate_count: int | None = None,
    enable_ai: bool = True,
) -> RecommendationRun:
    started = time.perf_counter()
    settings = get_settings()
    history = _load_history(db, lottery_type)
    if len(history) < 5:
        raise ValidationAppError(
            "历史开奖数据不足，请先同步至少 5 期",
            code="INSUFFICIENT_HISTORY",
            details={"count": len(history)},
        )

    if strategy_profile_id:
        profile = db.get(StrategyProfile, strategy_profile_id)
        if profile is None or profile.lottery_type != lottery_type:
            raise ValidationAppError("策略配置不存在或不匹配彩种", code="STRATEGY_NOT_FOUND")
    else:
        profile = ensure_default_strategy(db, lottery_type)

    config = merge_strategy_config(profile.config if isinstance(profile.config, dict) else None)
    if candidate_count:
        config["candidate_count"] = int(candidate_count)

    latest_issue = history[0].issue
    target = target_issue or next_issue_guess(latest_issue)
    used_seed = seed if seed is not None else derive_seed(lottery_type, target, profile.version)
    rng = make_rng(used_seed)

    snap = snapshot_hash(
        [
            (
                d.issue,
                d.draw_date.isoformat(),
                d.primary_numbers,
                d.secondary_numbers,
            )
            for d in history
        ]
    )

    job = create_job(
        db,
        job_type="recommendation",
        payload_summary={
            "lottery_type": lottery_type,
            "target_issue": target,
            "strategy_profile_id": str(profile.id),
            "seed": used_seed,
            "enable_ai": enable_ai,
        },
        created_by=created_by,
        resource_type="recommendation_run",
    )
    run = RecommendationRun(
        job_id=job.id,
        lottery_type=lottery_type,
        target_issue=target,
        strategy_profile_id=profile.id,
        data_cutoff_issue=latest_issue,
        data_snapshot_hash=snap,
        seed=used_seed,
        candidate_count=0,
        ai_status="skipped",
        status="running",
        metrics={},
    )
    db.add(run)
    db.flush()
    job.resource_id = run.id
    mark_job_running(db, job, total=4)
    db.commit()

    try:
        primary_stats = number_stats(
            history,
            lottery_type=lottery_type,
            zone="primary",
            windows=config["windows"],
            lambda_decay=float(config["lambda_decay"]),
        )
        secondary_stats = number_stats(
            history,
            lottery_type=lottery_type,
            zone="secondary",
            windows=config["windows"],
            lambda_decay=float(config["lambda_decay"]),
        )
        baselines = historical_structure_baselines(history)
        candidates = generate_candidates(
            lottery_type=lottery_type,
            history=history,
            primary_stats=primary_stats,
            secondary_stats=secondary_stats,
            config=config,
            rng=rng,
        )
        run.candidate_count = len(candidates)
        job.progress_current = 1
        db.add(job)
        db.add(run)
        db.commit()

        latest_primary = set(history[0].primary_numbers)
        scored = [
            score_candidate(
                c,
                lottery_type=lottery_type,
                primary_stats=primary_stats,
                secondary_stats=secondary_stats,
                baselines=baselines,
                config=config,
                latest_primary=latest_primary,
            )
            for c in candidates
        ]
        selected, relax_level = select_diverse(
            scored,
            final_count=int(config["final_count"]),
            config=config,
        )
        if len(selected) < int(config["final_count"]):
            raise AppError("RECOMMENDATION_FAILED", "无法生成足够的多样化候选", status_code=500)

        job.progress_current = 2
        db.add(job)
        db.commit()

        # Optional AI limited rerank + explanation (fail-open).
        selected, ai_meta = maybe_apply_ai(
            db,
            settings=settings,
            lottery_type=lottery_type,
            target_issue=target,
            tickets=selected,
            enable_ai=enable_ai,
        )
        job.progress_current = 3
        db.add(job)
        db.commit()

        for item in selected:
            db.add(
                RecommendationTicket(
                    run_id=run.id,
                    rank=int(item["rank"]),
                    primary_numbers=item["primary_numbers"],
                    secondary_numbers=item["secondary_numbers"],
                    statistical_score=item["statistical_score"],
                    ai_score=item.get("ai_score"),
                    final_score=item.get("final_score", item["statistical_score"]),
                    feature_summary=item.get("feature_summary") or {},
                    tags={"labels": item.get("tags") or []},
                    explanation=item.get("explanation"),
                )
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        run.status = "succeeded"
        run.finished_at = utcnow()
        run.ai_status = str(ai_meta.get("ai_status") or "skipped")
        run.ai_provider = ai_meta.get("ai_provider")
        run.ai_model = ai_meta.get("ai_model")
        run.ai_prompt_version = ai_meta.get("ai_prompt_version")
        run.ai_response_hash = ai_meta.get("ai_response_hash")
        run.ai_metrics = ai_meta.get("ai_metrics") or {}
        if ai_meta.get("ai_config_id"):
            try:
                run.ai_config_id = UUID(str(ai_meta["ai_config_id"]))
            except Exception:  # noqa: BLE001
                run.ai_config_id = None
        run.metrics = {
            "elapsed_ms": elapsed_ms,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "diversity_relax_level": relax_level,
            "strategy_version": profile.version,
            "ai_weight": ai_meta.get("ai_weight", 0.0),
            "ai_status": run.ai_status,
        }
        mark_job_succeeded(db, job)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.finished_at = utcnow()
        run.metrics = {"error": str(getattr(exc, "message", exc))}
        mark_job_failed(
            db,
            job,
            code=getattr(exc, "code", "RECOMMENDATION_FAILED"),
            summary=str(getattr(exc, "message", exc)),
        )
        db.add(run)
        db.commit()
        raise
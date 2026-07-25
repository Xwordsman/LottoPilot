"""Walk-forward backtest engine (statistical only)."""

from __future__ import annotations

import random
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationAppError
from app.models.backtest import BacktestIssueResult, BacktestRun
from app.models.draw import Draw
from app.models.system import Job
from app.services.jobs import create_job, mark_job_failed, mark_job_running, mark_job_succeeded
from app.services.recommendation.engine import ensure_default_strategy
from app.services.recommendation.features import HistoryDraw, historical_structure_baselines, number_stats
from app.services.recommendation.candidates import generate_candidates
from app.services.recommendation.scoring import score_candidate, select_diverse
from app.services.recommendation.seed import derive_seed, make_rng
from app.services.recommendation.strategy import merge_strategy_config
from app.services.backtest_core import train_slice_before_target, validate_backtest_window
from app.utils.time import utcnow


def _hits(pred_primary: list[int], pred_secondary: list[int], actual: HistoryDraw) -> dict[str, int]:
    return {
        "primary_hits": len(set(pred_primary) & set(actual.primary_numbers)),
        "secondary_hits": len(set(pred_secondary) & set(actual.secondary_numbers)),
    }


def run_backtest(
    db: Session,
    *,
    lottery_type: str,
    start_issue: str,
    end_issue: str,
    seed: int | None = None,
    baseline_trials: int = 20,
    candidate_count: int = 2000,
    created_by: UUID | None = None,
) -> BacktestRun:
    rows = db.scalars(
        select(Draw)
        .where(Draw.lottery_type == lottery_type)
        .order_by(Draw.draw_date.asc(), Draw.issue.asc())
    ).all()
    history_all = [
        HistoryDraw(r.issue, r.draw_date, tuple(r.primary_numbers), tuple(r.secondary_numbers))
        for r in rows
    ]
    issues = [h.issue for h in history_all]
    try:
        start_idx, end_idx = validate_backtest_window(issues, start_issue, end_issue)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "INSUFFICIENT_HISTORY": "回测至少需要 10 期历史数据",
            "ISSUE_NOT_FOUND": "起止期号不在历史数据中",
            "INVALID_RANGE": "start_issue 必须小于 end_issue",
            "INSUFFICIENT_TRAINING": "起始期之前至少保留 5 期训练数据",
        }
        raise ValidationAppError(messages.get(code, "回测参数无效"), code=code) from exc

    profile = ensure_default_strategy(db, lottery_type)
    config = merge_strategy_config(profile.config if isinstance(profile.config, dict) else None)
    config["candidate_count"] = candidate_count
    used_seed = seed if seed is not None else derive_seed(lottery_type, f"{start_issue}-{end_issue}", profile.version)

    job = create_job(
        db,
        job_type="backtest",
        payload_summary={
            "lottery_type": lottery_type,
            "start_issue": start_issue,
            "end_issue": end_issue,
            "seed": used_seed,
        },
        created_by=created_by,
        resource_type="backtest_run",
    )
    run = BacktestRun(
        job_id=job.id,
        lottery_type=lottery_type,
        strategy_profile_id=profile.id,
        start_issue=start_issue,
        end_issue=end_issue,
        seed=used_seed,
        baseline_trials=baseline_trials,
        status="running",
        summary={},
        started_at=utcnow(),
    )
    db.add(run)
    db.flush()
    job.resource_id = run.id
    mark_job_running(db, job, total=end_idx - start_idx + 1)
    db.commit()

    try:
        issue_metrics: list[dict[str, Any]] = []
        total_primary_hits = 0
        total_secondary_hits = 0
        baseline_primary_hits = 0

        for idx in range(start_idx, end_idx + 1):
            t0 = time.perf_counter()
            target = history_all[idx]
            train = train_slice_before_target(history_all, idx)  # newest first; no future leak
            if len(train) < 5:
                continue
            local_seed = derive_seed(lottery_type, target.issue, f"{profile.version}:{used_seed}")
            rng = make_rng(local_seed)
            primary_stats = number_stats(
                train,
                lottery_type=lottery_type,
                zone="primary",
                windows=config["windows"],
                lambda_decay=float(config["lambda_decay"]),
            )
            secondary_stats = number_stats(
                train,
                lottery_type=lottery_type,
                zone="secondary",
                windows=config["windows"],
                lambda_decay=float(config["lambda_decay"]),
            )
            baselines = historical_structure_baselines(train)
            candidates = generate_candidates(
                lottery_type=lottery_type,
                history=train,
                primary_stats=primary_stats,
                secondary_stats=secondary_stats,
                config=config,
                rng=rng,
            )
            scored = [
                score_candidate(
                    c,
                    lottery_type=lottery_type,
                    primary_stats=primary_stats,
                    secondary_stats=secondary_stats,
                    baselines=baselines,
                    config=config,
                    latest_primary=set(train[0].primary_numbers),
                )
                for c in candidates
            ]
            selected, _relax = select_diverse(scored, final_count=5, config=config)

            tickets_payload = []
            best_primary = 0
            best_secondary = 0
            for ticket in selected:
                h = _hits(ticket["primary_numbers"], ticket["secondary_numbers"], target)
                best_primary = max(best_primary, h["primary_hits"])
                best_secondary = max(best_secondary, h["secondary_hits"])
                tickets_payload.append(
                    {
                        "rank": ticket["rank"],
                        "primary_numbers": ticket["primary_numbers"],
                        "secondary_numbers": ticket["secondary_numbers"],
                        "statistical_score": ticket["statistical_score"],
                        **h,
                    }
                )

            # random baseline
            rules_primary = list(range(1, 34 if lottery_type == "ssq" else 36))
            rules_secondary = list(range(1, 17 if lottery_type == "ssq" else 13))
            p_count = 6 if lottery_type == "ssq" else 5
            s_count = 1 if lottery_type == "ssq" else 2
            base_hits = []
            brng = random.Random(local_seed ^ 0xABCDEF)
            for _ in range(baseline_trials):
                p = sorted(brng.sample(rules_primary[: 33 if lottery_type == "ssq" else 35], p_count))
                s = sorted(brng.sample(rules_secondary[: 16 if lottery_type == "ssq" else 12], s_count))
                base_hits.append(_hits(p, s, target)["primary_hits"])
            baseline_avg = sum(base_hits) / max(1, len(base_hits))

            total_primary_hits += best_primary
            total_secondary_hits += best_secondary
            baseline_primary_hits += baseline_avg

            # map to draw ids
            target_draw = rows[idx]
            cutoff_draw = rows[idx - 1]
            db.add(
                BacktestIssueResult(
                    backtest_run_id=run.id,
                    target_draw_id=target_draw.id,
                    training_cutoff_draw_id=cutoff_draw.id,
                    tickets=tickets_payload,
                    hit_metrics={
                        "best_primary_hits": best_primary,
                        "best_secondary_hits": best_secondary,
                        "target_issue": target.issue,
                    },
                    baseline_metrics={"avg_primary_hits": baseline_avg, "trials": baseline_trials},
                    runtime_ms=int((time.perf_counter() - t0) * 1000),
                )
            )
            issue_metrics.append(
                {
                    "issue": target.issue,
                    "best_primary_hits": best_primary,
                    "best_secondary_hits": best_secondary,
                    "baseline_avg_primary_hits": baseline_avg,
                }
            )
            job.progress_current = idx - start_idx + 1
            db.add(job)
            db.commit()

        n = max(1, len(issue_metrics))
        run.status = "succeeded"
        run.finished_at = utcnow()
        run.summary = {
            "issues": len(issue_metrics),
            "avg_best_primary_hits": round(total_primary_hits / n, 4),
            "avg_best_secondary_hits": round(total_secondary_hits / n, 4),
            "avg_baseline_primary_hits": round(baseline_primary_hits / n, 4),
            "lift_primary_vs_baseline": round((total_primary_hits / n) - (baseline_primary_hits / n), 4),
            "issue_metrics": issue_metrics,
            "disclaimer": "回测指标仅为历史拟合观察，不代表未来收益或中奖承诺。",
        }
        mark_job_succeeded(db, job)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.finished_at = utcnow()
        run.summary = {"error": str(getattr(exc, "message", exc))}
        mark_job_failed(db, job, code=getattr(exc, "code", "BACKTEST_FAILED"), summary=str(getattr(exc, "message", exc)))
        db.add(run)
        db.commit()
        raise


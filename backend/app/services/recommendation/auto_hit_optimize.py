"""Official automatic optimizer for recommendation configs.

Product rule:
- User only clicks generate.
- System automatically searches for the best config under a fixed historical
  objective and uses it for the current 5 tickets.

Official objective (lexicographic / heavily weighted):
1) more prize-mapped tickets in walk-forward window
2) higher best primary hits among the 5
3) higher total primary hits
4) higher total secondary hits

This optimizes a historical hit/prize proxy. It does not change true lottery odds.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
import itertools
import time

from app.services.recommendation.candidates import generate_candidates
from app.services.recommendation.features import (
    HistoryDraw,
    historical_structure_baselines,
    number_stats,
)
from app.services.recommendation.prize_rules import evaluate_ticket_against_draw
from app.services.recommendation.scoring import score_candidate, select_diverse
from app.services.recommendation.seed import derive_seed, make_rng
from app.services.recommendation.strategy import merge_strategy_config

_CACHE: dict[str, dict[str, Any]] = {}

# Fixed product objective. Do not ask the user to choose.
OBJECTIVE_NAME = "historical_prize_then_hits"
OBJECTIVE_NOTE = (
    "Auto-optimal under historical walk-forward prize/hit proxy; "
    "not a claim of higher true winning probability."
)


@dataclass(frozen=True)
class AutoHitResult:
    config: dict[str, Any]
    meta: dict[str, Any]


def _apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    cfg = merge_strategy_config(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            merged = dict(cfg[key])
            merged.update(value)
            cfg[key] = merged
        else:
            cfg[key] = value
    return cfg


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    keys = [
        "number_score",
        "structure_score",
        "temporal_stability_score",
        "cooccurrence_score",
        "extreme_penalty",
    ]
    vals = [max(0.01, float(weights.get(k, 0.1))) for k in keys]

    total = sum(vals) or 1.0
    return {k: round(v / total, 6) for k, v in zip(keys, vals, strict=True)}


def _coarse_specs() -> list[tuple[str, dict[str, Any]]]:
    return [
        ("baseline", {}),
        (
            "number_hot",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.55,
                        "structure_score": 0.20,
                        "temporal_stability_score": 0.15,
                        "cooccurrence_score": 0.05,
                        "extreme_penalty": 0.05,
                    }
                ),
                "lambda_decay": 0.05,
                "sampling": {
                    "uniform_ratio": 0.15,
                    "weighted_ratio": 0.60,
                    "structure_ratio": 0.20,
                    "explore_ratio": 0.05,
                },
            },
        ),
        (
            "number_hot_mild",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.48,
                        "structure_score": 0.24,
                        "temporal_stability_score": 0.16,
                        "cooccurrence_score": 0.06,
                        "extreme_penalty": 0.06,
                    }
                ),
                "lambda_decay": 0.035,
            },
        ),
        (
            "structure_stable",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.26,
                        "structure_score": 0.44,
                        "temporal_stability_score": 0.20,
                        "cooccurrence_score": 0.05,
                        "extreme_penalty": 0.05,
                    }
                ),
                "lambda_decay": 0.018,
                "sampling": {
                    "uniform_ratio": 0.22,
                    "weighted_ratio": 0.28,
                    "structure_ratio": 0.45,
                    "explore_ratio": 0.05,
                },
            },
        ),
        (
            "mean_revert",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.50,
                        "structure_score": 0.25,
                        "temporal_stability_score": 0.08,
                        "cooccurrence_score": 0.07,
                        "extreme_penalty": 0.10,
                    }
                ),
                "lambda_decay": 0.012,
                "sampling": {
                    "uniform_ratio": 0.28,
                    "weighted_ratio": 0.32,
                    "structure_ratio": 0.28,
                    "explore_ratio": 0.12,
                },
            },
        ),
        (
            "cooccur",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.32,
                        "structure_score": 0.24,
                        "temporal_stability_score": 0.14,
                        "cooccurrence_score": 0.24,
                        "extreme_penalty": 0.06,
                    }
                ),
                "lambda_decay": 0.028,
            },
        ),
        (
            "stable_cover",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.36,
                        "structure_score": 0.30,
                        "temporal_stability_score": 0.22,
                        "cooccurrence_score": 0.06,
                        "extreme_penalty": 0.06,
                    }
                ),
                "diversity": {
                    "primary_overlap_max": 2,
                    "secondary_identical_penalty": True,
                    "mmr_lambda": 0.48,
                },
                "sampling": {
                    "uniform_ratio": 0.35,
                    "weighted_ratio": 0.30,
                    "structure_ratio": 0.25,
                    "explore_ratio": 0.10,
                },
            },
        ),
        (
            "explore_mix",
            {
                "weights": _normalize_weights(
                    {
                        "number_score": 0.40,
                        "structure_score": 0.28,
                        "temporal_stability_score": 0.16,
                        "cooccurrence_score": 0.08,
                        "extreme_penalty": 0.08,
                    }
                ),
                "lambda_decay": 0.03,
                "sampling": {
                    "uniform_ratio": 0.45,
                    "weighted_ratio": 0.25,
                    "structure_ratio": 0.18,
                    "explore_ratio": 0.12,
                },
            },
        ),
        (
            "decay_fast",
            {
                "lambda_decay": 0.06,
                "weights": _normalize_weights(
                    {
                        "number_score": 0.52,
                        "structure_score": 0.22,
                        "temporal_stability_score": 0.14,
                        "cooccurrence_score": 0.06,
                        "extreme_penalty": 0.06,
                    }
                ),
            },
        ),
        (
            "decay_slow",
            {
                "lambda_decay": 0.01,
                "weights": _normalize_weights(
                    {
                        "number_score": 0.34,
                        "structure_score": 0.34,
                        "temporal_stability_score": 0.20,
                        "cooccurrence_score": 0.06,
                        "extreme_penalty": 0.06,
                    }
                ),
            },
        ),
    ]


def _objective_tuple(
    *,
    lottery_type: str,
    tickets: list[dict[str, Any]],
    actual: HistoryDraw,
) -> tuple[int, int, int, int, float]:
    """Higher tuple is better under official product objective."""
    prize_count = 0
    best_primary = 0
    total_primary = 0
    total_secondary = 0
    prize_quality = 0.0
    for ticket in tickets:
        ev = evaluate_ticket_against_draw(
            lottery_type=lottery_type,
            ticket_primary=list(ticket["primary_numbers"]),
            ticket_secondary=list(ticket["secondary_numbers"]),
            draw_primary=list(actual.primary_numbers),
            draw_secondary=list(actual.secondary_numbers),
        )
        ph = int(ev["primary_hits"])
        sh = int(ev["secondary_hits"])
        best_primary = max(best_primary, ph)
        total_primary += ph
        total_secondary += sh
        level = ev.get("prize_level")
        if level is not None:
            prize_count += 1
            try:
                lvl = int(str(level))
                prize_quality += max(0.0, 20.0 - lvl)
            except ValueError:
                prize_quality += 5.0
    return (prize_count, best_primary, total_primary, total_secondary, round(prize_quality, 4))


def _tuple_to_score(t: tuple[int, int, int, int, float]) -> float:
    prize_count, best_primary, total_primary, total_secondary, prize_quality = t
    return (
        prize_count * 100000.0
        + best_primary * 1000.0
        + total_primary * 100.0
        + total_secondary * 40.0
        + prize_quality
    )


def _run_one_issue(
    *,
    lottery_type: str,
    train_newest_first: list[HistoryDraw],
    actual: HistoryDraw,
    config: dict[str, Any],
    seed: int,
) -> tuple[int, int, int, int, float]:
    if len(train_newest_first) < 5:
        return (0, 0, 0, 0, 0.0)
    rng = make_rng(seed)
    primary_stats = number_stats(
        train_newest_first,
        lottery_type=lottery_type,
        zone="primary",
        windows=config["windows"],
        lambda_decay=float(config["lambda_decay"]),
    )
    secondary_stats = number_stats(
        train_newest_first,
        lottery_type=lottery_type,
        zone="secondary",
        windows=config["windows"],
        lambda_decay=float(config["lambda_decay"]),
    )
    baselines = historical_structure_baselines(train_newest_first)
    local_cfg = deepcopy(config)
    local_cfg["candidate_count"] = int(
        local_cfg.get("_search_candidate_count") or local_cfg.get("candidate_count") or 600
    )
    local_cfg["final_count"] = int(local_cfg.get("final_count") or 5)
    candidates = generate_candidates(
        lottery_type=lottery_type,
        history=train_newest_first,
        primary_stats=primary_stats,
        secondary_stats=secondary_stats,
        config=local_cfg,
        rng=rng,
    )
    latest_primary = set(train_newest_first[0].primary_numbers)
    scored = [
        score_candidate(
            candidate,
            lottery_type=lottery_type,
            primary_stats=primary_stats,
            secondary_stats=secondary_stats,
            baselines=baselines,
            config=local_cfg,
            latest_primary=latest_primary,
        )
        for candidate in candidates
    ]
    selected, _ = select_diverse(
        scored,
        final_count=int(local_cfg["final_count"]),
        config=local_cfg,
    )
    if not selected:
        return (0, 0, 0, 0, 0.0)
    return _objective_tuple(lottery_type=lottery_type, tickets=selected, actual=actual)


def _sum_tuples(
    values: list[tuple[int, int, int, int, float]],
) -> tuple[int, int, int, int, float]:
    if not values:
        return (0, 0, 0, 0, 0.0)
    return (
        sum(v[0] for v in values),
        sum(v[1] for v in values),
        sum(v[2] for v in values),
        sum(v[3] for v in values),
        round(sum(v[4] for v in values), 4),
    )


def _evaluate_config(
    *,
    name: str,
    cfg: dict[str, Any],
    lottery_type: str,
    chrono: list[HistoryDraw],
    start_idx: int,
    end_idx: int,
    seed: int,
    search_candidate_count: int,
) -> dict[str, Any]:
    cfg = deepcopy(cfg)
    cfg["_search_candidate_count"] = search_candidate_count
    parts: list[tuple[int, int, int, int, float]] = []
    for idx in range(start_idx, end_idx + 1):
        actual = chrono[idx]
        train = list(reversed(chrono[:idx]))
        local_seed = derive_seed(lottery_type, actual.issue, f"auto-opt:{name}:{seed}")
        parts.append(
            _run_one_issue(
                lottery_type=lottery_type,
                train_newest_first=train,
                actual=actual,
                config=cfg,
                seed=local_seed,
            )
        )
    total = _sum_tuples(parts)
    n_eval = max(1, len(parts))
    avg_score = _tuple_to_score(total) / n_eval
    return {
        "name": name,
        "score": round(avg_score, 6),
        "issues_evaluated": n_eval,
        "totals": {
            "prize_count": total[0],
            "best_primary_sum": total[1],
            "primary_hits": total[2],
            "secondary_hits": total[3],
            "prize_quality": total[4],
        },
        "config": cfg,
    }


def _local_refine_specs(best_cfg: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Local search around current best weights/lambda/diversity."""
    base_w = dict(best_cfg.get("weights") or {})
    base_lambda = float(best_cfg.get("lambda_decay") or 0.03)
    specs: list[tuple[str, dict[str, Any]]] = []
    deltas = [-0.06, -0.03, 0.03, 0.06]
    for key, delta in itertools.product(
        ["number_score", "structure_score", "temporal_stability_score", "cooccurrence_score"],
        deltas,
    ):
        weights = dict(base_w)
        weights[key] = float(weights.get(key, 0.2)) + delta
        specs.append(
            (
                f"refine_{key}_{delta:+.2f}",
                {
                    "weights": _normalize_weights(weights),
                    "lambda_decay": base_lambda,
                },
            )
        )
    for lam in [base_lambda * 0.7, base_lambda * 1.3, base_lambda * 1.6]:
        specs.append(
            (
                f"refine_lambda_{lam:.4f}",
                {
                    "weights": _normalize_weights(base_w),
                    "lambda_decay": max(0.005, min(0.08, lam)),
                },
            )
        )
    specs.append(
        (
            "refine_diversity_tight",
            {
                "weights": _normalize_weights(base_w),
                "lambda_decay": base_lambda,
                "diversity": {
                    "primary_overlap_max": 2,
                    "secondary_identical_penalty": True,
                    "mmr_lambda": 0.5,
                },
            },
        )
    )
    return specs


def search_best_hit_config(
    *,
    lottery_type: str,
    history_newest_first: list[HistoryDraw],
    base_config: dict[str, Any] | None = None,
    seed: int,
    window: int | None = None,
    search_candidate_count: int = 450,
    refine_top_k: int = 1,
    max_refine: int = 8,
) -> AutoHitResult:
    started = time.perf_counter()
    base = merge_strategy_config(base_config)
    history_count = len(history_newest_first)
    if history_count < 12:
        meta = {
            "mode": "auto_optimal",
            "status": "skipped_insufficient_history",
            "objective": OBJECTIVE_NAME,
            "reason": "need_at_least_12_draws",
            "history_count": history_count,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "note": OBJECTIVE_NOTE,
        }
        return AutoHitResult(config=base, meta=meta)

    # Adaptive window: more history => longer evaluation, capped for latency.
    if window is None:
        window = max(12, min(20, history_count // 3))
    chrono = list(reversed(history_newest_first))
    end_idx = len(chrono) - 1
    start_idx = max(5, end_idx - window + 1)

    leaderboard: list[dict[str, Any]] = []
    for name, overrides in _coarse_specs():
        cfg = _apply_overrides(base, overrides)
        row = _evaluate_config(
            name=name,
            cfg=cfg,
            lottery_type=lottery_type,
            chrono=chrono,
            start_idx=start_idx,
            end_idx=end_idx,
            seed=seed,
            search_candidate_count=search_candidate_count,
        )
        leaderboard.append(row)

    leaderboard.sort(key=lambda row: row["score"], reverse=True)

    # Local refinement around top configs.
    refined: list[dict[str, Any]] = []
    for top in leaderboard[: max(1, refine_top_k)]:
        for name, overrides in _local_refine_specs(top["config"])[: max_refine]:
            cfg = _apply_overrides(top["config"], overrides)
            refined.append(
                _evaluate_config(
                    name=f"{top['name']}::{name}",
                    cfg=cfg,
                    lottery_type=lottery_type,
                    chrono=chrono,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    seed=seed,
                    search_candidate_count=max(400, search_candidate_count - 100),
                )
            )
    if refined:
        leaderboard.extend(refined)
        leaderboard.sort(key=lambda row: row["score"], reverse=True)

    best = leaderboard[0]
    best_cfg = deepcopy(best["config"])
    best_cfg.pop("_search_candidate_count", None)
    # Final generate uses a large candidate pool.
    best_cfg["candidate_count"] = max(int(base.get("candidate_count") or 8000), 8000)
    best_cfg["final_count"] = 5
    best_cfg["auto_hit_optimize"] = True
    best_cfg["optimization_goal"] = OBJECTIVE_NAME

    meta = {
        "mode": "auto_optimal",
        "status": "selected",
        "objective": OBJECTIVE_NAME,
        "selected_variant": best["name"],
        "selected_score": best["score"],
        "selected_totals": best.get("totals"),
        "window": window,
        "search_candidate_count": search_candidate_count,
        "candidates_searched": len(leaderboard),
        "leaderboard": [
            {
                "name": row["name"],
                "score": row["score"],
                "issues_evaluated": row["issues_evaluated"],
                "totals": row.get("totals"),
            }
            for row in leaderboard[:12]
        ],
        "cutoff_issue": history_newest_first[0].issue,
        "history_count": history_count,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "note": OBJECTIVE_NOTE,
    }
    return AutoHitResult(config=best_cfg, meta=meta)


def get_auto_hit_config(
    *,
    lottery_type: str,
    history_newest_first: list[HistoryDraw],
    base_config: dict[str, Any] | None = None,
    seed: int,
    force_refresh: bool = False,
) -> AutoHitResult:
    if not history_newest_first:
        cfg = merge_strategy_config(base_config)
        return AutoHitResult(
            config=cfg,
            meta={
                "mode": "auto_optimal",
                "status": "empty_history",
                "objective": OBJECTIVE_NAME,
                "note": OBJECTIVE_NOTE,
            },
        )

    cutoff = history_newest_first[0].issue
    cache_key = f"{lottery_type}:{cutoff}:{OBJECTIVE_NAME}"
    if not force_refresh and cache_key in _CACHE:
        cached = _CACHE[cache_key]
        return AutoHitResult(
            config=deepcopy(cached["config"]),
            meta={**cached["meta"], "cache_hit": True},
        )

    result = search_best_hit_config(
        lottery_type=lottery_type,
        history_newest_first=history_newest_first,
        base_config=base_config,
        seed=seed,
    )
    _CACHE[cache_key] = {"config": deepcopy(result.config), "meta": dict(result.meta)}
    result.meta["cache_hit"] = False
    return result


def clear_auto_hit_cache(lottery_type: str | None = None) -> None:
    if lottery_type is None:
        _CACHE.clear()
        return
    for key in list(_CACHE):
        if key.startswith(f"{lottery_type}:"):
            _CACHE.pop(key, None)

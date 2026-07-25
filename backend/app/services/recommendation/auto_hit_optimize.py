"""Automatic historical-hit oriented strategy selection.

This module does NOT claim to change true lottery odds. It selects, from a small
search space, the scoring/sampling configuration that performed best on a recent
walk-forward window (primary/secondary hits and mapped prize levels). The chosen
config is then used for the current recommendation run automatically.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
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


def _variant_grid(base: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    specs: list[tuple[str, dict[str, Any]]] = [
        ("baseline", {}),
        (
            "number_hot",
            {
                "weights": {
                    "number_score": 0.55,
                    "structure_score": 0.20,
                    "temporal_stability_score": 0.15,
                    "cooccurrence_score": 0.05,
                    "extreme_penalty": 0.05,
                },
                "lambda_decay": 0.045,
                "sampling": {
                    "uniform_ratio": 0.20,
                    "weighted_ratio": 0.55,
                    "structure_ratio": 0.20,
                    "explore_ratio": 0.05,
                },
            },
        ),
        (
            "structure_stable",
            {
                "weights": {
                    "number_score": 0.28,
                    "structure_score": 0.42,
                    "temporal_stability_score": 0.20,
                    "cooccurrence_score": 0.05,
                    "extreme_penalty": 0.05,
                },
                "lambda_decay": 0.02,
                "sampling": {
                    "uniform_ratio": 0.25,
                    "weighted_ratio": 0.30,
                    "structure_ratio": 0.40,
                    "explore_ratio": 0.05,
                },
            },
        ),
        (
            "mean_revert_missing",
            {
                "weights": {
                    "number_score": 0.48,
                    "structure_score": 0.27,
                    "temporal_stability_score": 0.10,
                    "cooccurrence_score": 0.05,
                    "extreme_penalty": 0.10,
                },
                "lambda_decay": 0.015,
                "sampling": {
                    "uniform_ratio": 0.30,
                    "weighted_ratio": 0.35,
                    "structure_ratio": 0.25,
                    "explore_ratio": 0.10,
                },
            },
        ),
        (
            "cooccur_focus",
            {
                "weights": {
                    "number_score": 0.34,
                    "structure_score": 0.26,
                    "temporal_stability_score": 0.15,
                    "cooccurrence_score": 0.20,
                    "extreme_penalty": 0.05,
                },
                "lambda_decay": 0.03,
            },
        ),
        (
            "diverse_cover",
            {
                "weights": {
                    "number_score": 0.38,
                    "structure_score": 0.28,
                    "temporal_stability_score": 0.18,
                    "cooccurrence_score": 0.08,
                    "extreme_penalty": 0.08,
                },
                "diversity": {
                    "primary_overlap_max": 2,
                    "secondary_identical_penalty": True,
                    "mmr_lambda": 0.45,
                },
                "sampling": {
                    "uniform_ratio": 0.40,
                    "weighted_ratio": 0.30,
                    "structure_ratio": 0.20,
                    "explore_ratio": 0.10,
                },
            },
        ),
    ]
    return [(name, _apply_overrides(base, overrides)) for name, overrides in specs]


def _objective_for_tickets(
    *,
    lottery_type: str,
    tickets: list[dict[str, Any]],
    actual: HistoryDraw,
) -> float:
    score = 0.0
    best_primary = 0
    any_prize = 0
    for ticket in tickets:
        ev = evaluate_ticket_against_draw(
            lottery_type=lottery_type,
            ticket_primary=list(ticket["primary_numbers"]),
            ticket_secondary=list(ticket["secondary_numbers"]),
            draw_primary=list(actual.primary_numbers),
            draw_secondary=list(actual.secondary_numbers),
        )
        primary_hits = int(ev["primary_hits"])
        secondary_hits = int(ev["secondary_hits"])
        best_primary = max(best_primary, primary_hits)
        score += primary_hits * 1.0 + secondary_hits * 1.25
        level = ev.get("prize_level")
        if level is not None:
            any_prize += 1
            try:
                lvl = int(str(level))
                score += max(0.0, 18.0 - lvl * 1.5)
            except ValueError:
                score += 6.0
    score += best_primary * 0.75
    score += any_prize * 4.0
    return score


def _run_one_issue(
    *,
    lottery_type: str,
    train_newest_first: list[HistoryDraw],
    actual: HistoryDraw,
    config: dict[str, Any],
    seed: int,
) -> float:
    if len(train_newest_first) < 5:
        return 0.0
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
        local_cfg.get("_search_candidate_count") or local_cfg.get("candidate_count") or 800
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
        return 0.0
    return _objective_for_tickets(lottery_type=lottery_type, tickets=selected, actual=actual)


def search_best_hit_config(
    *,
    lottery_type: str,
    history_newest_first: list[HistoryDraw],
    base_config: dict[str, Any] | None = None,
    seed: int,
    window: int = 12,
    search_candidate_count: int = 500,
) -> AutoHitResult:
    started = time.perf_counter()
    base = merge_strategy_config(base_config)
    if len(history_newest_first) < 12:
        meta = {
            "mode": "auto_hit",
            "status": "skipped_insufficient_history",
            "reason": "need_at_least_12_draws",
            "history_count": len(history_newest_first),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "note": "Optimized on historical walk-forward hit/prize proxy; not a promise of future winning odds.",
        }
        return AutoHitResult(config=base, meta=meta)

    chrono = list(reversed(history_newest_first))
    end_idx = len(chrono) - 1
    start_idx = max(5, end_idx - window + 1)
    variants = _variant_grid(base)

    leaderboard: list[dict[str, Any]] = []
    best_name = "baseline"
    best_cfg = variants[0][1]
    best_score = float("-inf")

    for name, cfg in variants:
        cfg = deepcopy(cfg)
        cfg["_search_candidate_count"] = search_candidate_count
        total = 0.0
        n_eval = 0
        for idx in range(start_idx, end_idx + 1):
            actual = chrono[idx]
            train = list(reversed(chrono[:idx]))
            local_seed = derive_seed(lottery_type, actual.issue, f"auto-hit:{name}:{seed}")
            total += _run_one_issue(
                lottery_type=lottery_type,
                train_newest_first=train,
                actual=actual,
                config=cfg,
                seed=local_seed,
            )
            n_eval += 1
        avg = total / max(1, n_eval)
        leaderboard.append({"name": name, "score": round(avg, 6), "issues_evaluated": n_eval})
        if avg > best_score:
            best_score = avg
            best_name = name
            best_cfg = cfg

    best_cfg = deepcopy(best_cfg)
    best_cfg.pop("_search_candidate_count", None)
    if int(best_cfg.get("candidate_count") or 0) < 5000:
        best_cfg["candidate_count"] = max(int(base.get("candidate_count") or 5000), 5000)

    meta = {
        "mode": "auto_hit",
        "status": "selected",
        "selected_variant": best_name,
        "selected_score": round(best_score, 6),
        "window": window,
        "search_candidate_count": search_candidate_count,
        "leaderboard": sorted(leaderboard, key=lambda row: row["score"], reverse=True),
        "cutoff_issue": history_newest_first[0].issue,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "note": "Optimized on historical walk-forward hit/prize proxy; not a promise of future winning odds.",
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
        return AutoHitResult(config=cfg, meta={"mode": "auto_hit", "status": "empty_history"})

    cutoff = history_newest_first[0].issue
    cache_key = f"{lottery_type}:{cutoff}"
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

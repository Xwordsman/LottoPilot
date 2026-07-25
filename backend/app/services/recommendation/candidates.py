"""Candidate generation for lottery recommendations."""

from __future__ import annotations

from typing import Any
import itertools
import math

from app.core.constants import LOTTERY_RULES
from app.services.recommendation.features import HistoryDraw
from app.utils.lottery import validate_ticket_numbers


def _sample_without_replacement(rng, population: list[int], weights: list[float], k: int) -> list[int]:
    chosen: list[int] = []
    pool = list(population)
    w = list(weights)
    for _ in range(k):
        total = sum(w)
        if total <= 0:
            # fallback uniform among remaining
            idx = rng.randrange(len(pool))
        else:
            r = rng.random() * total
            acc = 0.0
            idx = len(pool) - 1
            for i, weight in enumerate(w):
                acc += weight
                if r <= acc:
                    idx = i
                    break
        chosen.append(pool.pop(idx))
        w.pop(idx)
    return sorted(chosen)


def _number_weights(stats: dict[int, dict[str, float]], numbers: list[int]) -> list[float]:
    weights: list[float] = []
    for n in numbers:
        s = stats[n]
        # blend frequency and moderate missing preference
        missing = s["missing"]
        missing_score = max(0.05, 1.0 - abs((missing / 20.0) - 0.4))
        w = 0.45 * s["decay_freq"] + 0.35 * s["freq_w30"] + 0.20 * missing_score
        weights.append(max(0.01, w))
    return weights


def generate_candidates(
    *,
    lottery_type: str,
    history: list[HistoryDraw],
    primary_stats: dict[int, dict[str, float]],
    secondary_stats: dict[int, dict[str, float]],
    config: dict[str, Any],
    rng,
) -> list[dict[str, Any]]:
    rules = LOTTERY_RULES[lottery_type]
    p_count = int(rules["primary_count"])
    s_count = int(rules["secondary_count"])
    p_nums = list(range(int(rules["primary_min"]), int(rules["primary_max"]) + 1))
    s_nums = list(range(int(rules["secondary_min"]), int(rules["secondary_max"]) + 1))

    total = int(config.get("candidate_count", 20000))
    ratios = config["sampling"]
    n_uniform = int(total * ratios["uniform_ratio"])
    n_weighted = int(total * ratios["weighted_ratio"])
    n_structure = int(total * ratios["structure_ratio"])
    n_explore = max(0, total - n_uniform - n_weighted - n_structure)

    primary_w = _number_weights(primary_stats, p_nums)
    secondary_w = _number_weights(secondary_stats, s_nums)

    # structure targets from history
    sums = [sum(d.primary_numbers) for d in history[:120] if d.primary_numbers]
    sum_lo = min(sums) if sums else sum(p_nums[:p_count])
    sum_hi = max(sums) if sums else sum(p_nums[-p_count:])
    sum_mean = sum(sums) / len(sums) if sums else (sum_lo + sum_hi) / 2

    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    candidates: list[dict[str, Any]] = []

    def add(primary: list[int], secondary: list[int], source: str) -> None:
        try:
            primary, secondary = validate_ticket_numbers(lottery_type, primary, secondary)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return
        key = (tuple(primary), tuple(secondary))
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "primary_numbers": primary,
                "secondary_numbers": secondary,
                "source": source,
            }
        )

    # 1) uniform
    for _ in range(n_uniform):
        primary = sorted(rng.sample(p_nums, p_count))
        secondary = sorted(rng.sample(s_nums, s_count))
        add(primary, secondary, "uniform")

    # 2) weighted
    for _ in range(n_weighted):
        primary = _sample_without_replacement(rng, p_nums, primary_w, p_count)
        secondary = _sample_without_replacement(rng, s_nums, secondary_w, s_count)
        add(primary, secondary, "weighted")

    # 3) structure-oriented: reject until sum near historical mean band
    attempts = 0
    while len([c for c in candidates if c["source"] == "structure"]) < n_structure and attempts < n_structure * 20:
        attempts += 1
        primary = _sample_without_replacement(rng, p_nums, primary_w, p_count)
        ssum = sum(primary)
        # accept if within expanded band around mean
        if abs(ssum - sum_mean) > max(12, (sum_hi - sum_lo) * 0.35):
            # soft: still accept occasionally
            if rng.random() > 0.25:
                continue
        secondary = _sample_without_replacement(rng, s_nums, secondary_w, s_count)
        add(primary, secondary, "structure")

    # 4) explore: reverse weights (favor cold)
    rev_primary = [1.0 / w for w in primary_w]
    rev_secondary = [1.0 / w for w in secondary_w]
    for _ in range(n_explore):
        primary = _sample_without_replacement(rng, p_nums, rev_primary, p_count)
        secondary = _sample_without_replacement(rng, s_nums, rev_secondary, s_count)
        add(primary, secondary, "explore")

    # Ensure minimum candidates even if collisions high
    guard = 0
    while len(candidates) < min(1000, total) and guard < total * 2:
        guard += 1
        primary = sorted(rng.sample(p_nums, p_count))
        secondary = sorted(rng.sample(s_nums, s_count))
        add(primary, secondary, "uniform")

    return candidates

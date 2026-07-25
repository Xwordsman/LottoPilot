"""Feature builders for recommendation scoring."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

from app.core.constants import LOTTERY_RULES


@dataclass(frozen=True)
class HistoryDraw:
    issue: str
    draw_date: date
    primary_numbers: tuple[int, ...]
    secondary_numbers: tuple[int, ...]


def _window_slice(draws: list[HistoryDraw], window: int) -> list[HistoryDraw]:
    if window <= 0:
        return draws
    return draws[:window]


def number_stats(
    draws: list[HistoryDraw],
    *,
    lottery_type: str,
    zone: str,
    windows: list[int],
    lambda_decay: float,
) -> dict[int, dict[str, float]]:
    rules = LOTTERY_RULES[lottery_type]
    if zone == "primary":
        lo, hi = int(rules["primary_min"]), int(rules["primary_max"])
        getter = lambda d: d.primary_numbers  # noqa: E731
    else:
        lo, hi = int(rules["secondary_min"]), int(rules["secondary_max"])
        getter = lambda d: d.secondary_numbers  # noqa: E731

    stats: dict[int, dict[str, float]] = {
        n: {
            "freq_full": 0.0,
            "freq_w30": 0.0,
            "freq_w60": 0.0,
            "freq_w120": 0.0,
            "decay_freq": 0.0,
            "missing": float(len(draws)),
            "trend": 0.0,
        }
        for n in range(lo, hi + 1)
    }

    # missing: newest first
    for n in range(lo, hi + 1):
        missing = 0
        for d in draws:
            if n in getter(d):
                break
            missing += 1
        stats[n]["missing"] = float(missing)

    for window_key, window in (("full", 0), ("w30", 30), ("w60", 60), ("w120", 120)):
        subset = _window_slice(draws, window)
        counter: Counter[int] = Counter()
        for d in subset:
            counter.update(getter(d))
        denom = max(1, len(subset))
        for n in range(lo, hi + 1):
            stats[n][f"freq_{window_key}"] = counter.get(n, 0) / denom

    # decay frequency
    for age, d in enumerate(draws):
        weight = math.exp(-lambda_decay * age)
        for n in getter(d):
            stats[n]["decay_freq"] += weight
    if draws:
        max_decay = max(v["decay_freq"] for v in stats.values()) or 1.0
        for n in stats:
            stats[n]["decay_freq"] /= max_decay
            stats[n]["trend"] = stats[n]["freq_w30"] - stats[n]["freq_w120"]

    # keep only requested windows for future use
    _ = windows
    return stats


def normalize_missing_score(missing: float, max_missing: float) -> float:
    if max_missing <= 0:
        return 0.5
    # moderate missing preferred: map via inverted parabola-ish
    x = missing / max_missing
    return max(0.0, 1.0 - abs(x - 0.35) / 0.65)


def combination_structure_features(
    primary: list[int],
    *,
    lottery_type: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    nums = sorted(primary)
    odd = sum(1 for n in nums if n % 2 == 1)
    even = len(nums) - odd
    size_split = int(config["size_split"][lottery_type])
    small = sum(1 for n in nums if n <= size_split)
    large = len(nums) - small
    zones = config["zones"][lottery_type]
    zone_counts = []
    for lo, hi in zones:
        zone_counts.append(sum(1 for n in nums if lo <= n <= hi))
    consecutive = 0
    max_run = 1
    run = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            consecutive += 1
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    gaps = [nums[i] - nums[i - 1] for i in range(1, len(nums))]
    gap_mean = sum(gaps) / len(gaps) if gaps else 0.0
    gap_var = (
        sum((g - gap_mean) ** 2 for g in gaps) / len(gaps) if gaps else 0.0
    )
    return {
        "sum": sum(nums),
        "span": nums[-1] - nums[0] if nums else 0,
        "odd": odd,
        "even": even,
        "odd_even": f"{odd}:{even}",
        "small": small,
        "large": large,
        "zones": zone_counts,
        "zone_pattern": "-".join(map(str, zone_counts)),
        "consecutive_pairs": consecutive,
        "max_run": max_run,
        "gap_mean": round(gap_mean, 4),
        "gap_var": round(gap_var, 4),
        "tails": [n % 10 for n in nums],
    }


def historical_structure_baselines(draws: Iterable[HistoryDraw]) -> dict[str, Any]:
    sums: list[int] = []
    spans: list[int] = []
    for d in draws:
        p = list(d.primary_numbers)
        if not p:
            continue
        sums.append(sum(p))
        spans.append(max(p) - min(p))
    if not sums:
        return {"sum_p10": 0, "sum_p90": 0, "span_p10": 0, "span_p90": 0, "sum_mean": 0, "span_mean": 0}

    def pct(values: list[int], q: float) -> float:
        ordered = sorted(values)
        idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
        return float(ordered[idx])

    return {
        "sum_p10": pct(sums, 0.10),
        "sum_p90": pct(sums, 0.90),
        "span_p10": pct(spans, 0.10),
        "span_p90": pct(spans, 0.90),
        "sum_mean": sum(sums) / len(sums),
        "span_mean": sum(spans) / len(spans),
    }

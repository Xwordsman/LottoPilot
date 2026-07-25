"""Statistical feature computation for lottery draws."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Literal

from app.core.constants import LOTTERY_RULES

LotteryType = Literal["ssq", "dlt"]


@dataclass(frozen=True)
class DrawView:
    issue: str
    draw_date: date
    primary_numbers: list[int]
    secondary_numbers: list[int]


def _rules(lottery_type: LotteryType) -> dict[str, Any]:
    return LOTTERY_RULES[lottery_type]


def frequency(
    draws: Iterable[DrawView],
    *,
    lottery_type: LotteryType,
    zone: Literal["primary", "secondary"] = "primary",
    window: int | None = None,
) -> list[dict[str, Any]]:
    items = list(draws)
    if window is not None and window > 0:
        items = items[:window]
    rules = _rules(lottery_type)
    if zone == "primary":
        lo, hi = int(rules["primary_min"]), int(rules["primary_max"])
        counter: Counter[int] = Counter()
        for d in items:
            counter.update(d.primary_numbers)
    else:
        lo, hi = int(rules["secondary_min"]), int(rules["secondary_max"])
        counter = Counter()
        for d in items:
            counter.update(d.secondary_numbers)

    total = sum(counter.values()) or 1
    return [
        {
            "number": n,
            "count": counter.get(n, 0),
            "ratio": round(counter.get(n, 0) / total, 6),
        }
        for n in range(lo, hi + 1)
    ]


def missing_streaks(
    draws: Iterable[DrawView],
    *,
    lottery_type: LotteryType,
    zone: Literal["primary", "secondary"] = "primary",
) -> list[dict[str, Any]]:
    """Compute current missing count for each number.

    `draws` must be ordered from newest to oldest.
    """
    items = list(draws)
    rules = _rules(lottery_type)
    if zone == "primary":
        lo, hi = int(rules["primary_min"]), int(rules["primary_max"])
        getter = lambda d: set(d.primary_numbers)  # noqa: E731
    else:
        lo, hi = int(rules["secondary_min"]), int(rules["secondary_max"])
        getter = lambda d: set(d.secondary_numbers)  # noqa: E731

    result: list[dict[str, Any]] = []
    for n in range(lo, hi + 1):
        missing = 0
        last_issue: str | None = None
        for d in items:
            if n in getter(d):
                last_issue = d.issue
                break
            missing += 1
        result.append(
            {
                "number": n,
                "missing": missing,
                "last_issue": last_issue,
            }
        )
    return result


def sum_span_odd_even(draws: Iterable[DrawView]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d in draws:
        primary = d.primary_numbers
        if not primary:
            continue
        odd = sum(1 for n in primary if n % 2 == 1)
        even = len(primary) - odd
        rows.append(
            {
                "issue": d.issue,
                "draw_date": d.draw_date.isoformat(),
                "sum": sum(primary),
                "span": max(primary) - min(primary),
                "odd": odd,
                "even": even,
                "odd_even": f"{odd}:{even}",
            }
        )
    return rows


def zone_distribution(
    draws: Iterable[DrawView],
    *,
    lottery_type: LotteryType,
) -> list[dict[str, Any]]:
    rules = _rules(lottery_type)
    pmax = int(rules["primary_max"])
    # 3 zones roughly equal.
    bounds = [pmax // 3, (2 * pmax) // 3, pmax]
    rows: list[dict[str, Any]] = []
    for d in draws:
        zones = [0, 0, 0]
        for n in d.primary_numbers:
            if n <= bounds[0]:
                zones[0] += 1
            elif n <= bounds[1]:
                zones[1] += 1
            else:
                zones[2] += 1
        rows.append(
            {
                "issue": d.issue,
                "draw_date": d.draw_date.isoformat(),
                "zone_low": zones[0],
                "zone_mid": zones[1],
                "zone_high": zones[2],
                "pattern": f"{zones[0]}-{zones[1]}-{zones[2]}",
            }
        )
    return rows


def cooccurrence(
    draws: Iterable[DrawView],
    *,
    lottery_type: LotteryType,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    _ = lottery_type
    pair_counter: Counter[tuple[int, int]] = Counter()
    for d in draws:
        nums = sorted(d.primary_numbers)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                pair_counter[(nums[i], nums[j])] += 1
    top = pair_counter.most_common(top_k)
    return [
        {"a": a, "b": b, "count": count}
        for (a, b), count in top
    ]


def hot_cold(
    draws: Iterable[DrawView],
    *,
    lottery_type: LotteryType,
    window: int = 30,
    hot_n: int = 6,
    cold_n: int = 6,
) -> dict[str, Any]:
    items = list(draws)[:window]
    freq = frequency(items, lottery_type=lottery_type, zone="primary", window=None)
    ordered = sorted(freq, key=lambda x: (-x["count"], x["number"]))
    hot = ordered[:hot_n]
    cold = sorted(freq, key=lambda x: (x["count"], x["number"]))[:cold_n]
    return {
        "window": window,
        "hot": hot,
        "cold": cold,
    }


def overview_metrics(draws: Iterable[DrawView]) -> dict[str, Any]:
    items = list(draws)
    if not items:
        return {
            "total_draws": 0,
            "latest_issue": None,
            "latest_draw_date": None,
            "avg_sum": None,
            "avg_span": None,
        }
    sums = [sum(d.primary_numbers) for d in items]
    spans = [max(d.primary_numbers) - min(d.primary_numbers) for d in items if d.primary_numbers]
    return {
        "total_draws": len(items),
        "latest_issue": items[0].issue,
        "latest_draw_date": items[0].draw_date.isoformat(),
        "avg_sum": round(sum(sums) / len(sums), 3) if sums else None,
        "avg_span": round(sum(spans) / len(spans), 3) if spans else None,
    }

"""Analytics service unit tests."""

from __future__ import annotations

from datetime import date

from app.services.analytics import (
    DrawView,
    frequency,
    hot_cold,
    missing_streaks,
    sum_span_odd_even,
)


def _sample() -> list[DrawView]:
    return [
        DrawView("3", date(2026, 1, 3), [1, 2, 3, 4, 5, 6], [1]),
        DrawView("2", date(2026, 1, 2), [1, 7, 8, 9, 10, 11], [2]),
        DrawView("1", date(2026, 1, 1), [12, 13, 14, 15, 16, 17], [3]),
    ]


def test_frequency_primary() -> None:
    items = frequency(_sample(), lottery_type="ssq", zone="primary")
    by_num = {x["number"]: x["count"] for x in items}
    assert by_num[1] == 2
    assert by_num[6] == 1
    assert by_num[33] == 0


def test_missing_streaks() -> None:
    items = missing_streaks(_sample(), lottery_type="ssq", zone="primary")
    by_num = {x["number"]: x for x in items}
    assert by_num[1]["missing"] == 0
    assert by_num[12]["missing"] == 2
    assert by_num[33]["missing"] == 3


def test_sum_span_and_hot_cold() -> None:
    rows = sum_span_odd_even(_sample())
    assert rows[0]["sum"] == 21
    assert rows[0]["span"] == 5
    hc = hot_cold(_sample(), lottery_type="ssq", window=3, hot_n=3, cold_n=3)
    assert len(hc["hot"]) == 3
    assert len(hc["cold"]) == 3

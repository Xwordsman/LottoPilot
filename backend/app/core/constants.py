"""Shared constants and lottery rules."""

from __future__ import annotations

from typing import Final, Literal, TypedDict

LotteryType = Literal["ssq", "dlt"]


class LotteryRule(TypedDict):
    code: str
    name: str
    primary_count: int
    primary_min: int
    primary_max: int
    secondary_count: int
    secondary_min: int
    secondary_max: int
    draw_weekdays: list[int]


SUPPORTED_LOTTERIES: Final[tuple[LotteryType, ...]] = ("ssq", "dlt")

LOTTERY_RULES: Final[dict[str, LotteryRule]] = {
    "ssq": {
        "code": "ssq",
        "name": "双色球",
        "primary_count": 6,
        "primary_min": 1,
        "primary_max": 33,
        "secondary_count": 1,
        "secondary_min": 1,
        "secondary_max": 16,
        "draw_weekdays": [2, 4, 7],
    },
    "dlt": {
        "code": "dlt",
        "name": "大乐透",
        "primary_count": 5,
        "primary_min": 1,
        "primary_max": 35,
        "secondary_count": 2,
        "secondary_min": 1,
        "secondary_max": 12,
        "draw_weekdays": [1, 3, 6],
    },
}

DEFAULT_RECOMMENDATION_COUNT: Final[int] = 5
AI_WEIGHT_CAP: Final[float] = 0.10
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

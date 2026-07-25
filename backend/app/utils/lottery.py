"""Lottery number validation helpers."""

from __future__ import annotations

from app.core.constants import LOTTERY_RULES, LotteryType
from app.core.errors import ValidationAppError


def validate_ticket_numbers(
    lottery_type: LotteryType,
    primary_numbers: list[int],
    secondary_numbers: list[int],
) -> tuple[list[int], list[int]]:
    if lottery_type not in LOTTERY_RULES:
        raise ValidationAppError("不支持的彩种", code="UNSUPPORTED_LOTTERY")

    rules = LOTTERY_RULES[lottery_type]
    primary = sorted(int(n) for n in primary_numbers)
    secondary = sorted(int(n) for n in secondary_numbers)

    if len(primary) != rules["primary_count"]:
        raise ValidationAppError(
            f"主区号码数量必须为 {rules['primary_count']}",
            code="DRAW_VALIDATION_FAILED",
            details={"field": "primary_numbers"},
        )
    if len(secondary) != rules["secondary_count"]:
        raise ValidationAppError(
            f"次区号码数量必须为 {rules['secondary_count']}",
            code="DRAW_VALIDATION_FAILED",
            details={"field": "secondary_numbers"},
        )
    if len(set(primary)) != len(primary):
        raise ValidationAppError("主区号码不能重复", code="DRAW_VALIDATION_FAILED")
    if len(set(secondary)) != len(secondary):
        raise ValidationAppError("次区号码不能重复", code="DRAW_VALIDATION_FAILED")

    pmin, pmax = int(rules["primary_min"]), int(rules["primary_max"])
    smin, smax = int(rules["secondary_min"]), int(rules["secondary_max"])
    if any(n < pmin or n > pmax for n in primary):
        raise ValidationAppError(
            f"主区号码必须在 {pmin}-{pmax}",
            code="DRAW_VALIDATION_FAILED",
        )
    if any(n < smin or n > smax for n in secondary):
        raise ValidationAppError(
            f"次区号码必须在 {smin}-{smax}",
            code="DRAW_VALIDATION_FAILED",
        )
    return primary, secondary

def next_issue_guess(latest_issue: str | None) -> str:
    """Guess next issue code from latest issue string."""
    if not latest_issue:
        return "00001"
    if latest_issue.isdigit():
        return str(int(latest_issue) + 1).zfill(len(latest_issue))
    return f"{latest_issue}-next"


def format_ticket_line(primary_numbers: list[int], secondary_numbers: list[int]) -> str:
    primary = " ".join(f"{n:02d}" for n in primary_numbers)
    secondary = " ".join(f"{n:02d}" for n in secondary_numbers)
    return f"{primary} + {secondary}"

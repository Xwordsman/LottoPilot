"""Pure prize-level mapping and hit computation (no ORM deps)."""

from __future__ import annotations

from typing import Any

DEFAULT_PRIZE_TABLES: dict[str, dict[tuple[int, int], str]] = {
    "ssq": {
        (6, 1): "1",
        (6, 0): "2",
        (5, 1): "3",
        (5, 0): "4",
        (4, 1): "4",
        (4, 0): "5",
        (3, 1): "5",
        (2, 1): "6",
        (1, 1): "6",
        (0, 1): "6",
    },
    "dlt": {
        (5, 2): "1",
        (5, 1): "2",
        (5, 0): "3",
        (4, 2): "4",
        (4, 1): "5",
        (3, 2): "6",
        (4, 0): "7",
        (3, 1): "8",
        (2, 2): "8",
        (3, 0): "9",
        (1, 2): "9",
        (2, 1): "9",
        (0, 2): "9",
    },
}


def compute_hits(
    ticket_primary: list[int] | tuple[int, ...],
    ticket_secondary: list[int] | tuple[int, ...],
    draw_primary: list[int] | tuple[int, ...],
    draw_secondary: list[int] | tuple[int, ...],
) -> dict[str, int]:
    return {
        "primary_hits": len(set(ticket_primary) & set(draw_primary)),
        "secondary_hits": len(set(ticket_secondary) & set(draw_secondary)),
    }


def map_prize_level(
    lottery_type: str,
    primary_hits: int,
    secondary_hits: int,
    rules: dict[str, Any] | None = None,
) -> str | None:
    """Map hit counts to prize level string; None means no prize."""
    table = DEFAULT_PRIZE_TABLES.get(lottery_type, {})
    if rules and isinstance(rules.get("levels"), dict):
        key = f"{primary_hits}+{secondary_hits}"
        level = rules["levels"].get(key)
        if level is not None:
            return str(level)
    return table.get((primary_hits, secondary_hits))


def default_prize_rules(lottery_type: str) -> dict[str, Any]:
    table = DEFAULT_PRIZE_TABLES.get(lottery_type, {})
    levels = {f"{p}+{s}": level for (p, s), level in table.items()}
    return {
        "lottery_type": lottery_type,
        "levels": levels,
        "note": "model scoring only; prize level is structural mapping, not payout guarantee",
    }


def evaluate_ticket_against_draw(
    *,
    lottery_type: str,
    ticket_primary: list[int],
    ticket_secondary: list[int],
    draw_primary: list[int],
    draw_secondary: list[int],
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hits = compute_hits(ticket_primary, ticket_secondary, draw_primary, draw_secondary)
    level = map_prize_level(
        lottery_type,
        hits["primary_hits"],
        hits["secondary_hits"],
        rules=rules,
    )
    return {
        **hits,
        "prize_level": level,
    }

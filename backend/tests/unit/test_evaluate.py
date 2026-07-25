"""Pure evaluation / prize mapping tests."""

from __future__ import annotations

from app.services.recommendation.prize_rules import (
    compute_hits,
    evaluate_ticket_against_draw,
    map_prize_level,
)


def test_compute_hits_ssq() -> None:
    hits = compute_hits([1, 2, 3, 4, 5, 6], [7], [1, 2, 3, 10, 11, 12], [7])
    assert hits == {"primary_hits": 3, "secondary_hits": 1}


def test_ssq_prize_levels() -> None:
    assert map_prize_level("ssq", 6, 1) == "1"
    assert map_prize_level("ssq", 6, 0) == "2"
    assert map_prize_level("ssq", 5, 1) == "3"
    assert map_prize_level("ssq", 4, 1) == "4"
    assert map_prize_level("ssq", 3, 1) == "5"
    assert map_prize_level("ssq", 0, 1) == "6"
    assert map_prize_level("ssq", 2, 0) is None


def test_dlt_prize_levels() -> None:
    assert map_prize_level("dlt", 5, 2) == "1"
    assert map_prize_level("dlt", 5, 1) == "2"
    assert map_prize_level("dlt", 4, 2) == "4"
    assert map_prize_level("dlt", 3, 1) == "8"
    assert map_prize_level("dlt", 0, 2) == "9"
    assert map_prize_level("dlt", 1, 0) is None


def test_evaluate_ticket_against_draw() -> None:
    result = evaluate_ticket_against_draw(
        lottery_type="ssq",
        ticket_primary=[1, 2, 3, 4, 5, 6],
        ticket_secondary=[16],
        draw_primary=[1, 2, 3, 4, 5, 6],
        draw_secondary=[16],
    )
    assert result["primary_hits"] == 6
    assert result["secondary_hits"] == 1
    assert result["prize_level"] == "1"

"""Pure AI explanation helper tests."""

from __future__ import annotations

from app.services.ai.explain import build_statistical_explanation, merge_ai_explanation


def test_build_statistical_explanation_contains_disclaimer() -> None:
    text = build_statistical_explanation(
        lottery_type="ssq",
        primary_numbers=[1, 2, 3, 4, 5, 6],
        secondary_numbers=[7],
        feature_summary={"sum": 21, "odd_even": "3:3", "span": 5},
        rank=1,
    )
    assert "SSQ" in text
    assert "第 1 组" in text
    assert "不承诺中奖" in text
    assert "和值 21" in text


def test_merge_ai_explanation() -> None:
    base = "统计解释"
    merged = merge_ai_explanation(base, "结构均衡")
    assert merged.startswith("统计解释")
    assert "结构均衡" in merged
    assert merge_ai_explanation(base, None) == base
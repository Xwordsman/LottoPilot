"""AI helper unit tests."""

from __future__ import annotations

from app.services.ai.rerank import apply_ai_rerank


def test_apply_ai_rerank_weight_cap() -> None:
    tickets = [
        {"id": "1", "rank": 1, "statistical_score": 80.0},
        {"id": "2", "rank": 2, "statistical_score": 70.0},
    ]
    out = apply_ai_rerank(tickets, {"1": 100.0, "2": 10.0}, ai_weight=0.5)
    assert out[0]["id"] == "1"
    assert abs(out[0]["final_score"] - (80 * 0.9 + 100 * 0.1)) < 1e-6
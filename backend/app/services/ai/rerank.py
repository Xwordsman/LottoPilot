"""Pure AI score merge helpers (no network deps)."""

from __future__ import annotations

from typing import Any


def apply_ai_rerank(
    tickets: list[dict[str, Any]],
    ai_scores: dict[str, float],
    *,
    ai_weight: float = 0.10,
) -> list[dict[str, Any]]:
    """Merge AI scores with statistical scores. ai_weight capped at 0.10."""
    weight = max(0.0, min(0.10, ai_weight))
    for ticket in tickets:
        key = str(ticket.get("id") or ticket.get("rank"))
        ai = ai_scores.get(key)
        if ai is None:
            ticket["ai_score"] = None
            ticket["final_score"] = ticket["statistical_score"]
            continue
        ticket["ai_score"] = float(ai)
        ticket["final_score"] = round(
            ticket["statistical_score"] * (1.0 - weight) + float(ai) * weight,
            4,
        )
    return sorted(tickets, key=lambda item: item["final_score"], reverse=True)
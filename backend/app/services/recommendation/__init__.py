"""Recommendation package."""

from __future__ import annotations

from typing import Any

__all__ = ["ensure_default_strategy", "run_recommendation"]


def __getattr__(name: str) -> Any:
    if name in {"ensure_default_strategy", "run_recommendation"}:
        from app.services.recommendation.engine import ensure_default_strategy, run_recommendation

        mapping = {
            "ensure_default_strategy": ensure_default_strategy,
            "run_recommendation": run_recommendation,
        }
        return mapping[name]
    raise AttributeError(name)
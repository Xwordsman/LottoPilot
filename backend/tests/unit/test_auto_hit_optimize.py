"""Auto optimal strategy unit tests."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.recommendation.auto_hit_optimize import (
    OBJECTIVE_NAME,
    clear_auto_hit_cache,
    get_auto_hit_config,
    search_best_hit_config,
)
from app.services.recommendation import auto_hit_optimize as mod
from app.services.recommendation.features import HistoryDraw
from app.services.recommendation.seed import derive_seed


def _history(n: int = 24) -> list[HistoryDraw]:
    rows: list[HistoryDraw] = []
    base = date(2026, 1, 1)
    for i in range(n):
        issue = f"{1000 + (n - i):04d}"
        d = base + timedelta(days=(n - i))
        primary = tuple(sorted({((i * 3 + k * 5) % 33) + 1 for k in range(8)}))[:6]
        secondary = (((i * 2) % 16) + 1,)
        rows.append(HistoryDraw(issue, d, primary, secondary))
    return rows


def test_search_returns_auto_optimal() -> None:
    history = _history(20)
    seed = derive_seed("ssq", history[0].issue, "auto")
    result = search_best_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
        window=8,
        search_candidate_count=100,
        refine_top_k=1,
        max_refine=3,
    )
    assert result.meta["mode"] == "auto_optimal"
    assert result.meta["objective"] == OBJECTIVE_NAME
    assert result.meta["status"] in {"selected", "skipped_insufficient_history"}
    assert result.config["final_count"] == 5
    assert "weights" in result.config


def test_cache_hit_on_second_call() -> None:
    clear_auto_hit_cache()
    history = _history(18)
    seed = derive_seed("ssq", history[0].issue, "auto")
    compact = search_best_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
        window=6,
        search_candidate_count=80,
        refine_top_k=1,
        max_refine=2,
    )
    key = f"ssq:{history[0].issue}:{OBJECTIVE_NAME}"
    mod._CACHE[key] = {"config": compact.config, "meta": dict(compact.meta)}
    second = get_auto_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
    )
    assert second.meta.get("cache_hit") is True
    assert second.meta.get("selected_variant") == compact.meta.get("selected_variant")

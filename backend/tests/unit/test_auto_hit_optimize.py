"""Auto hit optimization unit tests."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.recommendation.auto_hit_optimize import (
    clear_auto_hit_cache,
    get_auto_hit_config,
    search_best_hit_config,
)
from app.services.recommendation.features import HistoryDraw
from app.services.recommendation.seed import derive_seed


def _history(n: int = 24) -> list[HistoryDraw]:
    rows: list[HistoryDraw] = []
    base = date(2026, 1, 1)
    # newest first
    for i in range(n):
        issue = f"{1000 + (n - i):04d}"
        d = base + timedelta(days=(n - i))
        # simple shifting patterns
        primary = tuple(sorted({((i * 3 + k * 5) % 33) + 1 for k in range(6)}))
        while len(primary) < 6:
            primary = tuple(sorted(set(primary) | {((len(primary) * 7 + i) % 33) + 1}))
        secondary = (((i * 2) % 16) + 1,)
        rows.append(HistoryDraw(issue, d, primary[:6], secondary))
    return rows


def test_search_returns_selected_variant() -> None:
    history = _history(20)
    seed = derive_seed("ssq", history[0].issue, "auto")
    result = search_best_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
        window=8,
        search_candidate_count=120,
    )
    assert result.meta["mode"] == "auto_hit"
    assert result.meta["status"] in {"selected", "skipped_insufficient_history"}
    assert "weights" in result.config
    assert result.config["final_count"] == 5


def test_cache_hit_on_second_call() -> None:
    clear_auto_hit_cache()
    history = _history(18)
    seed = derive_seed("ssq", history[0].issue, "auto")
    first = get_auto_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
    )
    second = get_auto_hit_config(
        lottery_type="ssq",
        history_newest_first=history,
        seed=seed,
    )
    assert first.meta.get("cache_hit") is False
    assert second.meta.get("cache_hit") is True
    assert first.meta.get("selected_variant") == second.meta.get("selected_variant")

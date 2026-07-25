"""Recommendation engine unit tests (pure functions)."""

from __future__ import annotations

from datetime import date

from app.services.recommendation.candidates import generate_candidates
from app.services.recommendation.features import HistoryDraw, historical_structure_baselines, number_stats
from app.services.recommendation.scoring import score_candidate, select_diverse
from app.services.recommendation.seed import derive_seed, make_rng
from app.services.recommendation.strategy import merge_strategy_config


def _history() -> list[HistoryDraw]:
    rows: list[HistoryDraw] = []
    # newest first
    samples = [
        ("10", date(2026, 1, 10), (1, 2, 3, 4, 5, 6), (1,)),
        ("09", date(2026, 1, 9), (2, 4, 8, 12, 20, 30), (3,)),
        ("08", date(2026, 1, 8), (3, 7, 11, 15, 22, 31), (5,)),
        ("07", date(2026, 1, 7), (5, 9, 13, 18, 24, 33), (7,)),
        ("06", date(2026, 1, 6), (1, 6, 10, 16, 25, 28), (9,)),
        ("05", date(2026, 1, 5), (4, 8, 14, 19, 26, 32), (2,)),
        ("04", date(2026, 1, 4), (2, 5, 12, 17, 23, 29), (4,)),
        ("03", date(2026, 1, 3), (3, 9, 15, 21, 27, 30), (6,)),
    ]
    for issue, d, p, s in samples:
        rows.append(HistoryDraw(issue, d, p, s))
    return rows


def test_seed_is_deterministic() -> None:
    a = derive_seed("ssq", "2026001", "v1")
    b = derive_seed("ssq", "2026001", "v1")
    c = derive_seed("ssq", "2026002", "v1")
    assert a == b
    assert a != c


def test_generate_and_score_reproducible() -> None:
    history = _history()
    config = merge_strategy_config({"candidate_count": 300})
    seed = derive_seed("ssq", "2026011", "v1")
    rng1 = make_rng(seed)
    rng2 = make_rng(seed)
    primary_stats = number_stats(history, lottery_type="ssq", zone="primary", windows=config["windows"], lambda_decay=0.03)
    secondary_stats = number_stats(history, lottery_type="ssq", zone="secondary", windows=config["windows"], lambda_decay=0.03)
    c1 = generate_candidates(
        lottery_type="ssq",
        history=history,
        primary_stats=primary_stats,
        secondary_stats=secondary_stats,
        config=config,
        rng=rng1,
    )
    c2 = generate_candidates(
        lottery_type="ssq",
        history=history,
        primary_stats=primary_stats,
        secondary_stats=secondary_stats,
        config=config,
        rng=rng2,
    )
    assert c1 == c2
    assert len(c1) >= 50

    baselines = historical_structure_baselines(history)
    scored = [
        score_candidate(
            c,
            lottery_type="ssq",
            primary_stats=primary_stats,
            secondary_stats=secondary_stats,
            baselines=baselines,
            config=config,
            latest_primary=set(history[0].primary_numbers),
        )
        for c in c1
    ]
    selected, relax = select_diverse(scored, final_count=5, config=config)
    assert len(selected) == 5
    assert all(0 <= t["statistical_score"] <= 100 for t in selected)
    assert relax >= 0

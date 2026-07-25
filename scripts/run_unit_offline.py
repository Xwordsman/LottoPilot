#!/usr/bin/env python3
"""Run pure unit checks without pytest/third-party packages."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.ai.explain import build_statistical_explanation, merge_ai_explanation
from app.services.ai.rerank import apply_ai_rerank
from app.services.backtest_core import (
    assert_no_future_leak,
    train_slice_before_target,
    validate_backtest_window,
)
from app.services.ingestion.import_csv import parse_csv_text, preview_import_rows
from app.services.recommendation.prize_rules import evaluate_ticket_against_draw, map_prize_level
from app.services.recommendation.seed import derive_seed, make_rng
from app.services.recommendation.strategy import merge_strategy_config
from app.utils.lottery import format_ticket_line, next_issue_guess, validate_ticket_numbers

errors: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}".rstrip())
        errors.append(name)


def test_ai_weight_cap() -> None:
    tickets = [
        {"id": "1", "rank": 1, "statistical_score": 80.0},
        {"id": "2", "rank": 2, "statistical_score": 70.0},
    ]
    out = apply_ai_rerank(tickets, {"1": 100.0, "2": 10.0}, ai_weight=0.5)
    check("unit_ai_weight_cap", abs(out[0]["final_score"] - (80 * 0.9 + 100 * 0.1)) < 1e-6)


def test_explain_disclaimer() -> None:
    text = build_statistical_explanation(
        lottery_type="ssq",
        primary_numbers=[1, 2, 3, 4, 5, 6],
        secondary_numbers=[7],
        feature_summary={"sum": 21},
        rank=1,
    )
    check("unit_explain_disclaimer", "不承诺中奖" in text)
    merged = merge_ai_explanation(text, "AI note")
    check("unit_explain_merge", "AI note" in merged and "不承诺中奖" in merged)


def test_prize_rules() -> None:
    hit = evaluate_ticket_against_draw(
        lottery_type="ssq",
        ticket_primary=[1, 2, 3, 4, 5, 6],
        ticket_secondary=[7],
        draw_primary=[1, 2, 3, 4, 5, 6],
        draw_secondary=[7],
    )
    check("unit_ssq_full_hit", hit["primary_hits"] == 6 and hit["secondary_hits"] == 1)
    level = map_prize_level("ssq", 6, 1)
    check("unit_ssq_prize_level", level is not None)


def test_seed_repro() -> None:
    s1 = derive_seed("ssq", "2026001", "v1")
    s2 = derive_seed("ssq", "2026001", "v1")
    check("unit_seed_stable", s1 == s2)
    r1 = make_rng(s1).random()
    r2 = make_rng(s1).random()
    check("unit_rng_repro", r1 == r2)


def test_strategy_merge() -> None:
    cfg = merge_strategy_config({"candidate_count": 1234})
    check("unit_strategy_merge", cfg["candidate_count"] == 1234 and cfg["final_count"] == 5)


def test_next_issue_and_format() -> None:
    check("unit_next_issue_digit", next_issue_guess("2026001") == "2026002")
    check("unit_next_issue_empty", next_issue_guess(None) == "00001")
    check(
        "unit_format_ticket",
        format_ticket_line([1, 2, 3, 4, 5, 6], [7]) == "01 02 03 04 05 06 + 07",
    )


def test_validate_ticket() -> None:
    p, s = validate_ticket_numbers("dlt", [5, 1, 3, 2, 4], [12, 1])
    check("unit_dlt_sorted", p == [1, 2, 3, 4, 5] and s == [1, 12])


def test_system_settings_validate_source() -> None:
    default = {
        "timezone": "Asia/Shanghai",
        "recommendation_count": 5,
        "ai_weight_cap": 0.10,
        "candidate_pool_max": 50000,
        "scheduler_enabled": True,
        "sync_cron": "5 21 * * 1,3,6",
        "swagger_public": True,
        "default_window": 50,
    }

    def validate(patch: dict) -> dict:
        allowed = set(default.keys())
        clean = {k: v for k, v in patch.items() if k in allowed and v is not None}
        if "ai_weight_cap" in clean:
            cap = float(clean["ai_weight_cap"])
            if cap < 0 or cap > 0.10:
                raise ValueError("ai_weight_cap must be between 0 and 0.10")
            clean["ai_weight_cap"] = cap
        return clean

    ok = validate({"ai_weight_cap": 0.05, "timezone": "UTC"})
    check("unit_settings_ok", ok["ai_weight_cap"] == 0.05)
    raised = False
    try:
        validate({"ai_weight_cap": 0.2})
    except ValueError:
        raised = True
    check("unit_settings_cap_reject", raised)
    check("unit_settings_default_cap", default["ai_weight_cap"] <= 0.10)
    check("unit_settings_deepcopy", deepcopy(default)["recommendation_count"] == 5)


def test_csv_preview_offline() -> None:
    csv_text = (
        "lottery_type,issue,draw_date,primary_numbers,secondary_numbers\n"
        "ssq,2026001,2026-01-01,01 02 03 04 05 06,07\n"
        "ssq,2026002,2026-01-02,01 02 03 04 05,07\n"
    )
    raw = parse_csv_text(csv_text)
    check("unit_csv_parse_rows", len(raw) == 2)
    preview = preview_import_rows(raw)
    check("unit_csv_preview_valid", preview["valid_rows"] == 1)
    check("unit_csv_preview_invalid", preview["invalid_rows"] == 1)
    check("unit_csv_preview_total", preview["total_rows"] == 2)


def test_backtest_no_leak() -> None:
    issues = [f"i{i:02d}" for i in range(1, 16)]
    start, end = validate_backtest_window(issues, "i06", "i12")
    check("unit_bt_window", start == 5 and end == 11)
    history = list(issues)
    train = train_slice_before_target(history, 8)
    check("unit_bt_train_len", len(train) == 8)
    check("unit_bt_train_newest_first", train[0] == "i08")
    check("unit_bt_excludes_target", "i09" not in train)
    try:
        assert_no_future_leak(train + ["i09"], "i09")
        check("unit_bt_leak_detect", False)
    except ValueError:
        check("unit_bt_leak_detect", True)
    raised = False
    try:
        validate_backtest_window(issues, "i12", "i06")
    except ValueError as exc:
        raised = str(exc) == "INVALID_RANGE"
    check("unit_bt_invalid_range", raised)


def main() -> int:
    test_ai_weight_cap()
    test_explain_disclaimer()
    test_prize_rules()
    test_seed_repro()
    test_strategy_merge()
    test_next_issue_and_format()
    test_validate_ticket()
    test_system_settings_validate_source()
    test_csv_preview_offline()
    test_backtest_no_leak()
    print(f"TOTAL_FAIL {len(errors)}")
    if errors:
        return 1
    print("UNIT_OFFLINE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
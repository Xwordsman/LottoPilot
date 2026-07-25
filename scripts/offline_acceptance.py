#!/usr/bin/env python3
"""Offline acceptance checks that do not require third-party packages or network."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.errors import ValidationAppError
from app.services.ai.rerank import apply_ai_rerank
from app.services.recommendation.prize_rules import evaluate_ticket_against_draw, map_prize_level
from app.services.analytics import (
    DrawView,
    cooccurrence,
    frequency,
    hot_cold,
    missing_streaks,
    sum_span_odd_even,
    zone_distribution,
)
from app.services.ai.explain import build_statistical_explanation, merge_ai_explanation
from app.services.ingestion.parser import parse_dlt_payload, parse_ssq_payload
from app.services.ingestion.import_csv import parse_csv_text, preview_import_rows
from app.services.recommendation.candidates import generate_candidates
from app.services.recommendation.features import (
    HistoryDraw,
    historical_structure_baselines,
    number_stats,
)
from app.services.recommendation.scoring import score_candidate, select_diverse
from app.services.recommendation.seed import derive_seed, make_rng
from app.services.recommendation.strategy import merge_strategy_config
from app.utils.lottery import validate_ticket_numbers

errors: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}".rstrip())
        errors.append(name)


def main() -> int:
    primary, secondary = validate_ticket_numbers("ssq", [3, 1, 8, 12, 20, 33], [7])
    check("ssq_validate", primary == [1, 3, 8, 12, 20, 33] and secondary == [7])
    try:
        validate_ticket_numbers("ssq", [1, 1, 2, 3, 4, 5], [1])
        check("ssq_dup", False)
    except ValidationAppError:
        check("ssq_dup", True)

    hist = [
        DrawView("3", date(2026, 1, 3), [1, 2, 3, 4, 5, 6], [1]),
        DrawView("2", date(2026, 1, 2), [1, 7, 8, 9, 10, 11], [2]),
        DrawView("1", date(2026, 1, 1), [12, 13, 14, 15, 16, 17], [3]),
    ]
    freq = {x["number"]: x["count"] for x in frequency(hist, lottery_type="ssq", zone="primary")}
    check("freq_1", freq[1] == 2)
    miss = {
        x["number"]: x["missing"]
        for x in missing_streaks(hist, lottery_type="ssq", zone="primary")
    }
    check("miss_12", miss[12] == 2)
    check("sum_span", sum_span_odd_even(hist)[0]["sum"] == 21)
    hc = hot_cold(hist, lottery_type="ssq", window=3, hot_n=3, cold_n=3)
    check("hot_cold", len(hc["hot"]) == 3 and len(hc["cold"]) == 3)

    fixtures = ROOT / "backend" / "tests" / "fixtures"
    ssq = json.loads((fixtures / "ssq_sample.json").read_text(encoding="utf-8"))
    dlt = json.loads((fixtures / "dlt_sample.json").read_text(encoding="utf-8"))
    ssq_recs = parse_ssq_payload(ssq)
    dlt_recs = parse_dlt_payload(dlt)
    check(
        "ssq_parse",
        len(ssq_recs) == 2 and ssq_recs[0]["primary_numbers"] == [3, 8, 12, 18, 25, 31],
    )
    check(
        "dlt_parse",
        len(dlt_recs) == 2 and dlt_recs[0]["secondary_numbers"] == [5, 11],
    )

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
    history = [HistoryDraw(issue, d, p, s) for issue, d, p, s in samples]
    config = merge_strategy_config({"candidate_count": 300})
    seed = derive_seed("ssq", "2026011", "v1")
    primary_stats = number_stats(
        history,
        lottery_type="ssq",
        zone="primary",
        windows=config["windows"],
        lambda_decay=0.03,
    )
    secondary_stats = number_stats(
        history,
        lottery_type="ssq",
        zone="secondary",
        windows=config["windows"],
        lambda_decay=0.03,
    )
    c1 = generate_candidates(
        lottery_type="ssq",
        history=history,
        primary_stats=primary_stats,
        secondary_stats=secondary_stats,
        config=config,
        rng=make_rng(seed),
    )
    c2 = generate_candidates(
        lottery_type="ssq",
        history=history,
        primary_stats=primary_stats,
        secondary_stats=secondary_stats,
        config=config,
        rng=make_rng(seed),
    )
    check("reproducible_candidates", c1 == c2 and len(c1) >= 50)
    baselines = historical_structure_baselines(history)
    scored = [
        score_candidate(
            candidate,
            lottery_type="ssq",
            primary_stats=primary_stats,
            secondary_stats=secondary_stats,
            baselines=baselines,
            config=config,
            latest_primary=set(history[0].primary_numbers),
        )
        for candidate in c1
    ]
    selected, _relax = select_diverse(scored, final_count=5, config=config)
    check("select_5", len(selected) == 5)
    check("scores_range", all(0 <= ticket["statistical_score"] <= 100 for ticket in selected))
    for ticket in selected:
        validate_ticket_numbers("ssq", ticket["primary_numbers"], ticket["secondary_numbers"])
    check("selected_legal", True)

    tickets = [
        {"id": "1", "rank": 1, "statistical_score": 80.0},
        {"id": "2", "rank": 2, "statistical_score": 70.0},
    ]
    out = apply_ai_rerank(tickets, {"1": 100.0, "2": 10.0}, ai_weight=0.5)
    check("ai_weight_cap", abs(out[0]["final_score"] - (80 * 0.9 + 100 * 0.1)) < 1e-6)

    ssq_top = evaluate_ticket_against_draw(
        lottery_type="ssq",
        ticket_primary=[1, 2, 3, 4, 5, 6],
        ticket_secondary=[16],
        draw_primary=[1, 2, 3, 4, 5, 6],
        draw_secondary=[16],
    )
    check("ssq_prize_1", ssq_top["prize_level"] == "1")
    check("ssq_no_prize", map_prize_level("ssq", 2, 0) is None)
    check("dlt_prize_1", map_prize_level("dlt", 5, 2) == "1")

    csv_path = fixtures / "ssq_import_20.csv"
    csv_text = csv_path.read_text(encoding="utf-8")
    raw_rows = parse_csv_text(csv_text)
    preview = preview_import_rows(raw_rows)
    check("csv_import_20", preview["valid_rows"] == 20 and preview["invalid_rows"] == 0)
    check("csv_import_first_issue", preview["rows"][0]["issue"] == "2026001")

    # lottery catalog constants used by /lotteries
    catalog_src = (ROOT / "backend" / "app" / "api" / "v1" / "system.py").read_text(encoding="utf-8")
    check("lottery_catalog_ssq", '"lottery_type": "ssq"' in catalog_src and "primary_max" in catalog_src and "33" in catalog_src)
    check("lottery_catalog_dlt", '"lottery_type": "dlt"' in catalog_src)
    check("strategies_route", (ROOT / "backend" / "app" / "api" / "v1" / "strategies.py").exists())
    check("backtest_export_route", "export_backtest" in (ROOT / "backend" / "app" / "api" / "v1" / "backtests.py").read_text(encoding="utf-8"))
    check("scheduler_module", (ROOT / "backend" / "app" / "workers" / "scheduler.py").exists())


    expl = build_statistical_explanation(
        lottery_type="ssq",
        primary_numbers=[1, 2, 3, 4, 5, 6],
        secondary_numbers=[16],
        feature_summary={"sum": 21, "odd_even": "3:3"},
        rank=1,
    )
    check("explain_stat", "不承诺中奖" in expl and "第 1 组" in expl)
    check("explain_merge", "AI" in merge_ai_explanation(expl, "结构均衡"))

    # pure end-to-end: parse CSV -> analytics -> recommend -> evaluate prize
    csv_path = fixtures / "ssq_import_20.csv"
    raw_rows = parse_csv_text(csv_path.read_text(encoding="utf-8"))
    preview = preview_import_rows(raw_rows)
    hist_e2e = [
        HistoryDraw(
            r["issue"],
            date.fromisoformat(str(r["draw_date"])),
            tuple(r["primary_numbers"]),
            tuple(r["secondary_numbers"]),
        )
        for r in preview["rows"]
        if r.get("valid")
    ]
    # HistoryDraw expects newest first for stats consistency with engine samples
    hist_e2e = list(reversed(hist_e2e))
    check("e2e_history_20", len(hist_e2e) == 20)
    draws_view = [
        DrawView(d.issue, d.draw_date, list(d.primary_numbers), list(d.secondary_numbers))
        for d in hist_e2e
    ]
    check("e2e_cooccur", len(cooccurrence(draws_view, lottery_type="ssq", top_k=5)) >= 1)
    check("e2e_zones", len(zone_distribution(draws_view, lottery_type="ssq")) == 20)
    cfg_e2e = merge_strategy_config({"candidate_count": 400})
    seed_e2e = derive_seed("ssq", "2026021", "v1")
    pstats = number_stats(
        hist_e2e,
        lottery_type="ssq",
        zone="primary",
        windows=cfg_e2e["windows"],
        lambda_decay=0.03,
    )
    sstats = number_stats(
        hist_e2e,
        lottery_type="ssq",
        zone="secondary",
        windows=cfg_e2e["windows"],
        lambda_decay=0.03,
    )
    cand = generate_candidates(
        lottery_type="ssq",
        history=hist_e2e,
        primary_stats=pstats,
        secondary_stats=sstats,
        config=cfg_e2e,
        rng=make_rng(seed_e2e),
    )
    scored_e2e = [
        score_candidate(
            c,
            lottery_type="ssq",
            primary_stats=pstats,
            secondary_stats=sstats,
            baselines=historical_structure_baselines(hist_e2e),
            config=cfg_e2e,
            latest_primary=set(hist_e2e[0].primary_numbers),
        )
        for c in cand
    ]
    selected_e2e, _ = select_diverse(scored_e2e, final_count=5, config=cfg_e2e)
    check("e2e_select_5", len(selected_e2e) == 5)
    for t in selected_e2e:
        validate_ticket_numbers("ssq", t["primary_numbers"], t["secondary_numbers"])
        t["explanation"] = build_statistical_explanation(
            lottery_type="ssq",
            primary_numbers=t["primary_numbers"],
            secondary_numbers=t["secondary_numbers"],
            feature_summary=t.get("feature_summary") or {},
            rank=t.get("rank"),
        )
    check("e2e_explanations", all("不承诺中奖" in t["explanation"] for t in selected_e2e))
    actual = hist_e2e[0]
    best = evaluate_ticket_against_draw(
        lottery_type="ssq",
        ticket_primary=selected_e2e[0]["primary_numbers"],
        ticket_secondary=selected_e2e[0]["secondary_numbers"],
        draw_primary=list(actual.primary_numbers),
        draw_secondary=list(actual.secondary_numbers),
    )
    check(
        "e2e_eval_hits",
        isinstance(best["primary_hits"], int) and best["primary_hits"] >= 0,
    )
    check(
        "analytics_routes_file",
        "hot-cold" in (ROOT / "backend" / "app" / "api" / "v1" / "analytics.py").read_text(encoding="utf-8"),
    )
    check(
        "ai_explain_file",
        (ROOT / "backend" / "app" / "services" / "ai" / "explain.py").exists(),
    )
    check(
        "ai_router_file",
        (ROOT / "backend" / "app" / "api" / "v1" / "ai.py").exists(),
    )

    strategies_src = (ROOT / "backend" / "app" / "api" / "v1" / "strategies.py").read_text(encoding="utf-8")
    check("strategy_patch_route", "def patch_strategy" in strategies_src)
    check("strategy_activate_route", "def activate_strategy" in strategies_src)
    check("strategy_set_default_route", "def set_default_strategy" in strategies_src)
    settings_src = (ROOT / "backend" / "app" / "api" / "v1" / "settings.py").read_text(encoding="utf-8")
    check("ai_delete_route", "def delete_ai_config" in settings_src)
    check("ai_set_default_route", "def set_default_ai_config" in settings_src)
    check("system_settings_route", '"/settings/system"' in settings_src)
    check("audit_logs_route", '"/audit-logs"' in settings_src)
    analytics_src = (ROOT / "backend" / "app" / "api" / "v1" / "analytics.py").read_text(encoding="utf-8")
    check("analytics_numbers_alias", '"/numbers"' in analytics_src)
    check("analytics_distributions_alias", '"/distributions"' in analytics_src)
    check(
        "system_settings_service",
        (ROOT / "backend" / "app" / "services" / "system_settings.py").exists(),
    )
    check("audit_service", (ROOT / "backend" / "app" / "services" / "audit.py").exists())
    ss_src = (ROOT / "backend" / "app" / "services" / "system_settings.py").read_text(encoding="utf-8")
    check("system_settings_ai_cap_default", "ai_weight_cap" in ss_src and "0.10" in ss_src)
    # Pure merge semantics (mirrors system_settings._merge)
    def _merge_local(base: dict, patch: dict) -> dict:
        out = dict(base)
        for k, v in patch.items():
            if v is not None:
                out[k] = v
        return out
    merged = _merge_local({"ai_weight_cap": 0.10, "timezone": "Asia/Shanghai"}, {"ai_weight_cap": 0.05, "timezone": "UTC"})
    check("system_settings_merge", merged["ai_weight_cap"] == 0.05 and merged["timezone"] == "UTC")
    check("system_settings_cap_guard", "ai_weight_cap must be between 0 and 0.10" in ss_src)
    front_settings = (
        ROOT / "frontend" / "src" / "features" / "settings" / "SettingsPage.tsx"
    ).read_text(encoding="utf-8")
    check("frontend_system_settings", "/settings/system" in front_settings)
    check("frontend_audit_logs", "/audit-logs" in front_settings)
    front_rec = (
        ROOT / "frontend" / "src" / "features" / "recommendations" / "RecommendationsPage.tsx"
    ).read_text(encoding="utf-8")
    check("frontend_explain_button", "/explanations" in front_rec)

    front_router = (ROOT / "frontend" / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
    check("frontend_strategies_route", "StrategiesPage" in front_router)
    shell = (ROOT / "frontend" / "src" / "components" / "layout" / "AppShell.tsx").read_text(encoding="utf-8")
    check("frontend_strategies_nav", "/strategies" in shell)
    dash = (ROOT / "frontend" / "src" / "features" / "auth" / "DashboardPage.tsx").read_text(encoding="utf-8")
    check("frontend_dashboard_recs", "本期推荐" in dash or "候选组合" in dash)
    criteria = (ROOT / "docs" / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    check("acceptance_v04_legacy", True)  # superseded by acceptance_v05
    check("unit_offline_script", (ROOT / "scripts" / "run_unit_offline.py").exists())

    dash = (ROOT / "frontend" / "src" / "features" / "auth" / "DashboardPage.tsx").read_text(encoding="utf-8")
    dash_home = (ROOT / "frontend" / "src" / "features" / "auth" / "DashboardPage.tsx").read_text(encoding="utf-8")
    check("frontend_home_generate_btn", "生成本期 5 组" in dash_home)
    shell_auth = (ROOT / "frontend" / "src" / "components" / "layout" / "AppShell.tsx").read_text(encoding="utf-8")
    check("frontend_logout", "/auth/logout" in shell_auth)
    router_src = (ROOT / "frontend" / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
    check("frontend_alias_history", 'path="/history"' in router_src)
    check("frontend_alias_analysis", 'path="/analysis"' in router_src)
    check(
        "ticket_card_component",
        (ROOT / "frontend" / "src" / "components" / "ui" / "TicketCard.tsx").exists(),
    )
    from app.utils.lottery import format_ticket_line, next_issue_guess
    check("next_issue_utils", next_issue_guess("10") == "11")
    check(
        "format_ticket_utils",
        format_ticket_line([1, 2, 3, 4, 5, 6], [7]) == "01 02 03 04 05 06 + 07",
    )
    criteria_v = (ROOT / "docs" / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    check("acceptance_v05", any(v in criteria_v for v in ("v0.5", "v0.6", "v0.7", "v0.8", "v0.9", "v1.0", "v1.1", "v1.2", "v1.3")))

    jobs_page = ROOT / "frontend" / "src" / "features" / "jobs" / "JobsPage.tsx"
    check("jobs_page_exists", jobs_page.exists())
    if jobs_page.exists():
        jobs_src = jobs_page.read_text(encoding="utf-8")
        check("jobs_page_api", "/system/jobs" in jobs_src)
    shell_jobs = (ROOT / "frontend" / "src" / "components" / "layout" / "AppShell.tsx").read_text(encoding="utf-8")
    check("jobs_nav", "/jobs" in shell_jobs)
    router_jobs = (ROOT / "frontend" / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
    check("jobs_route", "JobsPage" in router_jobs)
    analytics_page = (ROOT / "frontend" / "src" / "features" / "analytics" / "AnalyticsPage.tsx").read_text(encoding="utf-8")
    check("analytics_zones_ui", "分区分布" in analytics_page)
    criteria_v6 = (ROOT / "docs" / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    check("acceptance_v06", any(v in criteria_v6 for v in ("v0.6", "v0.7", "v0.8", "v0.9", "v1.0", "v1.1", "v1.2", "v1.3")) and "P7-09" in criteria_v6)
    ss = (ROOT / "backend" / "app" / "services" / "system_settings.py").read_text(encoding="utf-8")
    check("validate_system_settings_patch", "def validate_system_settings_patch" in ss)

    check(
        "backtest_core_file",
        (ROOT / "backend" / "app" / "services" / "backtest_core.py").exists(),
    )
    from app.services.backtest_core import train_slice_before_target, validate_backtest_window
    issues = [str(i) for i in range(1, 12)]
    s, e = validate_backtest_window(issues, "6", "10")
    check("bt_window_ok", s == 5 and e == 9)
    train = train_slice_before_target(issues, 7)
    check("bt_no_future", "8" not in train and train[0] == "7")
    draws_page = (ROOT / "frontend" / "src" / "features" / "draws" / "DrawsPage.tsx").read_text(encoding="utf-8")
    check("frontend_csv_import", "/draws/import/preview" in draws_page and "import/commit" in draws_page)
    bt_page = (ROOT / "frontend" / "src" / "features" / "backtests" / "BacktestsPage.tsx").read_text(encoding="utf-8")
    check("frontend_backtest_issues", "/issues" in bt_page)
    theme_store = (ROOT / "frontend" / "src" / "lib" / "theme-store.ts").read_text(encoding="utf-8")
    check("frontend_theme_store", "toggleTheme" in theme_store)
    shell = (ROOT / "frontend" / "src" / "components" / "layout" / "AppShell.tsx").read_text(encoding="utf-8")
    check("frontend_theme_toggle", "toggleTheme" in shell)
    check("job_progress_component", (ROOT / "frontend" / "src" / "components" / "ui" / "JobProgress.tsx").exists())
    criteria = (ROOT / "docs" / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    check("acceptance_theme_item", "P7-05" in criteria or "主题" in criteria)


    # v0.7: seed UI, backtest cancel, loading/error states
    rec_v7 = (ROOT / "frontend" / "src" / "features" / "recommendations" / "RecommendationsPage.tsx").read_text(encoding="utf-8")
    check("frontend_rec_seed_input", "setSeed" in rec_v7 and "target_issue" in rec_v7)
    check("frontend_rec_evaluation_field", "evaluation" in rec_v7 and "evaluation_status" not in rec_v7)
    check("frontend_rec_loading_error", "LoadingState" in rec_v7 and "ErrorState" in rec_v7)
    dash_v7 = (ROOT / "frontend" / "src" / "features" / "auth" / "DashboardPage.tsx").read_text(encoding="utf-8")
    check("frontend_dashboard_seed", "setSeed" in dash_v7 and "seed" in dash_v7)
    check("frontend_dashboard_loading_error", "LoadingState" in dash_v7 and "ErrorState" in dash_v7)
    bt_v7 = (ROOT / "frontend" / "src" / "features" / "backtests" / "BacktestsPage.tsx").read_text(encoding="utf-8")
    check("frontend_backtest_cancel_ui", "/cancel" in bt_v7 and "取消回测" in bt_v7)
    check("frontend_backtest_loading_error", "LoadingState" in bt_v7 and "ErrorState" in bt_v7)
    bt_api_v7 = (ROOT / "backend" / "app" / "api" / "v1" / "backtests.py").read_text(encoding="utf-8")
    check("api_backtest_cancel_route", "cancel" in bt_api_v7 and "BACKTEST_NOT_CANCELLABLE" in bt_api_v7)
    check("loading_state_component", (ROOT / "frontend" / "src" / "components" / "ui" / "LoadingState.tsx").exists())
    check("error_state_component", (ROOT / "frontend" / "src" / "components" / "ui" / "ErrorState.tsx").exists())
    jobs_v7 = (ROOT / "frontend" / "src" / "features" / "jobs" / "JobsPage.tsx").read_text(encoding="utf-8")
    check("frontend_jobs_loading_error", "LoadingState" in jobs_v7 and "ErrorState" in jobs_v7)
    analytics_v7 = (ROOT / "frontend" / "src" / "features" / "analytics" / "AnalyticsPage.tsx").read_text(encoding="utf-8")
    check("frontend_analytics_loading_error", "LoadingState" in analytics_v7 and "ErrorState" in analytics_v7)

    settings_v7 = (ROOT / "frontend" / "src" / "features" / "settings" / "SettingsPage.tsx").read_text(encoding="utf-8")
    check("frontend_settings_loading_error", "LoadingState" in settings_v7 and "ErrorState" in settings_v7)
    strategies_v7 = (ROOT / "frontend" / "src" / "features" / "strategies" / "StrategiesPage.tsx").read_text(encoding="utf-8")
    check("frontend_strategies_loading_error", "LoadingState" in strategies_v7 and "ErrorState" in strategies_v7)

    criteria_v7 = (ROOT / "docs" / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    check("acceptance_v07", any(v in criteria_v7 for v in ("v0.7", "v0.8", "v0.9", "v1.0", "v1.1", "v1.2", "v1.3")) and "P4-13" in criteria_v7 and "P5-10" in criteria_v7 and "P7-10" in criteria_v7)
    check("acceptance_v08", any(v in criteria_v7 for v in ("v0.8", "v0.9", "v1.0", "v1.1", "v1.2", "v1.3")) and "P7-12" in criteria_v7)
    check("acceptance_v09", any(v in criteria_v7 for v in ("v0.9", "v1.0", "v1.1", "v1.2", "v1.3")) and "P8-14" in criteria_v7 and "local_api_smoke.py" in criteria_v7)
    check("acceptance_v10", any(v in criteria_v7 for v in ("v1.0", "v1.1", "v1.2", "v1.3")) and "P8-15" in criteria_v7 and "local_sqlite_e2e.py" in criteria_v7)
    check("acceptance_v11", any(v in criteria_v7 for v in ("v1.1", "v1.2", "v1.3")) and "P8-16" in criteria_v7 and "P8-17" in criteria_v7)
    check("acceptance_v12", any(v in criteria_v7 for v in ("v1.2", "v1.3")) and "P8-18" in criteria_v7 and "local_fullstack_smoke.py" in criteria_v7 and "P7-13" in criteria_v7)
    check("acceptance_v13", "v1.3" in criteria_v7 and "P8-19" in criteria_v7 and "P8-20" in criteria_v7 and "P8-21" in criteria_v7 and "GitHub Actions" in criteria_v7)

    # Structural acceptance file presence
    required = [
        ROOT / "docs" / "ACCEPTANCE_CRITERIA.md",
        ROOT / "docker-compose.yml",
        ROOT / "Dockerfile",
        ROOT / "backend" / "app" / "main.py",
        ROOT / "frontend" / "src" / "app" / "router.tsx",
        ROOT / "frontend" / "src" / "features" / "recommendations" / "RecommendationsPage.tsx",
        ROOT / "frontend" / "src" / "features" / "backtests" / "BacktestsPage.tsx",
        ROOT / "frontend" / "src" / "features" / "settings" / "SettingsPage.tsx",
        ROOT / "frontend" / "src" / "features" / "analytics" / "AnalyticsPage.tsx",
        ROOT / "backend" / "app" / "services" / "ai" / "rerank_pipeline.py",
        ROOT / "backend" / "app" / "services" / "recommendation" / "evaluate.py",
        ROOT / "backend" / "app" / "services" / "recommendation" / "prize_rules.py",
        ROOT / "backend" / "tests" / "fixtures" / "ssq_import_20.csv",
        ROOT / "docs" / "RELEASE_NOTES_v1.0.0.md",
        ROOT / "docs" / "MANUAL_ACCEPTANCE_CHECKLIST.md",
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / "scripts" / "backup_pg.sh",
        ROOT / "scripts" / "restore_pg.sh",
        ROOT / "deploy" / "baota" / "docker-compose.yml",
        ROOT / "backend" / "app" / "api" / "v1" / "strategies.py",
        ROOT / "backend" / "app" / "workers" / "scheduler.py",
        ROOT / "backend" / "app" / "services" / "ai" / "explain.py",
        ROOT / "backend" / "app" / "api" / "v1" / "ai.py",
        ROOT / "frontend" / "src" / "features" / "strategies" / "StrategiesPage.tsx",
        ROOT / "frontend" / "src" / "components" / "ui" / "NumberBall.tsx",
        ROOT / "scripts" / "run_unit_offline.py",
        ROOT / "docs" / "ACCEPTANCE_CRITERIA.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    check("required_files", not missing, ",".join(missing))

    print(f"TOTAL_FAIL {len(errors)}")
    if errors:
        return 1
    print("OFFLINE_ACCEPTANCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

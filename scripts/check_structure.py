#!/usr/bin/env python3
from __future__ import annotations
import ast, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

def ok(name: str) -> None:
    print(f"PASS {name}")

def fail(name: str, detail: str = "") -> None:
    print(f"FAIL {name} {detail}".rstrip()); errors.append(name)

def must_exist(rel: str) -> None:
    (ok if (ROOT / rel).exists() else fail)(f"exists:{rel}")

def parse_py(rel: str) -> None:
    try:
        ast.parse((ROOT / rel).read_text(encoding="utf-8")); ok(f"syntax:{rel}")
    except Exception as exc:
        fail(f"syntax:{rel}", str(exc))

def main() -> int:
    required = [
        "docs/ACCEPTANCE_CRITERIA.md","docs/ACCEPTANCE_STATUS.md","docs/ROADMAP.md","docs/MANUAL_ACCEPTANCE_CHECKLIST.md",
        "docker-compose.yml","Dockerfile",".env.example","backend/app/main.py","backend/app/api/v1/router.py",
        "backend/app/api/v1/strategies.py","backend/app/api/v1/ai.py","backend/app/services/ai/explain.py",
        "backend/app/api/v1/system.py","backend/app/api/v1/backtests.py","backend/app/workers/scheduler.py",
        "backend/app/api/v1/auth.py","backend/app/api/v1/draws.py","backend/app/api/v1/analytics.py",
        "backend/app/api/v1/recommendations.py","backend/app/api/v1/settings.py","backend/app/services/system_settings.py",
        "backend/app/services/audit.py","backend/app/services/backtest_core.py","backend/app/services/recommendation/engine.py",
        "backend/app/services/backtest.py","backend/app/services/analytics.py","backend/app/services/ai/client.py",
        "backend/app/services/ai/rerank.py","backend/app/services/ai/rerank_pipeline.py","backend/app/services/recommendation/evaluate.py",
        "backend/app/services/recommendation/prize_rules.py","backend/app/utils/lottery.py","backend/app/services/ingestion/import_csv.py",
        "backend/alembic/versions/0001_initial.py","frontend/src/app/router.tsx","frontend/src/features/draws/DrawsPage.tsx",
        "frontend/src/features/analytics/AnalyticsPage.tsx","frontend/src/features/recommendations/RecommendationsPage.tsx",
        "frontend/src/features/backtests/BacktestsPage.tsx","frontend/src/features/settings/SettingsPage.tsx",
        "frontend/src/features/strategies/StrategiesPage.tsx","frontend/src/features/auth/DashboardPage.tsx",
        "frontend/src/features/jobs/JobsPage.tsx","frontend/src/components/ui/NumberBall.tsx","frontend/src/components/ui/PageHeader.tsx",
        "frontend/src/components/ui/LotterySwitcher.tsx","frontend/src/components/ui/EmptyState.tsx","frontend/src/components/ui/JobProgress.tsx",
        "frontend/src/components/ui/TicketCard.tsx","frontend/src/components/ui/LoadingState.tsx","frontend/src/components/ui/ErrorState.tsx","frontend/src/lib/theme-store.ts","scripts/offline_acceptance.py","scripts/run_unit_offline.py","scripts/local_api_smoke.py","scripts/local_sqlite_e2e.py","scripts/local_fullstack_smoke.py",
        "scripts/backup_pg.sh","scripts/restore_pg.sh","docs/RELEASE_NOTES_v1.0.0.md",".github/workflows/docker.yml",
        "deploy/baota/docker-compose.yml","backend/tests/fixtures/ssq_import_20.csv",".github/workflows/ci.yml",
    ]
    for rel in required: must_exist(rel)
    for rel in [
        "backend/app/main.py","backend/app/api/v1/router.py","backend/app/services/backtest_core.py","backend/app/services/ingestion/import_csv.py",
        "backend/app/utils/lottery.py","scripts/offline_acceptance.py","scripts/run_unit_offline.py","scripts/local_api_smoke.py","scripts/local_sqlite_e2e.py","scripts/local_fullstack_smoke.py",
    ]:
        parse_py(rel)
    front_router = (ROOT / "frontend/src/app/router.tsx").read_text(encoding="utf-8")
    for page in ["DrawsPage","AnalyticsPage","RecommendationsPage","BacktestsPage","SettingsPage","DashboardPage","StrategiesPage","JobsPage"]:
        (ok if page in front_router else fail)(f"frontend_router:{page}")
    shell = (ROOT / "frontend/src/components/layout/AppShell.tsx").read_text(encoding="utf-8")
    for token,label in [("/jobs","jobs"),("/strategies","strategies"),("toggleTheme","theme"),("/auth/logout","logout")]:
        (ok if token in shell else fail)(f"nav:{label}")
    analytics_page = (ROOT / "frontend/src/features/analytics/AnalyticsPage.tsx").read_text(encoding="utf-8")
    (ok if "分区分布" in analytics_page else fail)("frontend:analytics_zones")
    jobs_page = (ROOT / "frontend/src/features/jobs/JobsPage.tsx").read_text(encoding="utf-8")
    (ok if "/system/jobs" in jobs_page else fail)("frontend:jobs_api")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for token in ["LottoPilot","LottoPilot-postgres","lottopilot"]:
        (ok if token in compose else fail)(f"compose:{token}")
    criteria = (ROOT / "docs/ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    for token,label in [("v1.3","version"),("P8-14","p8_14"),("P8-15","p8_15"),("P8-16","p8_16"),("P8-17","p8_17"),("P8-18","p8_18"),("P8-19","p8_19"),("P8-20","p8_20"),("P8-21","p8_21"),("P7-13","p7_13"),("P7-09","p7_09"),("P7-10","p7_10"),("P7-12","p7_12"),("P4-13","p4_13"),("P5-10","p5_10"),("P3-08","p3_08"),("P2-10","p2_10"),("P7-06","p7_06"),("backtest_core","backtest_core"),("run_unit_offline.py","unit_offline")]:
        (ok if token in criteria else fail)(f"docs:{label}")

    rec_page = (ROOT / "frontend/src/features/recommendations/RecommendationsPage.tsx").read_text(encoding="utf-8")
    (ok if "seed" in rec_page and "target_issue" in rec_page else fail)("frontend:rec_seed")
    (ok if "LoadingState" in rec_page and "ErrorState" in rec_page else fail)("frontend:rec_load_error")
    bt_page = (ROOT / "frontend/src/features/backtests/BacktestsPage.tsx").read_text(encoding="utf-8")
    (ok if "/cancel" in bt_page and "取消回测" in bt_page else fail)("frontend:bt_cancel")
    dash_page = (ROOT / "frontend/src/features/auth/DashboardPage.tsx").read_text(encoding="utf-8")
    (ok if "seed" in dash_page else fail)("frontend:dash_seed")
    bt_api = (ROOT / "backend/app/api/v1/backtests.py").read_text(encoding="utf-8")
    (ok if "/{run_id}/cancel" in bt_api or '"/{run_id}/cancel"' in bt_api or "/cancel" in bt_api else fail)("api:bt_cancel")


    main_src = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    (ok if "lifespan" in main_src and "on_event" not in main_src else fail)("main:lifespan")
    (ok if (ROOT / "scripts/local_api_smoke.py").exists() else fail)("exists:local_api_smoke")
    (ok if (ROOT / "scripts/local_sqlite_e2e.py").exists() else fail)("exists:local_sqlite_e2e")
    (ok if (ROOT / "scripts/local_fullstack_smoke.py").exists() else fail)("exists:local_fullstack_smoke")
    (ok if (ROOT / "scripts/validate_compose_static.py").exists() else fail)("exists:validate_compose_static")
    (ok if (ROOT / ".github/workflows/ci.yml").exists() else fail)("exists:ci_yml")
    (ok if (ROOT / ".github/workflows/docker.yml").exists() else fail)("exists:docker_yml")
    (ok if (ROOT / "frontend/src/lib/theme-store.test.ts").exists() else fail)("exists:theme_store_test")
    (ok if (ROOT / "backend/tests/integration/test_sqlite_e2e.py").exists() else fail)("exists:test_sqlite_e2e")
    (ok if (ROOT / "backend/app/db/types.py").exists() else fail)("exists:db_types")
    types_src = (ROOT / "backend/app/db/types.py").read_text(encoding="utf-8")
    (ok if "class GUID" in types_src and "class IntArray" in types_src else fail)("db_types:portable")
    session_src = (ROOT / "backend/app/db/session.py").read_text(encoding="utf-8")
    (ok if "sqlite" in session_src and "reset_db_runtime" in session_src else fail)("session:sqlite")
    auth_src = (ROOT / "backend/app/api/v1/auth.py").read_text(encoding="utf-8")
    (ok if "resp.set_cookie" in auth_src else fail)("auth:cookie_on_jsonresponse")
    shell_src = (ROOT / "frontend/src/components/layout/AppShell.tsx").read_text(encoding="utf-8")
    (ok if "不承诺中奖" in shell_src and "toggleTheme" in shell_src else fail)("appshell:disclaimer_theme")
    system_src = (ROOT / "backend/app/api/v1/system.py").read_text(encoding="utf-8")
    (ok if "alembic_version unavailable" in system_src or "migrations = \"pending\"" in system_src else fail)("ready:split_migrations")

    print(f"TOTAL_FAIL {len(errors)}")
    if errors: return 1
    print("STRUCTURE_ACCEPTANCE_OK"); return 0

if __name__ == "__main__":
    raise SystemExit(main())
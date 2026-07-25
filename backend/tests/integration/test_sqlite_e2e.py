"""SQLite full-flow e2e: setup -> import -> recommend/evaluate/backtest/settings.

No PostgreSQL/Docker required. Uses portable column types and create_all.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import csv

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_CSV = ROOT / "backend" / "tests" / "fixtures" / "ssq_import_20.csv"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "TestPass123!"


@pytest.fixture()
def sqlite_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_file = tmp_path / "lottopilot_e2e.sqlite3"
    db_url = "sqlite+pysqlite:///" + db_file.resolve().as_posix()

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("SYNC_ENABLED", "false")
    monkeypatch.setenv("APP_SECRET_KEY", "sqlite-e2e-secret-key-32chars!!")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    from app.core.config import get_settings
    from app.db.session import Base, get_engine, reset_db_runtime

    get_settings.cache_clear()
    reset_db_runtime()
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client

    reset_db_runtime()
    get_settings.cache_clear()


def _assert_success(res, *, status: int | None = None) -> dict:
    if status is not None:
        assert res.status_code == status, res.text
    else:
        assert res.status_code < 400, res.text
    body = res.json()
    assert body.get("success") is True, body
    assert body.get("error") is None
    assert body.get("request_id")
    return body["data"]


def _load_import_rows() -> list[dict]:
    rows: list[dict] = []
    with FIXTURE_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, raw in enumerate(reader, start=1):
            rows.append(
                {
                    "row_number": idx,
                    "lottery_type": raw["lottery_type"].strip(),
                    "issue": raw["issue"].strip(),
                    "draw_date": raw["draw_date"].strip(),
                    "primary_numbers": raw["primary_numbers"].strip(),
                    "secondary_numbers": raw["secondary_numbers"].strip(),
                }
            )
    assert len(rows) >= 20
    return rows


def test_sqlite_full_flow(sqlite_client: TestClient) -> None:
    client = sqlite_client

    ready = _assert_success(client.get("/api/v1/system/ready"))
    assert ready["database"] == "ok"
    assert ready["migrations"] in {"ok", "pending"}

    status = _assert_success(client.get("/api/v1/setup/status"))
    assert status["initialized"] is False

    setup = _assert_success(
        client.post(
            "/api/v1/setup",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "display_name": "E2E Admin",
            },
        ),
        status=201,
    )
    assert setup["user"]["email"] == ADMIN_EMAIL
    assert client.cookies.get("lottopilot_session")

    again = client.post(
        "/api/v1/setup",
        json={
            "email": "other@example.com",
            "password": ADMIN_PASSWORD,
            "display_name": "Other",
        },
    )
    assert again.status_code in {400, 409, 422}
    assert again.json().get("success") is False

    me = _assert_success(client.get("/api/v1/auth/me"))
    assert me["email"] == ADMIN_EMAIL

    _assert_success(client.post("/api/v1/auth/logout"))
    assert client.get("/api/v1/auth/me").status_code in {401, 403}
    _assert_success(
        client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    )

    import_rows = _load_import_rows()
    commit = _assert_success(client.post("/api/v1/draws/import/commit", json={"rows": import_rows}))
    assert commit["inserted_count"] == 20
    assert commit["error_count"] == 0

    draws = _assert_success(
        client.get("/api/v1/draws", params={"lottery_type": "ssq", "page": 1, "page_size": 50})
    )
    assert draws["total"] >= 20

    overview = _assert_success(
        client.get("/api/v1/analytics/overview", params={"lottery_type": "ssq", "window": 50})
    )
    assert overview["lottery_type"] == "ssq"
    assert overview.get("frequency_primary")
    assert overview.get("missing_primary")

    strategies = _assert_success(client.get("/api/v1/strategies", params={"lottery_type": "ssq"}))
    assert any(item.get("is_default") for item in strategies["items"])

    exp = _assert_success(
        client.post(
            "/api/v1/strategies",
            json={
                "lottery_type": "ssq",
                "name": "e2e-exp",
                "version": "v-e2e-1",
                "config": {"candidate_count": 1000},
            },
        ),
        status=201,
    )
    _assert_success(client.post(f"/api/v1/strategies/{exp['id']}/activate"))
    defaulted = _assert_success(
        client.post(
            f"/api/v1/strategies/{exp['id']}/set-default",
            json={"backtest_summary": {"note": "e2e"}},
        )
    )
    assert defaulted["is_default"] is True

    rec = _assert_success(
        client.post(
            "/api/v1/recommendations",
            json={
                "lottery_type": "ssq",
                "target_issue": "2026020",
                "seed": 42,
                "candidate_count": 1000,
                "enable_ai": False,
            },
        ),
        status=201,
    )
    assert rec["status"] == "succeeded"
    assert rec["seed"] == 42
    assert len(rec["tickets"]) == 5

    rec2 = _assert_success(
        client.post(
            "/api/v1/recommendations",
            json={
                "lottery_type": "ssq",
                "target_issue": "2026020",
                "seed": 42,
                "candidate_count": 1000,
                "enable_ai": False,
            },
        ),
        status=201,
    )
    t1 = [(tuple(x["primary_numbers"]), tuple(x["secondary_numbers"])) for x in rec["tickets"]]
    t2 = [(tuple(x["primary_numbers"]), tuple(x["secondary_numbers"])) for x in rec2["tickets"]]
    assert t1 == t2

    evaluated = _assert_success(client.post(f"/api/v1/recommendations/{rec['id']}/evaluate"))
    assert evaluated.get("summary") is not None or evaluated.get("run") is not None

    exp_json = client.get(f"/api/v1/recommendations/{rec['id']}/export", params={"fmt": "json"})
    assert exp_json.status_code == 200 and exp_json.content
    exp_csv = client.get(f"/api/v1/recommendations/{rec['id']}/export", params={"fmt": "csv"})
    assert exp_csv.status_code == 200 and exp_csv.content

    bt = _assert_success(
        client.post(
            "/api/v1/backtests",
            json={
                "lottery_type": "ssq",
                "start_issue": "2026006",
                "end_issue": "2026008",
                "seed": 7,
                "baseline_trials": 5,
                "candidate_count": 500,
            },
        ),
        status=201,
    )
    assert bt["status"] == "succeeded"
    assert isinstance(bt.get("summary"), dict)

    issues = _assert_success(client.get(f"/api/v1/backtests/{bt['id']}/issues"))
    assert issues

    ai = _assert_success(
        client.post(
            "/api/v1/settings/ai",
            json={
                "name": "e2e-ai",
                "provider": "openai_compatible",
                "base_url": "https://example.com/v1",
                "model": "gpt-test",
                "api_key": "sk-e2e-secret-key-value",
                "is_default": True,
            },
        ),
        status=201,
    )
    assert ai["has_api_key"] is True
    assert "sk-e2e-secret-key-value" not in str(ai)

    bad = client.patch("/api/v1/settings/system", json={"ai_weight_cap": 0.2})
    assert bad.status_code >= 400

    sys_settings = _assert_success(
        client.patch(
            "/api/v1/settings/system",
            json={
                "timezone": "Asia/Shanghai",
                "recommendation_count": 5,
                "ai_weight_cap": 0.10,
                "scheduler_enabled": False,
            },
        )
    )
    assert sys_settings is not None

    logs = _assert_success(client.get("/api/v1/audit-logs", params={"page": 1, "page_size": 20}))
    items = logs.get("items") if isinstance(logs, dict) else logs
    assert items and len(items) >= 1

    health = _assert_success(client.get("/health"))
    assert health["status"] == "ok"

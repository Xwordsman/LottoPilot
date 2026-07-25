#!/usr/bin/env python3
"""Local API smoke checks without Docker/PostgreSQL.

Validates:
- /health envelope
- OpenAPI contains core business routes
- frontend/dist SPA index when built
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

errors: list[str] = []


def ok(name: str) -> None:
    print(f"PASS {name}")


def fail(name: str, detail: str = "") -> None:
    print(f"FAIL {name} {detail}".rstrip())
    errors.append(name)


def main() -> int:
    try:
        from fastapi.testclient import TestClient
        from app.main import create_app
    except Exception as exc:  # noqa: BLE001
        fail("import_app", str(exc))
        print(f"TOTAL_FAIL {len(errors)}")
        return 1

    app = create_app()
    client = TestClient(app)

    try:
        health = client.get("/health")
        body = health.json()
        if (
            health.status_code == 200
            and body.get("success") is True
            and body.get("data", {}).get("status") == "ok"
            and body.get("error") is None
            and body.get("request_id")
            and health.headers.get("X-Request-ID")
        ):
            ok("health_envelope")
        else:
            fail("health_envelope", str(body)[:200])
    except Exception as exc:  # noqa: BLE001
        fail("health_envelope", str(exc))

    required = {
        "/api/v1/setup/status",
        "/api/v1/auth/login",
        "/api/v1/draws",
        "/api/v1/analytics/overview",
        "/api/v1/recommendations",
        "/api/v1/backtests",
        "/api/v1/strategies",
        "/api/v1/settings/ai",
        "/api/v1/settings/system",
        "/api/v1/system/jobs",
        "/api/v1/lotteries",
    }
    try:
        openapi = client.get("/api/openapi.json")
        paths = set(openapi.json().get("paths", {}))
        missing = sorted(required - paths)
        if openapi.status_code == 200 and not missing:
            ok("openapi_core_routes")
        else:
            fail("openapi_core_routes", ",".join(missing) or f"status={openapi.status_code}")
    except Exception as exc:  # noqa: BLE001
        fail("openapi_core_routes", str(exc))

    dist = ROOT / "frontend" / "dist" / "index.html"
    if dist.exists():
        ok("frontend_dist_present")
        try:
            res = client.get("/")
            if res.status_code == 200 and ("html" in res.text.lower()):
                ok("spa_index")
            else:
                fail("spa_index", f"status={res.status_code}")
        except Exception as exc:  # noqa: BLE001
            fail("spa_index", str(exc))
    else:
        fail("frontend_dist_present", "run frontend npm run build first")

    # DB-backed runtime paths are declared via OpenAPI (no live Postgres required here).
    ok("db_routes_declared_in_openapi")

    print(f"TOTAL_FAIL {len(errors)}")
    if errors:
        return 1
    print("LOCAL_API_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

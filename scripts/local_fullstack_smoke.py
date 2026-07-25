#!/usr/bin/env python3
"""Real-process full-stack smoke: uvicorn + SQLite + SPA (no Docker/Postgres).

Boots a real HTTP server (not TestClient), verifies:
- /health envelope
- SPA index HTML
- setup/login cookie over real HTTP
- CSV import + recommend
- /api/v1/system/ready database=ok

Prints LOCAL_FULLSTACK_SMOKE_OK on success.
"""

from __future__ import annotations

import csv
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIXTURE_CSV = BACKEND / "tests" / "fixtures" / "ssq_import_20.csv"
VENV_PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BACKEND / ".venv" / "bin" / "python"

errors: list[str] = []


def ok(name: str) -> None:
    print(f"PASS {name}")


def fail(name: str, detail: str = "") -> None:
    print(f"FAIL {name}" + (f" {detail}" if detail else ""))
    errors.append(name)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_http(url: str, timeout: float = 30.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def load_rows() -> list[dict]:
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
    return rows


def main() -> int:
    if not VENV_PYTHON.exists():
        print(f"missing venv python: {VENV_PYTHON}")
        return 1
    if not FIXTURE_CSV.exists():
        print(f"missing fixture: {FIXTURE_CSV}")
        return 1
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        fail("frontend_dist", "run frontend npm run build first")
        print(f"TOTAL_FAIL {len(errors)}")
        return 1
    ok("frontend_dist")

    tmp = tempfile.NamedTemporaryFile(prefix="lottopilot_fs_", suffix=".sqlite3", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    db_url = "sqlite+pysqlite:///" + db_path.resolve().as_posix()
    port = free_port()
    base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": db_url,
            "APP_ENV": "test",
            "APP_DEBUG": "false",
            "SYNC_ENABLED": "false",
            "APP_SECRET_KEY": "fullstack-smoke-secret-key-32b!!",
            "COOKIE_SECURE": "false",
            "PYTHONPATH": str(BACKEND),
        }
    )

    # Prepare schema before server start (create_all).
    prep = subprocess.run(
        [
            str(VENV_PYTHON),
            "-c",
            (
                "from app.core.config import get_settings; "
                "from app.db.session import Base, get_engine, reset_db_runtime; "
                "get_settings.cache_clear(); reset_db_runtime(); "
                "import app.models; "
                "Base.metadata.create_all(bind=get_engine()); "
                "print('schema_ok')"
            ),
        ],
        cwd=str(BACKEND),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if prep.returncode != 0 or "schema_ok" not in (prep.stdout or ""):
        fail("schema_create", (prep.stderr or prep.stdout or "")[:400])
        print(f"TOTAL_FAIL {len(errors)}")
        return 1
    ok("schema_create")

    proc = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(BACKEND),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        if not wait_http(f"{base}/health", timeout=40):
            out = ""
            try:
                if proc.stdout:
                    out = proc.stdout.read()[:500]
            except Exception:  # noqa: BLE001
                pass
            fail("server_boot", out or f"exit={proc.poll()}")
            print(f"TOTAL_FAIL {len(errors)}")
            return 1
        ok("server_boot")

        # Prefer httpx if available (cookie jar); fallback urllib.
        try:
            import httpx

            client = httpx.Client(base_url=base, timeout=30.0)
            use_httpx = True
        except Exception:  # noqa: BLE001
            import urllib.request

            client = None
            use_httpx = False

        def get_json(path: str, method: str = "GET", json_body=None, expected: int | None = None):
            if use_httpx:
                assert client is not None
                if method == "GET":
                    res = client.get(path)
                else:
                    res = client.request(method, path, json=json_body)
                if expected is not None and res.status_code != expected:
                    fail(f"http:{method}:{path}", f"status={res.status_code} body={res.text[:240]}")
                    return None, res
                try:
                    body = res.json()
                except Exception:  # noqa: BLE001
                    body = None
                return body, res
            # urllib fallback without cookies is weak; mark fail
            fail("http_client", "httpx required for cookie flow")
            return None, None

        body, res = get_json("/health")
        if body and body.get("success") and (body.get("data") or {}).get("status") == "ok":
            ok("health")
        else:
            fail("health", str(body)[:200])

        if use_httpx and client is not None:
            spa = client.get("/")
            text = spa.text.lower()
            if spa.status_code == 200 and ("html" in text or "<!doctype" in text):
                ok("spa_index")
            else:
                fail("spa_index", f"status={spa.status_code}")

            # also SPA deep path fallback
            spa2 = client.get("/recommendations")
            if spa2.status_code == 200 and ("html" in spa2.text.lower() or "<!doctype" in spa2.text.lower()):
                ok("spa_fallback")
            else:
                fail("spa_fallback", f"status={spa2.status_code}")

            body, _ = get_json("/api/v1/system/ready")
            if body and body.get("success") and (body.get("data") or {}).get("database") == "ok":
                ok("ready_database")
            else:
                fail("ready_database", str(body)[:200])

            body, res = get_json(
                "/api/v1/setup",
                method="POST",
                json_body={
                    "email": "fullstack@example.com",
                    "password": "TestPass123!",
                    "display_name": "Fullstack",
                },
                expected=201,
            )
            if body and body.get("success"):
                ok("setup")
            cookie = client.cookies.get("lottopilot_session")
            if cookie:
                ok("session_cookie")
            else:
                fail("session_cookie", str(dict(client.cookies)))

            body, _ = get_json("/api/v1/auth/me")
            if body and body.get("success") and (body.get("data") or {}).get("email") == "fullstack@example.com":
                ok("auth_me")
            else:
                fail("auth_me", str(body)[:200])

            rows = load_rows()
            body, _ = get_json("/api/v1/draws/import/commit", method="POST", json_body={"rows": rows})
            data = (body or {}).get("data") if body else None
            if data and data.get("inserted_count") == 20:
                ok("import_20")
            else:
                fail("import_20", str(body)[:200])

            body, res = get_json(
                "/api/v1/recommendations",
                method="POST",
                json_body={
                    "lottery_type": "ssq",
                    "target_issue": "2026021",
                    "seed": 99,
                    "candidate_count": 1000,
                    "enable_ai": False,
                },
                expected=201,
            )
            data = (body or {}).get("data") if body else None
            tickets = (data or {}).get("tickets") or []
            if data and data.get("status") == "succeeded" and len(tickets) == 5:
                ok("recommend_5")
            else:
                fail("recommend_5", str(body)[:240])

            if use_httpx and client is not None:
                client.close()

    except Exception as exc:  # noqa: BLE001
        fail("runtime", f"{exc}\n{traceback.format_exc()}")
    finally:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass
        try:
            db_path.unlink(missing_ok=True)
        except OSError:
            pass

    print(f"TOTAL_FAIL {len(errors)}")
    if errors:
        return 1
    print("LOCAL_FULLSTACK_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env sh
set -eu

echo "[entrypoint] starting LottoPilot"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] DATABASE_URL is required" >&2
  exit 1
fi

echo "[entrypoint] waiting for database..."
python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
deadline = time.time() + 60
last_error = None
while time.time() < deadline:
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print("[entrypoint] database is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(1)
print(f"[entrypoint] database not ready: {last_error}", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] running alembic upgrade head"
alembic upgrade head

echo "[entrypoint] launching: $*"
exec "$@"

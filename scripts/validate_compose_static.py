#!/usr/bin/env python3
"""Static validation of compose/deploy artifacts without Docker daemon.

Prints COMPOSE_STATIC_OK on success.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def ok(name: str) -> None:
    print(f"PASS {name}")


def fail(name: str, detail: str = "") -> None:
    print(f"FAIL {name}" + (f" {detail}" if detail else ""))
    errors.append(name)


def main() -> int:
    compose = ROOT / "docker-compose.yml"
    if not compose.exists():
        fail("compose_exists")
        print(f"TOTAL_FAIL {len(errors)}")
        return 1
    text = compose.read_text(encoding="utf-8")
    for token in [
        "LottoPilot-postgres",
        "LottoPilot",
        "lottopilot",
        "postgres:17",
        "healthcheck",
        "alembic",  # may only be in entrypoint
        "8000",
    ]:
        if token == "alembic":
            continue
        (ok if token in text else fail)(f"compose:{token}")

    # services postgres + app
    has_pg = bool(re.search(r"(?m)^\s*postgres:\s*$", text) or re.search(r"(?m)^\s*postgres:\s*#", text) or "\n  postgres:" in text or "\npostgres:" in text)
    has_app = bool(re.search(r"(?m)^\s*app:\s*$", text) or "\n  app:" in text or "\napp:" in text)
    # also accept services block containing both keys
    if ("postgres:" in text and "app:" in text and "services:" in text):
        ok("compose:services")
    else:
        fail("compose:services", f"pg={has_pg} app={has_app}")

    entry = ROOT / "scripts/entrypoint.sh"
    et = entry.read_text(encoding="utf-8") if entry.exists() else ""
    (ok if entry.exists() else fail)("entrypoint_exists")
    (ok if "alembic upgrade head" in et else fail)("entrypoint:alembic")
    (ok if "waiting for database" in et or "database is ready" in et else fail)("entrypoint:wait_db")

    dockerfile = ROOT / "Dockerfile"
    dt = dockerfile.read_text(encoding="utf-8") if dockerfile.exists() else ""
    (ok if "frontend-build" in dt and "frontend_dist" in dt else fail)("dockerfile:frontend_stage")
    (ok if "entrypoint.sh" in dt else fail)("dockerfile:entrypoint")
    (ok if "HEALTHCHECK" in dt else fail)("dockerfile:healthcheck")

    baota = ROOT / "deploy/baota/docker-compose.yml"
    bt = baota.read_text(encoding="utf-8") if baota.exists() else ""
    (ok if baota.exists() else fail)("baota_compose_exists")
    (ok if "LOTTOPILOT_IMAGE" in bt or "image:" in bt else fail)("baota:image")

    readme = ROOT / "deploy/baota/README.md"
    rt = readme.read_text(encoding="utf-8") if readme.exists() else ""
    (ok if "HTTPS" in rt or "反代" in rt or "nginx" in rt.lower() else fail)("baota:readme_proxy")
    (ok if "backup" in rt.lower() or "备份" in rt else fail)("baota:readme_backup")

    for name in ["scripts/backup_pg.sh", "scripts/restore_pg.sh", ".github/workflows/docker.yml", "docs/RELEASE_NOTES_v1.0.0.md"]:
        (ok if (ROOT / name).exists() else fail)(f"exists:{name}")

    docker_wf = (ROOT / ".github/workflows/docker.yml").read_text(encoding="utf-8")
    (ok if "setup-qemu-action" in docker_wf and "setup-buildx-action" in docker_wf else fail)("docker_wf:multiarch")
    (ok if "ghcr.io" in docker_wf else fail)("docker_wf:ghcr")

    print(f"TOTAL_FAIL {len(errors)}")
    if errors:
        return 1
    print("COMPOSE_STATIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

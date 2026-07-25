"""Ingestion package."""

from __future__ import annotations

from typing import Any

from app.services.ingestion.parser import parse_dlt_payload, parse_ssq_payload

__all__ = [
    "parse_ssq_payload",
    "parse_dlt_payload",
    "create_sync_run",
    "run_sync_job",
    "upsert_draw",
]


def __getattr__(name: str) -> Any:
    if name in {"create_sync_run", "run_sync_job", "upsert_draw"}:
        from app.services.ingestion.sync import create_sync_run, run_sync_job, upsert_draw

        mapping = {
            "create_sync_run": create_sync_run,
            "run_sync_job": run_sync_job,
            "upsert_draw": upsert_draw,
        }
        return mapping[name]
    raise AttributeError(name)
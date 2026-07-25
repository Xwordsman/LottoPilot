"""Draw synchronization service."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID
import asyncio
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.draw import Draw, IngestionError, IngestionRun
from app.models.system import Job
from app.services.ingestion.adapters import get_adapter
from app.services.jobs import mark_job_failed, mark_job_running, mark_job_succeeded, update_job_progress
from app.services.recommendation.evaluate import evaluate_recent_upserts
from app.utils.time import utcnow

SyncMode = Literal["incremental", "full"]


def _to_date(value: str) -> date:
    return date.fromisoformat(value)


def upsert_draw(db: Session, record: dict[str, Any]) -> str:
    """Upsert one normalized draw record. Returns inserted|updated|skipped."""
    existing = db.scalar(
        select(Draw).where(
            Draw.lottery_type == record["lottery_type"],
            Draw.issue == record["issue"],
        )
    )
    if existing is None:
        draw = Draw(
            lottery_type=record["lottery_type"],
            issue=record["issue"],
            draw_date=_to_date(record["draw_date"]),
            primary_numbers=record["primary_numbers"],
            secondary_numbers=record["secondary_numbers"],
            source=record["source_name"],
            source_checksum=record["source_hash"],
            raw_payload={
                "sales_amount": record.get("sales_amount"),
                "pool_amount": record.get("pool_amount"),
                "prize_tiers": record.get("prize_tiers") or [],
                "source_url": record.get("source_url"),
                "raw_item": record.get("raw_item") or {},
            },
        )
        db.add(draw)
        return "inserted"

    if existing.source_checksum == record["source_hash"]:
        return "skipped"

    existing.draw_date = _to_date(record["draw_date"])
    existing.primary_numbers = record["primary_numbers"]
    existing.secondary_numbers = record["secondary_numbers"]
    existing.source = record["source_name"]
    existing.source_checksum = record["source_hash"]
    existing.raw_payload = {
        "sales_amount": record.get("sales_amount"),
        "pool_amount": record.get("pool_amount"),
        "prize_tiers": record.get("prize_tiers") or [],
        "source_url": record.get("source_url"),
        "raw_item": record.get("raw_item") or {},
    }
    db.add(existing)
    return "updated"


async def _sleep_between_pages() -> None:
    await asyncio.sleep(random.uniform(1.0, 2.0))


async def run_sync_job(
    db: Session,
    *,
    job: Job,
    run: IngestionRun,
    lottery_type: str,
    mode: SyncMode = "incremental",
    page_size: int = 30,
    max_pages: int | None = None,
) -> IngestionRun:
    adapter = get_adapter(lottery_type)
    mark_job_running(db, job, total=0)
    run.status = "running"
    run.started_at = utcnow()
    db.add(run)
    db.commit()

    latest_issue: str | None = None
    touched_issues: list[str] = []
    if mode == "incremental":
        latest_issue = db.scalar(
            select(Draw.issue)
            .where(Draw.lottery_type == lottery_type)
            .order_by(Draw.draw_date.desc(), Draw.issue.desc())
            .limit(1)
        )

    page_no = 1
    consecutive_known = 0
    try:
        while True:
            if max_pages is not None and page_no > max_pages:
                break
            if mode == "incremental" and page_no > 3:
                # Incremental only needs recent pages.
                break

            payload = await adapter.fetch_page(page_no, page_size=page_size)
            records = adapter.parse_page(payload)
            if not records:
                break

            run.pages_processed += 1
            for record in records:
                run.records_seen += 1
                try:
                    action = upsert_draw(db, record)
                    if action == "inserted":
                        run.inserted_count += 1
                        consecutive_known = 0
                        touched_issues.append(str(record["issue"]))
                    elif action == "updated":
                        run.updated_count += 1
                        consecutive_known = 0
                        touched_issues.append(str(record["issue"]))
                    else:
                        run.skipped_count += 1
                        if mode == "incremental" and latest_issue and record["issue"] <= latest_issue:
                            consecutive_known += 1
                except Exception as exc:  # noqa: BLE001
                    run.error_count += 1
                    db.add(
                        IngestionError(
                            run_id=run.id,
                            source_item_key=str(record.get("issue")),
                            raw_payload=record.get("raw_item") or record,
                            error_code=getattr(exc, "code", "INGESTION_ITEM_FAILED"),
                            error_message=str(getattr(exc, "message", exc)),
                        )
                    )

            run.cursor = str(page_no)
            update_job_progress(db, job, current=run.pages_processed)
            db.add(run)
            db.commit()

            if mode == "incremental" and consecutive_known >= 5:
                break
            if len(records) < page_size:
                break

            page_no += 1
            await _sleep_between_pages()

        if touched_issues:
            try:
                evaluate_recent_upserts(db, lottery_type=lottery_type, issues=touched_issues)
            except Exception:  # noqa: BLE001 - evaluation must not fail ingestion
                db.rollback()
        run.status = "succeeded"
        run.finished_at = utcnow()
        mark_job_succeeded(db, job)
        db.add(run)
        db.commit()
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error_summary = str(getattr(exc, "message", exc))
        run.finished_at = utcnow()
        mark_job_failed(
            db,
            job,
            code=getattr(exc, "code", "INGESTION_FAILED"),
            summary=run.error_summary or "ingestion failed",
        )
        db.add(run)
        db.commit()
        if isinstance(exc, AppError):
            raise
        raise AppError("INGESTION_FAILED", str(exc), status_code=500) from exc
    finally:
        close = getattr(adapter, "aclose", None)
        if callable(close):
            await close()


def create_sync_run(
    db: Session,
    *,
    job: Job,
    lottery_type: str,
    mode: SyncMode,
    source_name: str,
) -> IngestionRun:
    run = IngestionRun(
        job_id=job.id,
        source_name=source_name,
        lottery_type=lottery_type,
        mode=mode,
        status="queued",
    )
    db.add(run)
    db.flush()
    job.resource_type = "ingestion_run"
    job.resource_id = run.id
    db.add(job)
    return run


def get_run(db: Session, run_id: UUID) -> IngestionRun | None:
    return db.get(IngestionRun, run_id)

"""Optional APScheduler wiring for official draw sync."""

from __future__ import annotations

from typing import Any
import asyncio
import logging

logger = logging.getLogger(__name__)

_scheduler: Any | None = None


def start_scheduler(settings: Any) -> Any | None:
    """Start background sync scheduler when enabled. Fail-open on errors."""
    global _scheduler
    if not getattr(settings, "sync_enabled", True):
        logger.info("scheduler disabled by SYNC_ENABLED=false")
        return None
    if _scheduler is not None:
        return _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception as exc:  # noqa: BLE001
        logger.warning("apscheduler unavailable: %s", exc)
        return None

    scheduler = AsyncIOScheduler(timezone=getattr(settings, "tz", "Asia/Shanghai"))

    async def _run_sync(lottery_type: str) -> None:
        # Lazy import to avoid hard dependency cycles at module import time.
        from app.db.session import SessionLocal
        from app.services.ingestion.adapters import get_adapter
        from app.services.ingestion.sync import create_sync_run, run_sync_job
        from app.services.jobs import create_job

        db = SessionLocal()
        try:
            adapter = get_adapter(lottery_type)
            job = create_job(
                db,
                job_type="draw_sync",
                payload_summary={"lottery_type": lottery_type, "mode": "incremental", "source": "scheduler"},
                resource_type="ingestion_run",
            )
            run = create_sync_run(
                db,
                job=job,
                lottery_type=lottery_type,
                mode="incremental",
                source_name=getattr(adapter, "source_name", lottery_type),
            )
            db.commit()
            await run_sync_job(
                db,
                job=job,
                run=run,
                lottery_type=lottery_type,
                mode="incremental",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("scheduled sync failed lottery=%s err=%s", lottery_type, exc)
            db.rollback()
        finally:
            db.close()

    def _add_cron(lottery_type: str, expr: str) -> None:
        # cron: minute hour day month day_of_week
        parts = expr.split()
        if len(parts) != 5:
            logger.warning("invalid cron for %s: %s", lottery_type, expr)
            return
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=getattr(settings, "tz", "Asia/Shanghai"),
        )
        scheduler.add_job(
            lambda lt=lottery_type: asyncio.create_task(_run_sync(lt)),
            trigger=trigger,
            id=f"sync-{lottery_type}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    try:
        _add_cron("ssq", getattr(settings, "sync_cron_ssq", "0 22 * * 2,4,7"))
        _add_cron("dlt", getattr(settings, "sync_cron_dlt", "5 21 * * 1,3,6"))
        scheduler.start()
        _scheduler = scheduler
        logger.info("scheduler started")
        return scheduler
    except Exception as exc:  # noqa: BLE001
        logger.exception("failed to start scheduler: %s", exc)
        return None


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:  # noqa: BLE001
        pass
    _scheduler = None

"""Job service helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.system import Job
from app.utils.time import utcnow


def create_job(
    db: Session,
    *,
    job_type: str,
    payload_summary: dict[str, Any] | None = None,
    created_by: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> Job:
    job = Job(
        job_type=job_type,
        status="queued",
        progress_current=0,
        progress_total=0,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_summary=payload_summary or {},
        created_by=created_by,
    )
    db.add(job)
    db.flush()
    return job


def mark_job_running(db: Session, job: Job, *, total: int = 0) -> Job:
    job.status = "running"
    job.started_at = utcnow()
    job.heartbeat_at = utcnow()
    job.progress_total = total
    db.add(job)
    db.flush()
    return job


def update_job_progress(db: Session, job: Job, *, current: int, total: int | None = None) -> Job:
    job.progress_current = current
    if total is not None:
        job.progress_total = total
    job.heartbeat_at = utcnow()
    db.add(job)
    db.flush()
    return job


def mark_job_succeeded(db: Session, job: Job) -> Job:
    job.status = "succeeded"
    job.finished_at = utcnow()
    job.heartbeat_at = utcnow()
    db.add(job)
    db.flush()
    return job


def mark_job_failed(db: Session, job: Job, *, code: str, summary: str) -> Job:
    job.status = "failed"
    job.error_code = code
    job.error_summary = summary
    job.finished_at = utcnow()
    job.heartbeat_at = utcnow()
    db.add(job)
    db.flush()
    return job

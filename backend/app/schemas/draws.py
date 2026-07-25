"""Draw and ingestion schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

LotteryType = Literal["ssq", "dlt"]
SyncMode = Literal["incremental", "full"]


class DrawPublic(BaseModel):
    id: UUID
    lottery_type: LotteryType
    issue: str
    draw_date: date
    primary_numbers: list[int]
    secondary_numbers: list[int]
    source: str
    source_checksum: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DrawDetail(DrawPublic):
    raw_payload: dict[str, Any] | None = None


class DrawListData(BaseModel):
    items: list[DrawPublic]
    page: int
    page_size: int
    total: int
    total_pages: int


class LatestDrawsData(BaseModel):
    ssq: DrawPublic | None = None
    dlt: DrawPublic | None = None


class SyncRequest(BaseModel):
    lottery_type: LotteryType
    mode: SyncMode = "incremental"
    page_size: int = Field(default=30, ge=10, le=100)


class SyncAcceptedData(BaseModel):
    job_id: UUID
    run_id: UUID
    lottery_type: LotteryType
    mode: SyncMode
    status: str


class IngestionRunPublic(BaseModel):
    id: UUID
    job_id: UUID | None
    source_name: str
    lottery_type: str
    mode: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    pages_processed: int
    records_seen: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    cursor: str | None
    error_summary: str | None

    model_config = {"from_attributes": True}


class IngestionRunListData(BaseModel):
    items: list[IngestionRunPublic]
    page: int
    page_size: int
    total: int
    total_pages: int


class ImportPreviewRow(BaseModel):
    row_number: int
    lottery_type: str | None = None
    issue: str | None = None
    draw_date: str | None = None
    primary_numbers: list[int] | None = None
    secondary_numbers: list[int] | None = None
    valid: bool
    errors: list[str] = Field(default_factory=list)


class ImportPreviewData(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ImportCommitRequest(BaseModel):
    rows: list[dict[str, Any]]


class ImportCommitData(BaseModel):
    inserted_count: int
    updated_count: int
    skipped_count: int
    error_count: int

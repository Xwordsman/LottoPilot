"""Parser unit tests for official draw payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.errors import ValidationAppError
from app.services.ingestion.parser import parse_dlt_payload, parse_ssq_payload, normalize_draw_record

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_ssq_payload() -> None:
    payload = json.loads((FIXTURES / "ssq_sample.json").read_text(encoding="utf-8"))
    records = parse_ssq_payload(payload)
    assert len(records) == 2
    first = records[0]
    assert first["lottery_type"] == "ssq"
    assert first["issue"] == "2026072"
    assert first["draw_date"] == "2026-07-21"
    assert first["primary_numbers"] == [3, 8, 12, 18, 25, 31]
    assert first["secondary_numbers"] == [9]
    assert first["source_name"] == "cwl_official"
    assert first["source_hash"]


def test_parse_dlt_payload() -> None:
    payload = json.loads((FIXTURES / "dlt_sample.json").read_text(encoding="utf-8"))
    records = parse_dlt_payload(payload)
    assert len(records) == 2
    first = records[0]
    assert first["lottery_type"] == "dlt"
    assert first["issue"] == "26072"
    assert first["primary_numbers"] == [2, 8, 15, 21, 33]
    assert first["secondary_numbers"] == [5, 11]


def test_normalize_rejects_bad_issue() -> None:
    with pytest.raises(ValidationAppError):
        normalize_draw_record(
            lottery_type="ssq",
            issue="abc",
            draw_date="2026-07-21",
            primary_numbers=[1, 2, 3, 4, 5, 6],
            secondary_numbers=[7],
            source_name="manual",
        )


def test_normalize_sorts_numbers() -> None:
    record = normalize_draw_record(
        lottery_type="ssq",
        issue="2026001",
        draw_date="2026-01-01",
        primary_numbers=[10, 1, 5, 8, 3, 20],
        secondary_numbers=[16],
        source_name="manual",
    )
    assert record["primary_numbers"] == [1, 3, 5, 8, 10, 20]

"""Parser unit tests for 500.com history HTML."""

from __future__ import annotations

from pathlib import Path

from app.services.ingestion.parser import parse_500_history_html

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_500_ssq_html() -> None:
    html = (FIXTURES / "ssq_500_sample.html").read_text(encoding="utf-8")
    records = parse_500_history_html(html, lottery_type="ssq")
    assert len(records) >= 1
    first = records[0]
    assert first["lottery_type"] == "ssq"
    assert first["issue"] == "2026084"
    assert first["draw_date"] == "2026-07-23"
    assert first["primary_numbers"] == [1, 5, 6, 10, 12, 16]
    assert first["secondary_numbers"] == [5]
    assert first["source_name"] == "500com"
    assert first["source_hash"]
    assert first.get("sales_amount") in {None, "348718788"}
    assert first.get("pool_amount") in {None, "480566551"}


def test_parse_500_dlt_html() -> None:
    html = (FIXTURES / "dlt_500_sample.html").read_text(encoding="utf-8")
    records = parse_500_history_html(html, lottery_type="dlt")
    assert len(records) >= 1
    by_issue = {item["issue"]: item for item in records}
    assert "26082" in by_issue
    item = by_issue["26082"]
    assert item["lottery_type"] == "dlt"
    assert len(item["primary_numbers"]) == 5
    assert len(item["secondary_numbers"]) == 2
    assert item["source_name"] == "500com"


def test_parse_500_skips_header_rows() -> None:
    html = (FIXTURES / "dlt_500_sample.html").read_text(encoding="utf-8")
    records = parse_500_history_html(html, lottery_type="dlt")
    for item in records:
        assert item["issue"].isdigit()
        assert len(item["primary_numbers"]) == 5
        assert len(item["secondary_numbers"]) == 2

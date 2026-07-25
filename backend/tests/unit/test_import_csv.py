"""CSV import helper tests."""

from __future__ import annotations

from app.services.ingestion.import_csv import parse_csv_text, preview_import_rows


def test_parse_and_preview_csv() -> None:
    content = """lottery_type,issue,draw_date,primary_numbers,secondary_numbers
ssq,2026001,2026-01-01,"1,2,3,4,5,6",7
ssq,bad,2026-01-02,"1,2,3,4,5,6",7
"""
    rows = parse_csv_text(content)
    assert len(rows) == 2
    preview = preview_import_rows(rows)
    assert preview["total_rows"] == 2
    assert preview["valid_rows"] == 1
    assert preview["invalid_rows"] == 1
    assert preview["rows"][0]["valid"] is True
    assert preview["rows"][1]["valid"] is False

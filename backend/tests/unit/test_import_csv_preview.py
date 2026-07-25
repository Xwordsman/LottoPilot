"""CSV import pure preview tests."""

from __future__ import annotations

from pathlib import Path

from app.services.ingestion.import_csv import parse_csv_text, preview_import_rows

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ssq_import_20.csv"


def test_preview_ssq_import_20() -> None:
    raw = parse_csv_text(FIXTURE.read_text(encoding="utf-8"))
    preview = preview_import_rows(raw)
    assert preview["total_rows"] == 20
    assert preview["valid_rows"] == 20
    assert preview["invalid_rows"] == 0
    assert preview["rows"][0]["issue"] == "2026001"
    assert preview["rows"][0]["primary_numbers"] == [1, 5, 12, 18, 22, 33]

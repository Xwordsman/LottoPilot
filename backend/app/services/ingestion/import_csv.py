"""CSV/manual import helpers for draw records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import csv
import io
import re

from app.core.errors import ValidationAppError
from app.services.ingestion.parser import normalize_draw_record

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_NUM_SPLIT = re.compile(r"[\s,|+/，]+")


def _parse_number_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    text = str(value).strip().replace("[", "").replace("]", "")
    if not text:
        return []
    return [int(part) for part in _NUM_SPLIT.split(text) if part]


def parse_csv_text(content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValidationAppError("CSV 缺少表头", code="IMPORT_INVALID")
    rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(reader, start=2):
        rows.append(
            {
                "row_number": idx,
                "lottery_type": (raw.get("lottery_type") or raw.get("彩种") or "").strip().lower() or None,
                "issue": (raw.get("issue") or raw.get("期号") or "").strip() or None,
                "draw_date": (raw.get("draw_date") or raw.get("开奖日期") or "").strip() or None,
                "primary_numbers": raw.get("primary_numbers") or raw.get("主区") or raw.get("红球"),
                "secondary_numbers": raw.get("secondary_numbers") or raw.get("次区") or raw.get("蓝球"),
            }
        )
    return rows


def preview_import_rows(raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    preview_rows: list[dict[str, Any]] = []
    valid = 0
    invalid = 0
    for raw in raw_rows:
        errors: list[str] = []
        row_number = int(raw.get("row_number") or 0)
        try:
            record = normalize_draw_record(
                lottery_type=str(raw.get("lottery_type") or ""),
                issue=str(raw.get("issue") or ""),
                draw_date=str(raw.get("draw_date") or ""),
                primary_numbers=_parse_number_list(raw.get("primary_numbers")),
                secondary_numbers=_parse_number_list(raw.get("secondary_numbers")),
                source_name="manual_import",
            )
            preview_rows.append(
                {
                    "row_number": row_number,
                    "lottery_type": record["lottery_type"],
                    "issue": record["issue"],
                    "draw_date": record["draw_date"],
                    "primary_numbers": record["primary_numbers"],
                    "secondary_numbers": record["secondary_numbers"],
                    "valid": True,
                    "errors": [],
                }
            )
            valid += 1
        except Exception as exc:  # noqa: BLE001
            invalid += 1
            message = str(getattr(exc, "message", exc))
            errors.append(message)
            preview_rows.append(
                {
                    "row_number": row_number,
                    "lottery_type": raw.get("lottery_type"),
                    "issue": raw.get("issue"),
                    "draw_date": str(raw.get("draw_date") or "") or None,
                    "primary_numbers": None,
                    "secondary_numbers": None,
                    "valid": False,
                    "errors": errors,
                }
            )
    return {
        "total_rows": len(raw_rows),
        "valid_rows": valid,
        "invalid_rows": invalid,
        "rows": preview_rows,
    }


def commit_import_rows(db: "Session", raw_rows: list[dict[str, Any]]) -> dict[str, int]:
    # Lazy imports keep pure preview/path offline without ORM stack.
    from app.services.ingestion.sync import upsert_draw
    from app.services.recommendation.evaluate import evaluate_recent_upserts

    inserted = updated = skipped = error = 0
    touched: dict[str, list[str]] = {}
    for raw in raw_rows:
        try:
            record = normalize_draw_record(
                lottery_type=str(raw.get("lottery_type") or ""),
                issue=str(raw.get("issue") or ""),
                draw_date=str(raw.get("draw_date") or ""),
                primary_numbers=_parse_number_list(raw.get("primary_numbers")),
                secondary_numbers=_parse_number_list(raw.get("secondary_numbers")),
                source_name="manual_import",
            )
            action = upsert_draw(db, record)
            if action == "inserted":
                inserted += 1
                touched.setdefault(record["lottery_type"], []).append(record["issue"])
            elif action == "updated":
                updated += 1
                touched.setdefault(record["lottery_type"], []).append(record["issue"])
            else:
                skipped += 1
        except Exception:  # noqa: BLE001
            error += 1
    db.commit()
    for lottery_type, issues in touched.items():
        try:
            evaluate_recent_upserts(db, lottery_type=lottery_type, issues=issues)
        except Exception:  # noqa: BLE001
            db.rollback()
    return {
        "inserted_count": inserted,
        "updated_count": updated,
        "skipped_count": skipped,
        "error_count": error,
    }

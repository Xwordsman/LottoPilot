"""Official draw parsers and normalization helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import ValidationAppError
from app.utils.lottery import validate_ticket_numbers

_ISSUE_RE = re.compile(r"^\d{5,10}$")


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_date(value: str) -> date:
    text = value.strip()
    # CWL often returns "2026-07-21(二)"
    text = re.split(r"[(\s]", text, maxsplit=1)[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationAppError("开奖日期无法解析", code="DRAW_VALIDATION_FAILED", details={"value": value})


def _parse_money(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).replace(",", "").strip()
    try:
        return str(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationAppError("金额字段无法解析", code="DRAW_VALIDATION_FAILED") from exc


def _split_numbers(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    text = str(value).strip()
    if not text:
        return []
    text = text.replace("[", "").replace("]", "").replace("，", ",")
    parts = re.split(r"[\s,|+/]+", text)
    return [int(p) for p in parts if p]


def normalize_draw_record(
    *,
    lottery_type: str,
    issue: str,
    draw_date: date | str,
    primary_numbers: list[int] | str,
    secondary_numbers: list[int] | str,
    source_name: str,
    source_url: str | None = None,
    sales_amount: Any = None,
    pool_amount: Any = None,
    prize_tiers: Any = None,
    raw_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lottery_type not in {"ssq", "dlt"}:
        raise ValidationAppError("不支持的彩种", code="UNSUPPORTED_LOTTERY")

    issue_text = str(issue).strip()
    if not _ISSUE_RE.match(issue_text):
        raise ValidationAppError("期号格式不正确", code="DRAW_VALIDATION_FAILED", details={"issue": issue_text})

    if isinstance(draw_date, str):
        parsed_date = _parse_date(draw_date)
    else:
        parsed_date = draw_date

    primary = _split_numbers(primary_numbers)
    secondary = _split_numbers(secondary_numbers)
    primary, secondary = validate_ticket_numbers(lottery_type, primary, secondary)  # type: ignore[arg-type]

    record = {
        "lottery_type": lottery_type,
        "issue": issue_text,
        "draw_date": parsed_date.isoformat(),
        "primary_numbers": primary,
        "secondary_numbers": secondary,
        "sales_amount": _parse_money(sales_amount),
        "pool_amount": _parse_money(pool_amount),
        "prize_tiers": prize_tiers or [],
        "source_name": source_name,
        "source_url": source_url,
        "raw_item": raw_item or {},
    }
    record["source_hash"] = _stable_hash(
        {
            "lottery_type": record["lottery_type"],
            "issue": record["issue"],
            "draw_date": record["draw_date"],
            "primary_numbers": record["primary_numbers"],
            "secondary_numbers": record["secondary_numbers"],
            "sales_amount": record["sales_amount"],
            "pool_amount": record["pool_amount"],
            "prize_tiers": record["prize_tiers"],
            "source_name": record["source_name"],
        }
    )
    return record


def parse_ssq_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse CWL findDrawNotice style payload into normalized records."""
    result = payload.get("result")
    if result is None and isinstance(payload.get("data"), dict):
        result = payload["data"].get("result")
    if not isinstance(result, list):
        # Some fixtures may pass a single item.
        if {"code", "red", "blue"} <= set(payload.keys()):
            result = [payload]
        else:
            raise ValidationAppError("双色球响应缺少 result 列表", code="INGESTION_PARSE_FAILED")

    records: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        records.append(
            normalize_draw_record(
                lottery_type="ssq",
                issue=str(item.get("code", "")),
                draw_date=str(item.get("date", "")),
                primary_numbers=item.get("red", ""),
                secondary_numbers=item.get("blue", ""),
                sales_amount=item.get("sales"),
                pool_amount=item.get("poolmoney"),
                prize_tiers=item.get("prizegrades") or [],
                source_name="cwl_official",
                source_url=item.get("detailsLink"),
                raw_item=item,
            )
        )
    return records


def parse_dlt_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Sporttery history page payload into normalized records."""
    value = payload.get("value")
    if isinstance(value, dict):
        items = value.get("list") or value.get("historyList") or []
    elif isinstance(payload.get("list"), list):
        items = payload["list"]
    elif {"lotteryDrawNum", "lotteryDrawResult"} <= set(payload.keys()):
        items = [payload]
    else:
        raise ValidationAppError("大乐透响应缺少列表数据", code="INGESTION_PARSE_FAILED")

    if not isinstance(items, list):
        raise ValidationAppError("大乐透列表格式错误", code="INGESTION_PARSE_FAILED")

    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        numbers = _split_numbers(item.get("lotteryDrawResult", ""))
        if len(numbers) < 7:
            raise ValidationAppError(
                "大乐透开奖号码数量不足",
                code="DRAW_VALIDATION_FAILED",
                details={"issue": item.get("lotteryDrawNum")},
            )
        records.append(
            normalize_draw_record(
                lottery_type="dlt",
                issue=str(item.get("lotteryDrawNum", "")),
                draw_date=str(item.get("lotteryDrawTime", "")),
                primary_numbers=numbers[:5],
                secondary_numbers=numbers[5:7],
                sales_amount=item.get("totalSaleAmount"),
                pool_amount=item.get("poolBalanceAfterdraw"),
                prize_tiers=item.get("prizeLevelList") or [],
                source_name="sporttery_official",
                source_url=item.get("drawPdfUrl"),
                raw_item=item,
            )
        )
    return records

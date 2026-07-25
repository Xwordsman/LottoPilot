"""Official draw parsers and normalization helpers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
import hashlib
import json
import re

from decimal import Decimal, InvalidOperation

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

def _normalize_source_issue(lottery_type: str, issue: str) -> str:
    """Normalize third-party issue codes to official-like formats."""
    issue_text = str(issue).strip()
    # 500.com SSQ uses YYNNN (e.g. 26084) while CWL uses YYYYNNN (2026084).
    if lottery_type == "ssq" and re.fullmatch(r"\d{5}", issue_text):
        return f"20{issue_text}"
    return issue_text


def parse_500_history_html(html: str, *, lottery_type: str) -> list[dict[str, Any]]:
    """Parse 500.com history table HTML into normalized draw records."""
    if lottery_type not in {"ssq", "dlt"}:
        raise ValidationAppError("unsupported lottery", code="UNSUPPORTED_LOTTERY")

    rows = re.findall(r'<tr[^>]*class="t_tr1"[^>]*>(.*?)</tr>', html, flags=re.I | re.S)
    records: list[dict[str, Any]] = []
    money_re = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d{6,})$")
    date_re = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")

    for row_html in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.I | re.S)
        cleaned: list[str] = []
        for cell in cells:
            cell_text = re.sub(r"<[^>]+>", "", cell)
            cell_text = cell_text.replace("\xa0", " ").replace("&nbsp;", " ").strip()
            if cell_text and cell_text != "&nbsp;":
                cleaned.append(cell_text)
        if len(cleaned) < 8:
            continue

        issue_idx = next((i for i, token in enumerate(cleaned) if re.fullmatch(r"\d{5,10}", token)), None)
        if issue_idx is None:
            continue
        issue = _normalize_source_issue(lottery_type, cleaned[issue_idx])

        need = 7
        nums: list[int] = []
        cursor = issue_idx + 1
        while cursor < len(cleaned) and len(nums) < need:
            token = cleaned[cursor]
            if re.fullmatch(r"\d{1,2}", token):
                nums.append(int(token))
                cursor += 1
                continue
            if nums:
                break
            cursor += 1
        if len(nums) < need:
            continue

        if lottery_type == "ssq":
            primary = nums[:6]
            secondary = [nums[6]]
        else:
            primary = nums[:5]
            secondary = nums[5:7]

        draw_date = next((token for token in reversed(cleaned) if date_re.match(token)), None)
        if draw_date is None:
            continue

        money_vals = [token for token in cleaned[cursor:] if money_re.match(token)]
        pool = money_vals[0] if money_vals else None
        sales = money_vals[-1] if len(money_vals) >= 2 else None

        try:
            records.append(
                normalize_draw_record(
                    lottery_type=lottery_type,
                    issue=issue,
                    draw_date=draw_date,
                    primary_numbers=primary,
                    secondary_numbers=secondary,
                    sales_amount=sales,
                    pool_amount=pool,
                    prize_tiers=[],
                    source_name="500com",
                    source_url=f"https://datachart.500.com/{lottery_type}/history/history.shtml",
                    raw_item={"cells": cleaned},
                )
            )
        except ValidationAppError:
            continue

    return records

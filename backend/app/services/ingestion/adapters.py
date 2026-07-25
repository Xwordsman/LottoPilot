"""HTTP adapters for lottery draw sources."""

from __future__ import annotations

from typing import Any, Protocol
import asyncio
import random

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.ingestion.parser import parse_500_history_html, parse_dlt_payload, parse_ssq_payload


class DrawSourceAdapter(Protocol):
    source_name: str
    lottery_type: str

    async def fetch_page(self, page_no: int, page_size: int) -> dict[str, Any]:
        ...

    def parse_page(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        ...


class BaseHttpAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True)
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        client = await self._get_client()
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    raise AppError(
                        "SOURCE_TEMPORARY_ERROR",
                        f"source temporary error: HTTP {response.status_code}",
                        status_code=502,
                    )
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= 3:
                    break
                await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.8))
        raise AppError(
            "SOURCE_FETCH_FAILED",
            f"failed to fetch source: {last_error}",
            status_code=502,
        )

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._request_with_retries(method, url, **kwargs)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type and "json" not in content_type:
            raise AppError(
                "SOURCE_WAF_BLOCKED",
                "source returned HTML/WAF page",
                status_code=502,
            )
        data = response.json()
        if not isinstance(data, dict):
            raise AppError("SOURCE_INVALID_JSON", "source JSON root is not object", status_code=502)
        return data

    async def _request_text(self, method: str, url: str, **kwargs: Any) -> str:
        response = await self._request_with_retries(method, url, **kwargs)
        return response.text


class SsqOfficialAdapter(BaseHttpAdapter):
    source_name = "cwl_official"
    lottery_type = "ssq"
    url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"

    async def fetch_page(self, page_no: int, page_size: int = 30) -> dict[str, Any]:
        headers = {
            "User-Agent": "LottoPilot/0.1 (+https://github.com/Xwordsman/LottoPilot)",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.cwl.gov.cn/",
        }
        params = {
            "name": "ssq",
            "pageNo": page_no,
            "pageSize": page_size,
            "systemType": "PC",
        }
        return await self._request_json("GET", self.url, params=params, headers=headers)

    def parse_page(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return parse_ssq_payload(payload)


class DltOfficialAdapter(BaseHttpAdapter):
    source_name = "sporttery_official"
    lottery_type = "dlt"
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"

    async def fetch_page(self, page_no: int, page_size: int = 30) -> dict[str, Any]:
        headers = {
            "User-Agent": "LottoPilot/0.1 (+https://github.com/Xwordsman/LottoPilot)",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.sporttery.cn/",
        }
        params = {
            "gameNo": "85",
            "provinceId": "0",
            "pageSize": page_size,
            "isVerify": "1",
            "pageNo": page_no,
        }
        return await self._request_json("GET", self.url, params=params, headers=headers)

    def parse_page(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return parse_dlt_payload(payload)


class FiveHundredComAdapter(BaseHttpAdapter):
    """Adapter for datachart.500.com history tables."""

    source_name = "500com"
    local_pagination = True

    def __init__(self, lottery_type: str, client: httpx.AsyncClient | None = None) -> None:
        if lottery_type not in {"ssq", "dlt"}:
            raise AppError("UNSUPPORTED_LOTTERY", f"unsupported lottery: {lottery_type}", status_code=422)
        super().__init__(client=client)
        self.lottery_type = lottery_type
        self._records: list[dict[str, Any]] | None = None

    @property
    def history_url(self) -> str:
        return f"https://datachart.500.com/{self.lottery_type}/history/newinc/history.php"

    async def _load_all_records(self) -> list[dict[str, Any]]:
        if self._records is not None:
            return self._records

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"https://datachart.500.com/{self.lottery_type}/history/history.shtml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        params = {"start": "00001", "end": "99999"}
        html = await self._request_text("GET", self.history_url, params=params, headers=headers)
        records = parse_500_history_html(html, lottery_type=self.lottery_type)
        if not records:
            raise AppError(
                "SOURCE_EMPTY",
                f"500.com returned no parseable {self.lottery_type} draws",
                status_code=502,
            )
        self._records = sorted(records, key=lambda item: item["issue"], reverse=True)
        return self._records

    async def fetch_page(self, page_no: int, page_size: int = 30) -> dict[str, Any]:
        if page_no < 1:
            page_no = 1
        if page_size < 1:
            page_size = 30
        records = await self._load_all_records()
        start = (page_no - 1) * page_size
        end = start + page_size
        page_records = records[start:end]
        return {
            "source": self.source_name,
            "lottery_type": self.lottery_type,
            "page_no": page_no,
            "page_size": page_size,
            "total": len(records),
            "records": page_records,
        }

    def parse_page(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        records = payload.get("records")
        if isinstance(records, list):
            return records
        html = payload.get("html")
        if isinstance(html, str) and html.strip():
            return parse_500_history_html(html, lottery_type=self.lottery_type)
        return []


class FallbackAdapter:
    """Try adapters in order until one successfully returns page-1 data."""

    def __init__(self, adapters: list[Any], *, source_name: str = "auto") -> None:
        if not adapters:
            raise AppError("SOURCE_CONFIG_INVALID", "no draw adapters configured", status_code=500)
        self._adapters = adapters
        self._chosen: Any | None = None
        self.source_name = source_name
        self.lottery_type = adapters[0].lottery_type

    @property
    def local_pagination(self) -> bool:
        if self._chosen is not None:
            return bool(getattr(self._chosen, "local_pagination", False))
        return False

    async def aclose(self) -> None:
        for adapter in self._adapters:
            close = getattr(adapter, "aclose", None)
            if callable(close):
                await close()

    async def fetch_page(self, page_no: int, page_size: int = 30) -> dict[str, Any]:
        if self._chosen is not None:
            payload = await self._chosen.fetch_page(page_no, page_size)
            return {
                "source": self._chosen.source_name,
                "records": self._chosen.parse_page(payload),
                "raw": payload,
            }

        errors: list[str] = []
        for adapter in self._adapters:
            try:
                payload = await adapter.fetch_page(page_no, page_size)
                records = adapter.parse_page(payload)
                if page_no == 1 and not records:
                    errors.append(f"{adapter.source_name}: empty page")
                    continue
                self._chosen = adapter
                self.source_name = adapter.source_name
                return {
                    "source": adapter.source_name,
                    "records": records,
                    "raw": payload,
                }
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{adapter.source_name}: {exc}")
                continue

        detail = "; ".join(errors) if errors else "all sources failed"
        raise AppError("SOURCE_FETCH_FAILED", f"all draw sources failed: {detail}", status_code=502)

    def parse_page(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        records = payload.get("records")
        if isinstance(records, list):
            return records
        if self._chosen is not None:
            raw = payload.get("raw")
            if isinstance(raw, dict):
                return self._chosen.parse_page(raw)
        return []


def _official_adapter(lottery_type: str, client: httpx.AsyncClient | None = None) -> DrawSourceAdapter:
    if lottery_type == "ssq":
        return SsqOfficialAdapter(client=client)
    if lottery_type == "dlt":
        return DltOfficialAdapter(client=client)
    raise AppError("UNSUPPORTED_LOTTERY", f"unsupported lottery: {lottery_type}", status_code=422)


def get_adapter(lottery_type: str, client: httpx.AsyncClient | None = None) -> DrawSourceAdapter:
    if lottery_type not in {"ssq", "dlt"}:
        raise AppError("UNSUPPORTED_LOTTERY", f"unsupported lottery: {lottery_type}", status_code=422)

    source = (get_settings().draw_data_source or "auto").strip().lower()
    if source in {"500", "500com", "fivehundred", "wubai"}:
        return FiveHundredComAdapter(lottery_type=lottery_type, client=client)
    if source in {"official", "cwl", "sporttery"}:
        return _official_adapter(lottery_type, client=client)

    primary = FiveHundredComAdapter(lottery_type=lottery_type, client=client)
    secondary = _official_adapter(lottery_type, client=client)
    return FallbackAdapter([primary, secondary], source_name="auto")

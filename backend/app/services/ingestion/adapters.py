"""HTTP adapters for official lottery sources."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Protocol

import httpx

from app.core.errors import AppError
from app.services.ingestion.parser import parse_dlt_payload, parse_ssq_payload


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
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0))
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        client = await self._get_client()
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = await client.request(method, url, **kwargs)
                content_type = response.headers.get("content-type", "")
                if response.status_code == 429 or response.status_code >= 500:
                    raise AppError(
                        "SOURCE_TEMPORARY_ERROR",
                        f"source temporary error: HTTP {response.status_code}",
                        status_code=502,
                    )
                if "text/html" in content_type and "json" not in content_type:
                    raise AppError(
                        "SOURCE_WAF_BLOCKED",
                        "source returned HTML/WAF page",
                        status_code=502,
                    )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise AppError("SOURCE_INVALID_JSON", "source JSON root is not object", status_code=502)
                return data
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= 3:
                    break
                await asyncio.sleep((2**attempt) + random.uniform(0.1, 0.8))
        raise AppError(
            "SOURCE_FETCH_FAILED",
            f"failed to fetch source: {last_error}",
            status_code=502,
        )


class SsqOfficialAdapter(BaseHttpAdapter):
    source_name = "cwl_official"
    lottery_type = "ssq"
    url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"

    async def fetch_page(self, page_no: int, page_size: int = 30) -> dict[str, Any]:
        headers = {
            "User-Agent": "LottoPilot/0.1 (+https://github.com/lottopilot)",
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
            "User-Agent": "LottoPilot/0.1 (+https://github.com/lottopilot)",
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


def get_adapter(lottery_type: str, client: httpx.AsyncClient | None = None) -> DrawSourceAdapter:
    if lottery_type == "ssq":
        return SsqOfficialAdapter(client=client)
    if lottery_type == "dlt":
        return DltOfficialAdapter(client=client)
    raise AppError("UNSUPPORTED_LOTTERY", f"unsupported lottery: {lottery_type}", status_code=422)

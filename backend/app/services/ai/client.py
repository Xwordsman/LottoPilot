"""OpenAI-compatible LLM client and AI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import hashlib
import json
import time

import httpx

from app.core.errors import AppError
from app.core.security import decrypt_secret, encrypt_secret, mask_secret

__all__ = [
    "ModelInfo",
    "LLMClient",
    "OpenAICompatibleClient",
    "encrypt_api_key",
    "decrypt_api_key",
    "public_key_mask",
    "response_hash",
    "apply_ai_rerank",
]


@dataclass
class ModelInfo:
    model: str
    latency_ms: int
    status: str


class LLMClient(Protocol):
    async def test_connection(self) -> ModelInfo: ...

    async def chat_json(self, *, system: str, user: str, temperature: float = 0.2) -> dict[str, Any]: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 30,
        max_tokens: int = 1024,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    async def test_connection(self) -> ModelInfo:
        started = time.perf_counter()
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    await self.chat_json(
                        system="You are a health check bot.",
                        user='Return JSON {"ok": true}',
                        temperature=0,
                    )
                latency = int((time.perf_counter() - started) * 1000)
                return ModelInfo(model=self.model, latency_ms=latency, status="ok")
            except Exception as exc:  # noqa: BLE001
                raise AppError("AI_CONNECTION_FAILED", f"AI 连接失败: {exc}", status_code=502) from exc

    async def chat_json(self, *, system: str, user: str, temperature: float = 0.2) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise AppError(
                    "AI_REQUEST_FAILED",
                    f"AI 请求失败: HTTP {resp.status_code}",
                    status_code=502,
                    details={"body": resp.text[:500]},
                )
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise AppError("AI_INVALID_JSON", "AI 返回非 JSON", status_code=502) from exc
            if not isinstance(parsed, dict):
                raise AppError("AI_INVALID_JSON", "AI JSON 根节点必须是对象", status_code=502)
            return parsed


def encrypt_api_key(api_key: str, app_secret: str) -> str:
    return encrypt_secret(api_key, app_secret)


def decrypt_api_key(ciphertext: str, app_secret: str) -> str:
    return decrypt_secret(ciphertext, app_secret)


def public_key_mask(api_key: str | None) -> str:
    if not api_key:
        return ""
    return mask_secret(api_key, visible=4)


def response_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
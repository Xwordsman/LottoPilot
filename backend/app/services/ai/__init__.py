"""AI service package."""

from __future__ import annotations

from typing import Any

from app.services.ai.rerank import apply_ai_rerank

__all__ = ["OpenAICompatibleClient", "apply_ai_rerank", "encrypt_api_key", "public_key_mask"]


def __getattr__(name: str) -> Any:
    if name in {"OpenAICompatibleClient", "encrypt_api_key", "public_key_mask"}:
        from app.services.ai import client as ai_client

        return getattr(ai_client, name)
    raise AttributeError(name)
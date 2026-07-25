"""Optional AI explanation + limited rerank for recommendation tickets."""

from __future__ import annotations

from typing import Any
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.ai import AIConfig
from app.services.ai.client import decrypt_api_key, response_hash
from app.services.ai.rerank import apply_ai_rerank

PROMPT_VERSION = "v1"


def get_default_ai_config(db: Session) -> AIConfig | None:
    return db.scalar(
        select(AIConfig)
        .where(AIConfig.is_active.is_(True), AIConfig.is_default.is_(True))
        .limit(1)
    ) or db.scalar(select(AIConfig).where(AIConfig.is_active.is_(True)).limit(1))


def _build_prompt(
    *,
    lottery_type: str,
    target_issue: str,
    tickets: list[dict[str, Any]],
) -> tuple[str, str]:
    system = (
        "You are LottoPilot's analysis assistant. "
        "You only explain statistical lottery candidates. "
        "Never promise winning. Return strict JSON only."
    )
    compact = []
    for t in tickets:
        compact.append(
            {
                "rank": t["rank"],
                "primary_numbers": t["primary_numbers"],
                "secondary_numbers": t["secondary_numbers"],
                "statistical_score": t["statistical_score"],
                "tags": t.get("tags") or [],
                "feature_summary": {
                    k: t.get("feature_summary", {}).get(k)
                    for k in (
                        "number_score",
                        "structure_score",
                        "temporal_stability_score",
                        "cooccurrence_score",
                        "extreme_penalty",
                    )
                },
            }
        )
    user = {
        "task": "score_and_explain",
        "lottery_type": lottery_type,
        "target_issue": target_issue,
        "constraints": {
            "ai_weight_cap": 0.10,
            "must_return_json": True,
            "no_win_promise": True,
        },
        "tickets": compact,
        "output_schema": {
            "items": [
                {
                    "rank": "int",
                    "ai_score": "float 0-100",
                    "explanation": "short Chinese explanation without win promise",
                }
            ]
        },
    }
    return system, json.dumps(user, ensure_ascii=False)


def _call_chat_json(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int,
    max_tokens: int,
    system: str,
    user: str,
) -> dict[str, Any]:
    import httpx

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"AI HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("AI JSON root must be object")
        return parsed


def maybe_apply_ai(
    db: Session,
    *,
    settings: Settings,
    lottery_type: str,
    target_issue: str,
    tickets: list[dict[str, Any]],
    enable_ai: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply optional AI rerank/explain. Always fails open to pure stats."""
    meta: dict[str, Any] = {
        "ai_status": "skipped",
        "ai_config_id": None,
        "ai_provider": None,
        "ai_model": None,
        "ai_prompt_version": None,
        "ai_response_hash": None,
        "ai_metrics": {},
        "ai_weight": 0.0,
    }
    if not enable_ai:
        return tickets, meta

    cfg = get_default_ai_config(db)
    if cfg is None or not cfg.api_key_encrypted:
        meta["ai_status"] = "skipped"
        meta["ai_metrics"] = {"reason": "no_active_ai_config"}
        return tickets, meta

    try:
        api_key = decrypt_api_key(cfg.api_key_encrypted, settings.app_secret_key)
        system, user = _build_prompt(
            lottery_type=lottery_type,
            target_issue=target_issue,
            tickets=tickets,
        )
        parsed = _call_chat_json(
            base_url=cfg.base_url,
            api_key=api_key,
            model=cfg.model,
            timeout_seconds=cfg.timeout_seconds or settings.ai_default_timeout_seconds,
            max_tokens=cfg.max_tokens or settings.ai_default_max_tokens,
            system=system,
            user=user,
        )
        items = parsed.get("items") or parsed.get("tickets") or []
        ai_scores: dict[str, float] = {}
        explanations: dict[int, str] = {}
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                rank = int(item.get("rank") or 0)
                if rank <= 0:
                    continue
                if item.get("ai_score") is not None:
                    ai_scores[str(rank)] = float(item["ai_score"])
                if item.get("explanation"):
                    explanations[rank] = str(item["explanation"])[:300]

        weight = min(0.10, float(settings.ai_weight_cap))
        # map by rank for apply_ai_rerank
        for t in tickets:
            t["id"] = str(t["rank"])
        reranked = apply_ai_rerank(tickets, ai_scores, ai_weight=weight)
        # reassign ranks by final score and attach explanations
        for idx, t in enumerate(reranked, start=1):
            old_rank = int(t.get("rank") or idx)
            t["rank"] = idx
            if old_rank in explanations:
                t["explanation"] = explanations[old_rank]
            elif not t.get("explanation"):
                t["explanation"] = (
                    f"统计分 {float(t['statistical_score']):.1f}；AI 仅作有限参考，不承诺中奖。"
                )
        meta.update(
            {
                "ai_status": "succeeded",
                "ai_config_id": str(cfg.id),
                "ai_provider": cfg.provider,
                "ai_model": cfg.model,
                "ai_prompt_version": PROMPT_VERSION,
                "ai_response_hash": response_hash(parsed),
                "ai_metrics": {
                    "items": len(items) if isinstance(items, list) else 0,
                    "scored": len(ai_scores),
                    "weight": weight,
                },
                "ai_weight": weight,
            }
        )
        return reranked, meta
    except Exception as exc:  # noqa: BLE001
        meta.update(
            {
                "ai_status": "failed",
                "ai_config_id": str(cfg.id),
                "ai_provider": cfg.provider,
                "ai_model": cfg.model,
                "ai_prompt_version": PROMPT_VERSION,
                "ai_metrics": {"error": str(exc)[:300]},
                "ai_weight": 0.0,
            }
        )
        # fail open: keep statistical ranking
        for t in tickets:
            t["ai_score"] = None
            t["final_score"] = t["statistical_score"]
            if not t.get("explanation"):
                t["explanation"] = (
                    f"统计分 {float(t['statistical_score']):.1f}：AI 不可用，已回退纯统计结果。"
                )
        return tickets, meta
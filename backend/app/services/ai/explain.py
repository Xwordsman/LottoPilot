"""AI explanation helpers (fail-open, pure where possible)."""

from __future__ import annotations

from typing import Any


def build_statistical_explanation(
    *,
    lottery_type: str,
    primary_numbers: list[int],
    secondary_numbers: list[int],
    feature_summary: dict[str, Any] | None = None,
    rank: int | None = None,
) -> str:
    """Deterministic statistical explanation without calling external AI."""
    feature_summary = feature_summary or {}
    p = " ".join(f"{n:02d}" for n in primary_numbers)
    s = " ".join(f"{n:02d}" for n in secondary_numbers)
    parts = [
        f"{lottery_type.upper()} 候选",
        f"主区 {p}",
        f"次区 {s}",
    ]
    if rank is not None:
        parts.insert(1, f"第 {rank} 组")
    if "sum" in feature_summary:
        parts.append(f"和值 {feature_summary['sum']}")
    if "odd_even" in feature_summary:
        parts.append(f"奇偶 {feature_summary['odd_even']}")
    if "span" in feature_summary:
        parts.append(f"跨度 {feature_summary['span']}")
    if "source" in feature_summary:
        parts.append(f"来源 {feature_summary['source']}")
    parts.append("分数为模型评分，不承诺中奖")
    return "；".join(parts)


def merge_ai_explanation(stat_text: str, ai_text: str | None, *, max_len: int = 500) -> str:
    ai_text = (ai_text or "").strip()
    if not ai_text:
        return stat_text[:max_len]
    merged = f"{stat_text}。AI：{ai_text}"
    return merged[:max_len]
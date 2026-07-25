"""Scoring and diversity selection for recommendation tickets."""

from __future__ import annotations

from typing import Any

from app.services.recommendation.features import (
    combination_structure_features,
    historical_structure_baselines,
    normalize_missing_score,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_candidate(
    candidate: dict[str, Any],
    *,
    lottery_type: str,
    primary_stats: dict[int, dict[str, float]],
    secondary_stats: dict[int, dict[str, float]],
    baselines: dict[str, Any],
    config: dict[str, Any],
    latest_primary: set[int] | None = None,
) -> dict[str, Any]:
    primary = candidate["primary_numbers"]
    secondary = candidate["secondary_numbers"]
    structure = combination_structure_features(primary, lottery_type=lottery_type, config=config)

    # number score
    p_scores = []
    max_missing = max((s["missing"] for s in primary_stats.values()), default=1.0) or 1.0
    for n in primary:
        s = primary_stats[n]
        p_scores.append(
            0.4 * s["decay_freq"]
            + 0.3 * s["freq_w30"]
            + 0.2 * normalize_missing_score(s["missing"], max_missing)
            + 0.1 * _clamp01(0.5 + s["trend"])
        )
    s_scores = []
    max_s_missing = max((s["missing"] for s in secondary_stats.values()), default=1.0) or 1.0
    for n in secondary:
        s = secondary_stats[n]
        s_scores.append(
            0.5 * s["decay_freq"]
            + 0.3 * s["freq_w30"]
            + 0.2 * normalize_missing_score(s["missing"], max_s_missing)
        )
    number_score = 0.8 * (sum(p_scores) / len(p_scores)) + 0.2 * (sum(s_scores) / max(1, len(s_scores)))

    # structure score around historical middle band
    sum_p10, sum_p90 = baselines["sum_p10"], baselines["sum_p90"]
    span_p10, span_p90 = baselines["span_p10"], baselines["span_p90"]
    ssum, span = structure["sum"], structure["span"]
    if sum_p90 > sum_p10:
        sum_score = 1.0 if sum_p10 <= ssum <= sum_p90 else max(0.0, 1.0 - abs(ssum - baselines["sum_mean"]) / max(1.0, sum_p90 - sum_p10))
    else:
        sum_score = 0.5
    if span_p90 > span_p10:
        span_score = 1.0 if span_p10 <= span <= span_p90 else max(0.0, 1.0 - abs(span - baselines["span_mean"]) / max(1.0, span_p90 - span_p10))
    else:
        span_score = 0.5
    odd_even_balance = 1.0 - abs(structure["odd"] - structure["even"]) / max(1, len(primary))
    structure_score = 0.45 * sum_score + 0.35 * span_score + 0.20 * odd_even_balance

    # temporal stability: prefer numbers with consistent short/long freq
    stability_vals = []
    for n in primary:
        s = primary_stats[n]
        stability_vals.append(1.0 - min(1.0, abs(s["freq_w30"] - s["freq_w120"]) * 5))
    temporal_stability_score = sum(stability_vals) / max(1, len(stability_vals))

    # weak co-occurrence proxy: average pairwise decay freq product
    co_vals = []
    for i in range(len(primary)):
        for j in range(i + 1, len(primary)):
            co_vals.append(primary_stats[primary[i]]["decay_freq"] * primary_stats[primary[j]]["decay_freq"])
    cooccurrence_score = sum(co_vals) / max(1, len(co_vals))

    # extreme penalty
    extreme = 0.0
    if structure["max_run"] >= 4:
        extreme += 0.4
    if structure["consecutive_pairs"] >= 3:
        extreme += 0.2
    if latest_primary:
        overlap = len(set(primary) & latest_primary)
        if overlap >= 4:
            extreme += 0.3
    extreme_penalty = min(1.0, extreme)

    weights = config["weights"]
    statistical = (
        weights["number_score"] * number_score
        + weights["structure_score"] * structure_score
        + weights["temporal_stability_score"] * temporal_stability_score
        + weights["cooccurrence_score"] * cooccurrence_score
        - weights["extreme_penalty"] * extreme_penalty
    )
    statistical = _clamp01(statistical) * 100.0

    tags = [
        f"source:{candidate.get('source', 'unknown')}",
        f"sum:{structure['sum']}",
        f"span:{structure['span']}",
        f"oe:{structure['odd_even']}",
        f"zone:{structure['zone_pattern']}",
    ]
    return {
        **candidate,
        "statistical_score": round(statistical, 4),
        "feature_summary": {
            "number_score": round(number_score, 4),
            "structure_score": round(structure_score, 4),
            "temporal_stability_score": round(temporal_stability_score, 4),
            "cooccurrence_score": round(cooccurrence_score, 4),
            "extreme_penalty": round(extreme_penalty, 4),
            "structure": structure,
        },
        "tags": tags,
        "explanation": (
            f"统计分 {statistical:.1f}：号码热度/遗漏平衡与结构和值跨度接近历史中位区间。"
        ),
    }


def primary_overlap(a: list[int], b: list[int]) -> int:
    return len(set(a) & set(b))


def select_diverse(
    scored: list[dict[str, Any]],
    *,
    final_count: int,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Select final tickets with MMR + overlap constraints.

    Returns (selected, relax_level).
    """
    if not scored:
        return [], 0

    ordered = sorted(scored, key=lambda x: x["statistical_score"], reverse=True)
    overlap_max = int(config["diversity"]["primary_overlap_max"])
    mmr_lambda = float(config["diversity"]["mmr_lambda"])
    avoid_same_secondary = bool(config["diversity"]["secondary_identical_penalty"])

    for relax in range(0, 4):
        selected: list[dict[str, Any]] = []
        allowed_overlap = overlap_max + relax
        for cand in ordered:
            if len(selected) >= final_count:
                break
            ok = True
            for prev in selected:
                if primary_overlap(cand["primary_numbers"], prev["primary_numbers"]) > allowed_overlap:
                    ok = False
                    break
                if avoid_same_secondary and relax == 0:
                    if cand["secondary_numbers"] == prev["secondary_numbers"]:
                        ok = False
                        break
            if not ok:
                continue
            # MMR gate against already selected
            if selected:
                sim = max(
                    primary_overlap(cand["primary_numbers"], prev["primary_numbers"]) / max(1, len(cand["primary_numbers"]))
                    for prev in selected
                )
                mmr = cand["statistical_score"] / 100.0 - mmr_lambda * sim
                if mmr < 0.05 and relax == 0:
                    continue
            selected.append(cand)
        if len(selected) >= final_count:
            # rank 1..n
            for idx, item in enumerate(selected[:final_count], start=1):
                item["rank"] = idx
                item["final_score"] = item["statistical_score"]
                item["ai_score"] = None
            return selected[:final_count], relax

    # fallback top-N
    top = ordered[:final_count]
    for idx, item in enumerate(top, start=1):
        item["rank"] = idx
        item["final_score"] = item["statistical_score"]
        item["ai_score"] = None
    return top, 3

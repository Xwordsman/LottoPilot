"""Default strategy configuration and helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_STRATEGY_CONFIG: dict[str, Any] = {
    "version": "v1",
    "candidate_count": 20000,
    "final_count": 5,
    "windows": [30, 60, 120, 0],  # 0 means full history
    "lambda_decay": 0.03,
    "sampling": {
        "uniform_ratio": 0.35,
        "weighted_ratio": 0.40,
        "structure_ratio": 0.20,
        "explore_ratio": 0.05,
    },
    "weights": {
        "number_score": 0.40,
        "structure_score": 0.30,
        "temporal_stability_score": 0.20,
        "cooccurrence_score": 0.05,
        "extreme_penalty": 0.05,
    },
    "diversity": {
        "primary_overlap_max": 3,
        "secondary_identical_penalty": True,
        "mmr_lambda": 0.35,
    },
    "zones": {
        "ssq": [[1, 11], [12, 22], [23, 33]],
        "dlt": [[1, 12], [13, 24], [25, 35]],
    },
    "size_split": {
        "ssq": 17,
        "dlt": 18,
    },
}


def merge_strategy_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_STRATEGY_CONFIG)
    if not overrides:
        return cfg

    def _merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                dst[key] = _merge(dst[key], value)
            else:
                dst[key] = value
        return dst

    return _merge(cfg, overrides)

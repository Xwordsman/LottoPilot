"""Deterministic RNG and seed derivation for recommendations."""

from __future__ import annotations

from typing import Sequence
import hashlib
import random


def derive_seed(lottery_type: str, target_issue: str, strategy_version: str) -> int:
    material = f"{lottery_type}:{target_issue}:{strategy_version}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


def snapshot_hash(records: Sequence[tuple[str, str, tuple[int, ...], tuple[int, ...]]]) -> str:
    """Hash a compact draw snapshot for reproducibility metadata."""
    h = hashlib.sha256()
    for issue, draw_date, primary, secondary in records:
        h.update(issue.encode("utf-8"))
        h.update(b"|")
        h.update(draw_date.encode("utf-8"))
        h.update(b"|")
        h.update(",".join(map(str, primary)).encode("utf-8"))
        h.update(b"|")
        h.update(",".join(map(str, secondary)).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()

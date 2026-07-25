"""Deterministic RNG and seed derivation for recommendations."""

from __future__ import annotations

from typing import Sequence
import hashlib
import random

# PostgreSQL BIGINT is signed int64.
_INT64_MAX = (1 << 63) - 1
_INT64_MIN = -(1 << 63)


def normalize_seed(seed: int) -> int:
    """Clamp/mask any seed into signed int64 so DB BigInteger inserts never overflow."""
    value = int(seed)
    if _INT64_MIN <= value <= _INT64_MAX:
        return value
    # Keep determinism while fitting signed BIGINT.
    return value & _INT64_MAX


def derive_seed(lottery_type: str, target_issue: str, strategy_version: str) -> int:
    material = f"{lottery_type}:{target_issue}:{strategy_version}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    # Use 63-bit positive space to stay inside PostgreSQL BIGINT.
    return int.from_bytes(digest[:8], "big", signed=False) & _INT64_MAX


def make_rng(seed: int) -> random.Random:
    return random.Random(normalize_seed(seed))


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

"""Seed helpers must stay within PostgreSQL BIGINT range."""

from __future__ import annotations

from app.services.recommendation.seed import derive_seed, make_rng, normalize_seed

INT64_MAX = (1 << 63) - 1


def test_derive_seed_fits_signed_bigint() -> None:
    seed = derive_seed("ssq", "2026085", "v1")
    assert 0 <= seed <= INT64_MAX
    # Historical bug: unsigned 64-bit seed overflowed PG BIGINT and caused HTTP 500.
    assert seed != 11906637161695582493


def test_normalize_seed_masks_overflow() -> None:
    huge = (1 << 63) + 123
    normalized = normalize_seed(huge)
    assert 0 <= normalized <= INT64_MAX
    assert make_rng(normalized).random() >= 0.0


def test_derive_seed_is_deterministic() -> None:
    a = derive_seed("dlt", "26083", "v1")
    b = derive_seed("dlt", "26083", "v1")
    assert a == b

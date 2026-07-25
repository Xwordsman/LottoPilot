"""AI pipeline unit tests with mocked HTTP and no DB network."""

from __future__ import annotations

from types import SimpleNamespace

from unittest.mock import patch

from app.services.ai.rerank import apply_ai_rerank
from app.services.ai.rerank_pipeline import maybe_apply_ai


class _FakeSettings:
    app_secret_key = "test-secret-key-0123456789"
    ai_default_timeout_seconds = 5
    ai_default_max_tokens = 256
    ai_weight_cap = 0.10


def _tickets() -> list[dict]:
    return [
        {
            "rank": 1,
            "primary_numbers": [1, 2, 3, 4, 5, 6],
            "secondary_numbers": [7],
            "statistical_score": 80.0,
            "final_score": 80.0,
            "feature_summary": {},
            "tags": ["source:weighted"],
            "explanation": "stat",
        },
        {
            "rank": 2,
            "primary_numbers": [2, 4, 6, 8, 10, 12],
            "secondary_numbers": [1],
            "statistical_score": 70.0,
            "final_score": 70.0,
            "feature_summary": {},
            "tags": ["source:uniform"],
            "explanation": "stat",
        },
    ]


def test_apply_ai_weight_cap_again() -> None:
    out = apply_ai_rerank(
        [{"id": "1", "statistical_score": 50.0}],
        {"1": 100.0},
        ai_weight=1.0,
    )
    assert abs(out[0]["final_score"] - (50 * 0.9 + 100 * 0.1)) < 1e-6


def test_maybe_apply_ai_skipped_without_config() -> None:
    class _DB:
        def scalar(self, *_args, **_kwargs):
            return None

    tickets, meta = maybe_apply_ai(
        _DB(),  # type: ignore[arg-type]
        settings=_FakeSettings(),  # type: ignore[arg-type]
        lottery_type="ssq",
        target_issue="2026001",
        tickets=_tickets(),
        enable_ai=True,
    )
    assert meta["ai_status"] == "skipped"
    assert tickets[0]["statistical_score"] == 80.0


def test_maybe_apply_ai_fail_open_on_error() -> None:
    cfg = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        provider="openai_compatible",
        base_url="https://example.invalid/v1",
        model="demo",
        api_key_encrypted="cipher",
        timeout_seconds=5,
        max_tokens=128,
    )

    class _DB:
        def scalar(self, *_args, **_kwargs):
            return cfg

    with (
        patch("app.services.ai.rerank_pipeline.decrypt_api_key", return_value="sk-test"),
        patch(
            "app.services.ai.rerank_pipeline._call_chat_json",
            side_effect=RuntimeError("boom"),
        ),
    ):
        tickets, meta = maybe_apply_ai(
            _DB(),  # type: ignore[arg-type]
            settings=_FakeSettings(),  # type: ignore[arg-type]
            lottery_type="ssq",
            target_issue="2026001",
            tickets=_tickets(),
            enable_ai=True,
        )
    assert meta["ai_status"] == "failed"
    assert meta["ai_weight"] == 0.0
    assert tickets[0]["final_score"] == tickets[0]["statistical_score"]
    assert tickets[0]["ai_score"] is None


def test_maybe_apply_ai_success_rerank() -> None:
    cfg = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000002",
        provider="openai_compatible",
        base_url="https://example.invalid/v1",
        model="demo",
        api_key_encrypted="cipher",
        timeout_seconds=5,
        max_tokens=128,
    )

    class _DB:
        def scalar(self, *_args, **_kwargs):
            return cfg

    payload = {
        "items": [
            {"rank": 1, "ai_score": 0.0, "explanation": "解释1，不承诺中奖"},
            {"rank": 2, "ai_score": 100.0, "explanation": "解释2，不承诺中奖"},
        ]
    }
    with (
        patch("app.services.ai.rerank_pipeline.decrypt_api_key", return_value="sk-test"),
        patch("app.services.ai.rerank_pipeline._call_chat_json", return_value=payload),
    ):
        tickets, meta = maybe_apply_ai(
            _DB(),  # type: ignore[arg-type]
            settings=_FakeSettings(),  # type: ignore[arg-type]
            lottery_type="ssq",
            target_issue="2026001",
            tickets=_tickets(),
            enable_ai=True,
        )
    assert meta["ai_status"] == "succeeded"
    assert meta["ai_weight"] == 0.10
    # rank2 has higher AI score so final order should flip after limited weight
    assert tickets[0]["primary_numbers"] == [2, 4, 6, 8, 10, 12]
    assert tickets[0]["explanation"].startswith("解释2")
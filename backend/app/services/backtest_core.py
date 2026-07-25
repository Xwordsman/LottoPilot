"""Pure walk-forward helpers without database dependencies."""

from __future__ import annotations

from typing import Any, Sequence


def validate_backtest_window(
    issues: Sequence[str],
    start_issue: str,
    end_issue: str,
    *,
    min_history: int = 10,
    min_training: int = 5,
) -> tuple[int, int]:
    """Validate start/end indices for walk-forward backtest.

    Returns (start_idx, end_idx) in chronological order.
    """
    if len(issues) < min_history:
        raise ValueError("INSUFFICIENT_HISTORY")
    try:
        start_idx = list(issues).index(start_issue)
        end_idx = list(issues).index(end_issue)
    except ValueError as exc:
        raise ValueError("ISSUE_NOT_FOUND") from exc
    if start_idx >= end_idx:
        raise ValueError("INVALID_RANGE")
    if start_idx < min_training:
        raise ValueError("INSUFFICIENT_TRAINING")
    return start_idx, end_idx


def train_slice_before_target(history_chrono: Sequence[Any], target_idx: int) -> list[Any]:
    """Return training history for target_idx, newest-first, excluding target and future."""
    if target_idx <= 0:
        return []
    return list(reversed(list(history_chrono[:target_idx])))


def assert_no_future_leak(
    train_newest_first: Sequence[Any],
    target: Any,
    *,
    issue_attr: str = "issue",
) -> None:
    """Raise if training set contains target or any issue after target when comparable."""
    target_issue = getattr(target, issue_attr, target)
    for item in train_newest_first:
        issue = getattr(item, issue_attr, item)
        if issue == target_issue:
            raise ValueError("FUTURE_LEAK: target issue present in training set")
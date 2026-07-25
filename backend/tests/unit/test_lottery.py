"""Unit tests for lottery validation."""

from __future__ import annotations

import pytest

from app.core.errors import ValidationAppError
from app.utils.lottery import validate_ticket_numbers


def test_validate_ssq_ok() -> None:
    primary, secondary = validate_ticket_numbers("ssq", [3, 1, 8, 12, 20, 33], [7])
    assert primary == [1, 3, 8, 12, 20, 33]
    assert secondary == [7]


def test_validate_dlt_ok() -> None:
    primary, secondary = validate_ticket_numbers("dlt", [2, 5, 11, 20, 35], [1, 12])
    assert primary == [2, 5, 11, 20, 35]
    assert secondary == [1, 12]


def test_validate_ssq_wrong_count() -> None:
    with pytest.raises(ValidationAppError) as exc:
        validate_ticket_numbers("ssq", [1, 2, 3, 4, 5], [1])
    assert exc.value.code == "DRAW_VALIDATION_FAILED"


def test_validate_duplicate_primary() -> None:
    with pytest.raises(ValidationAppError):
        validate_ticket_numbers("ssq", [1, 1, 2, 3, 4, 5], [1])


def test_validate_out_of_range() -> None:
    with pytest.raises(ValidationAppError):
        validate_ticket_numbers("dlt", [1, 2, 3, 4, 36], [1, 2])

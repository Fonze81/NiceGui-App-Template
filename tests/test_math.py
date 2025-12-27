from __future__ import annotations

from nicegui_app_template.app import add


def test_add_two_positive_numbers() -> None:
    """Valida a soma de dois números positivos."""
    assert add(2, 3) == 5


def test_add_with_zero() -> None:
    """Valida soma com zero."""
    assert add(5, 0) == 5


def test_add_negative_numbers() -> None:
    """Valida soma de números negativos."""
    assert add(-2, -3) == -5

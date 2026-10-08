"""HTTP error message mapping."""

from __future__ import annotations

from errors import map_http_status_to_message


def test_422_includes_detail() -> None:
    m = map_http_status_to_message(422, "bad field")
    assert "422" in m or "Invalid parameters" in m
    assert "bad field" in m


def test_422_domain_error_does_not_blame_the_input() -> None:
    m = map_http_status_to_message(
        422, "Sunrise could not be calculated (polar night)", "sun_calculation_failed"
    )
    assert "polar night" in m
    assert "Fix the field" not in m


def test_422_input_error_keeps_the_fix_hint() -> None:
    m = map_http_status_to_message(422, "date: invalid", "validation_error")
    assert "Fix the field" in m


def test_unknown_status_with_detail() -> None:
    m = map_http_status_to_message(418, "teapot")
    assert "418" in m
    assert "teapot" in m


def test_unknown_status_no_detail() -> None:
    m = map_http_status_to_message(418, None)
    assert "418" in m

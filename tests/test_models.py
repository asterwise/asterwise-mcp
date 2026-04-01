"""Tests for Pydantic input models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import AyanamsaType, BirthData


def test_valid_birth_data() -> None:
    b = BirthData(
        date="1985-11-12",
        time="06:45",
        lat=19.0760,
        lon=72.8777,
    )
    assert b.ayanamsa == AyanamsaType.LAHIRI


def test_invalid_date_format() -> None:
    with pytest.raises(ValidationError):
        BirthData(date="12-11-1985", time="06:45", lat=19.07, lon=72.87)


def test_invalid_time_format() -> None:
    with pytest.raises(ValidationError):
        BirthData(date="1985-11-12", time="6:45am", lat=19.07, lon=72.87)


def test_lat_out_of_range() -> None:
    with pytest.raises(ValidationError):
        BirthData(date="1985-11-12", time="06:45", lat=91.0, lon=72.87)


def test_invalid_ayanamsa() -> None:
    with pytest.raises(ValidationError):
        BirthData.model_validate(
            {
                "date": "1985-11-12",
                "time": "06:45",
                "lat": 19.07,
                "lon": 72.87,
                "ayanamsa": "made_up",
            }
        )


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        BirthData.model_validate(
            {
                "date": "1985-11-12",
                "time": "06:45",
                "lat": 19.07,
                "lon": 72.87,
                "unknown_field": "value",
            }
        )

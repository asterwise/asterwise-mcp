"""Strict Pydantic models: BirthData, LocationInput."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    AyanamsaType,
    BirthData,
    HouseSystem,
    LocationInput,
    WesternBirthData,
)


class TestBirthData:
    def test_valid_birth_data(self) -> None:
        b = BirthData(
            date="1985-11-12",
            time="06:45",
            lat=19.0760,
            lon=72.8777,
        )
        assert b.ayanamsa == AyanamsaType.LAHIRI
        assert b.date == "1985-11-12"

    def test_default_ayanamsa_is_lahiri(self) -> None:
        b = BirthData(date="1985-11-12", time="06:45", lat=0.0, lon=0.0)
        assert b.ayanamsa == AyanamsaType.LAHIRI

    def test_all_ayanamsas_accepted(self) -> None:
        for ayanamsa in ("lahiri", "kp", "raman", "tropical"):
            b = BirthData(
                date="1985-11-12",
                time="06:45",
                lat=0.0,
                lon=0.0,
                ayanamsa=ayanamsa,
            )
            assert b.ayanamsa.value == ayanamsa

    def test_invalid_date_format_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            BirthData(date="12-11-1985", time="06:45", lat=0.0, lon=0.0)
        msg = str(exc.value)
        assert "date" in msg and ("pattern" in msg.lower() or "YYYY-MM-DD" in msg)

    def test_invalid_time_format_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            BirthData(date="1985-11-12", time="6:45am", lat=0.0, lon=0.0)
        assert "HH:MM" in str(exc.value) or "String should match pattern" in str(exc.value)

    def test_lat_too_high_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BirthData(date="1985-11-12", time="06:45", lat=91.0, lon=0.0)

    def test_lat_too_low_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BirthData(date="1985-11-12", time="06:45", lat=-91.0, lon=0.0)

    def test_lon_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BirthData(date="1985-11-12", time="06:45", lat=0.0, lon=181.0)

    def test_invalid_ayanamsa_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BirthData(
                date="1985-11-12",
                time="06:45",
                lat=0.0,
                lon=0.0,
                ayanamsa="not_valid",
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BirthData(
                date="1985-11-12",
                time="06:45",
                lat=0.0,
                lon=0.0,
                unknown="value",
            )

    def test_to_api_dict(self) -> None:
        b = BirthData(
            date="1985-11-12",
            time="06:45",
            lat=19.07,
            lon=72.87,
            person_name="Test Person",
            timezone="Asia/Kolkata",
        )
        d = b.to_api_dict()
        assert d == {
            "name": "Test Person",
            "date": "1985-11-12",
            "time": "06:45",
            "latitude": 19.07,
            "longitude": 72.87,
            "timezone": "Asia/Kolkata",
            "ayanamsa": "lahiri",
        }

    def test_birth_data_default_name_and_timezone(self) -> None:
        b = BirthData(date="1985-11-12", time="06:45", lat=0.0, lon=0.0)
        d = b.to_api_dict()
        assert d["name"] == "Chart"
        assert d["timezone"] == "Asia/Kolkata"

    def test_year_before_1800_rejected(self) -> None:
        with pytest.raises(ValidationError, match="1800 or later"):
            BirthData(date="1799-01-01", time="06:45", lat=0.0, lon=0.0)

    def test_whitespace_stripped_from_strings(self) -> None:
        b = BirthData(date="1985-11-12 ", time=" 06:45", lat=0.0, lon=0.0)
        assert b.date == "1985-11-12"
        assert b.time == "06:45"

    def test_to_api_dict_omits_time_when_none(self) -> None:
        b = BirthData(date="1985-11-12", lat=0.0, lon=0.0)
        assert b.time is None
        d = b.to_api_dict()
        assert "time" not in d

    def test_to_api_dict_includes_time_when_set(self) -> None:
        b = BirthData(date="1985-11-12", time="06:45", lat=0.0, lon=0.0)
        d = b.to_api_dict()
        assert d["time"] == "06:45"


class TestWesternBirthData:
    def test_valid_defaults(self) -> None:
        b = WesternBirthData(
            date="1985-11-12",
            time="06:45",
            lat=40.7128,
            lon=-74.0060,
        )
        assert b.house_system == HouseSystem.PLACIDUS
        assert b.timezone == "UTC"
        assert b.person_name == "Chart"

    def test_to_api_dict(self) -> None:
        b = WesternBirthData(
            date="1985-11-12",
            time="06:45",
            lat=40.0,
            lon=-74.0,
            person_name="Alex",
            timezone="America/New_York",
            house_system=HouseSystem.WHOLE_SIGN,
        )
        d = b.to_api_dict()
        assert d == {
            "name": "Alex",
            "date": "1985-11-12",
            "time": "06:45",
            "latitude": 40.0,
            "longitude": -74.0,
            "timezone": "America/New_York",
            "house_system": "whole_sign",
        }

    def test_to_api_dict_no_house(self) -> None:
        b = WesternBirthData(date="1985-11-12", time="06:45", lat=0.0, lon=0.0)
        d = b.to_api_dict_no_house()
        assert "house_system" not in d
        assert d["name"] == "Chart"

    def test_invalid_date_validator(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            WesternBirthData(date="1985-13-40", time="06:45", lat=0.0, lon=0.0)

    def test_year_before_1800_rejected(self) -> None:
        with pytest.raises(ValidationError, match="1800 or later"):
            WesternBirthData(date="1799-01-01", time="06:45", lat=0.0, lon=0.0)

    def test_invalid_time_validator(self) -> None:
        with pytest.raises(ValidationError, match="HH:MM"):
            WesternBirthData(date="1985-11-12", time="25:70", lat=0.0, lon=0.0)

    def test_coord_bounds(self) -> None:
        with pytest.raises(ValidationError):
            WesternBirthData(date="1985-11-12", time="06:45", lat=91.0, lon=0.0)
        with pytest.raises(ValidationError):
            WesternBirthData(date="1985-11-12", time="06:45", lat=0.0, lon=181.0)

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WesternBirthData(
                date="1985-11-12",
                time="06:45",
                lat=0.0,
                lon=0.0,
                ayanamsa="lahiri",
            )

    def test_all_house_systems(self) -> None:
        for hs in HouseSystem:
            b = WesternBirthData(
                date="1985-11-12",
                time="06:45",
                lat=0.0,
                lon=0.0,
                house_system=hs,
            )
            assert b.to_api_dict()["house_system"] == hs.value


class TestLocationInput:
    def test_valid(self) -> None:
        loc = LocationInput(date="2020-01-15", lat=19.0, lon=72.0)
        assert loc.date == "2020-01-15"
        assert loc.timezone == "Asia/Kolkata"

    def test_location_timezone_override(self) -> None:
        loc = LocationInput(
            date="2020-01-15", lat=19.0, lon=72.0, timezone="America/New_York"
        )
        assert loc.timezone == "America/New_York"

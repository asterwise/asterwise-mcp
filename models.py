"""Strict Pydantic input models for Asterwise MCP tools."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AyanamsaType(str, Enum):
    LAHIRI = "lahiri"
    KP = "kp"
    RAMAN = "raman"
    TROPICAL = "tropical"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class BirthData(BaseModel):
    """Birth data for a single person."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    date: str = Field(
        ...,
        description=(
            "Birth date in YYYY-MM-DD format. Example: '1985-11-12'"
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    time: str = Field(
        ...,
        description=(
            "Birth time in HH:MM format (24-hour). Example: '06:45'. Use '00:00' if unknown."
        ),
        pattern=r"^\d{2}:\d{2}$",
    )
    lat: float = Field(
        ...,
        description=(
            "Birth latitude in decimal degrees. North positive, south negative. "
            "Example: 19.0760 for Mumbai, -33.8688 for Sydney"
        ),
        ge=-90.0,
        le=90.0,
    )
    lon: float = Field(
        ...,
        description=(
            "Birth longitude in decimal degrees. East positive, west negative. "
            "Example: 72.8777 for Mumbai, -74.0060 for New York"
        ),
        ge=-180.0,
        le=180.0,
    )
    person_name: str = Field(
        default="Chart",
        description=(
            "Name of the person for this chart. "
            "Example: 'Arjun Mehta'"
        ),
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description=(
            "IANA timezone for the birth location. "
            "Examples: 'Asia/Kolkata' (India), "
            "'America/New_York' (New York), "
            "'Europe/London' (London), "
            "'Asia/Tokyo' (Japan), "
            "'America/Los_Angeles' (Los Angeles), "
            "'Europe/Paris' (Paris), "
            "'Asia/Dubai' (Dubai), "
            "'Asia/Singapore' (Singapore), "
            "'America/Chicago' (Chicago), "
            "'Australia/Sydney' (Sydney). "
            "Default: Asia/Kolkata"
        ),
    )
    ayanamsa: AyanamsaType = Field(
        default=AyanamsaType.LAHIRI,
        description=(
            "Ayanamsa system for sidereal calculations. "
            "'lahiri' (default, recommended for Vedic), "
            "'kp' (Krishnamurti Paddhati), 'raman', 'tropical' (Western)"
        ),
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"date must be YYYY-MM-DD. Got: {v!r}. Example: '1985-11-12'"
            ) from None
        parsed_d = parsed.date()
        if parsed_d.year < 1800:
            raise ValueError(f"date year must be 1800 or later. Got: {parsed_d.year}")
        latest = date.today() + timedelta(days=365)
        if parsed_d > latest:
            raise ValueError(
                "date cannot be more than one year in the future relative to today"
            )
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(
                f"time must be HH:MM in 24-hour format. Got: {v!r}. "
                "Example: '06:45', '14:30', '00:00'"
            ) from None
        return v

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to the dict format the Asterwise API expects."""
        return {
            "name": self.person_name,
            "date": self.date,
            "time": self.time,
            "latitude": self.lat,
            "longitude": self.lon,
            "timezone": self.timezone,
            "ayanamsa": self.ayanamsa.value,
        }


class LocationInput(BaseModel):
    """For tools that need location but not birth time."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date in YYYY-MM-DD format",
    )
    lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees",
    )
    lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description="IANA timezone for the location.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD. Got: {v!r}") from None
        return v


class PanchangaCalendarInput(BaseModel):
    """Monthly Panchanga calendar parameters."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class PrashnaInput(BaseModel):
    """Prashna (horary) query parameters."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    question: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    ayanamsa: AyanamsaType = Field(default=AyanamsaType.LAHIRI)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format. Got: {v!r}") from None
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"time must be HH:MM format (24h). Got: {v!r}") from None
        return v


class DivisionalChartType(str, Enum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D7 = "D7"
    D9 = "D9"
    D10 = "D10"
    D12 = "D12"
    D16 = "D16"
    D20 = "D20"
    D24 = "D24"
    D27 = "D27"
    D30 = "D30"
    D40 = "D40"
    D45 = "D45"
    D60 = "D60"


class HoroscopePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


def birth_dict(b: BirthData) -> dict[str, Any]:
    """Serialize BirthData for JSON request bodies."""
    return b.to_api_dict()


def prashna_dict(p: PrashnaInput) -> dict[str, Any]:
    """Serialize PrashnaInput for the API (BirthInput-style location + question)."""
    return {
        "latitude": p.lat,
        "longitude": p.lon,
        "question": p.question,
        "ayanamsa": p.ayanamsa.value,
    }

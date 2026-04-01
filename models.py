"""Shared Pydantic input models for Asterwise MCP tools."""

from __future__ import annotations

from datetime import datetime
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

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

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
            "Birth time in HH:MM format (24h). Example: '06:45'"
        ),
        pattern=r"^\d{2}:\d{2}$",
    )
    lat: float = Field(
        ...,
        description="Birth latitude. Example: 19.0760 for Mumbai",
        ge=-90.0,
        le=90.0,
    )
    lon: float = Field(
        ...,
        description="Birth longitude. Example: 72.8777 for Mumbai",
        ge=-180.0,
        le=180.0,
    )
    ayanamsa: AyanamsaType = Field(
        default=AyanamsaType.LAHIRI,
        description=(
            "Ayanamsa system: 'lahiri' (default), 'kp', 'raman', 'tropical'"
        ),
    )

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


class LocationInput(BaseModel):
    """Date + geolocation for Panchanga and similar tools (not full birth time)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    date: str = Field(
        ...,
        description="Date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description='Response format: "markdown" or "json"',
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format. Got: {v!r}") from None
        return v


class PanchangaCalendarInput(BaseModel):
    """Monthly Panchanga calendar parameters."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class PrashnaInput(BaseModel):
    """Prashna (horary) query parameters."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

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
    return b.model_dump(mode="json")


def prashna_dict(p: PrashnaInput) -> dict[str, Any]:
    """Serialize PrashnaInput for the API."""
    d = p.model_dump(mode="json")
    d.pop("response_format", None)
    return d

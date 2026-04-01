"""Shared Pydantic input models for Asterwise MCP tools."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    ayanamsa: str = Field(
        default="lahiri",
        description=(
            "Ayanamsa system. Options: 'lahiri' (default, recommended for Vedic), "
            "'kp', 'raman', 'tropical'"
        ),
    )


class AyanamsaType(str, Enum):
    LAHIRI = "lahiri"
    KP = "kp"
    RAMAN = "raman"
    TROPICAL = "tropical"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


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


def birth_dict(b: BirthData) -> dict[str, str | float]:
    """Serialize BirthData for JSON request bodies."""
    return b.model_dump()

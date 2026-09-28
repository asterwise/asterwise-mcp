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


class HouseSystem(str, Enum):
    PLACIDUS = "placidus"
    KOCH = "koch"
    EQUAL = "equal"
    WHOLE_SIGN = "whole_sign"


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
        description="Birth date YYYY-MM-DD.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    time: str | None = Field(
        default=None,
        description=(
            "Birth time HH:MM (24h), e.g. '06:45'. Omit if unknown (a sunrise chart is "
            "used and birth_time_provided=false); never pass '00:00' for unknown."
        ),
        pattern=r"^\d{2}:\d{2}$",
    )
    lat: float = Field(
        ...,
        description="Latitude in decimal degrees, north positive (Mumbai 19.076).",
        ge=-90.0,
        le=90.0,
    )
    lon: float = Field(
        ...,
        description="Longitude in decimal degrees, east positive (Mumbai 72.8777).",
        ge=-180.0,
        le=180.0,
    )
    person_name: str = Field(
        default="Chart",
        description="Person's name, used in labels only.",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description=(
            "IANA timezone of the birth place, e.g. 'Asia/Kolkata', 'America/New_York', "
            "'Europe/London'. Default: Asia/Kolkata"
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
    def validate_time(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(
                f"time must be HH:MM in 24-hour format. Got: {v!r}. "
                "Example: '06:45', '14:30'"
            ) from None
        return v

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to the dict format the Asterwise API expects."""
        payload: dict[str, Any] = {
            "name": self.person_name,
            "date": self.date,
            "latitude": self.lat,
            "longitude": self.lon,
            "timezone": self.timezone,
            "ayanamsa": self.ayanamsa.value,
        }
        if self.time is not None:
            payload["time"] = self.time
        return payload


class WesternBirthData(BaseModel):
    """Birth data for Western astrology tools (tropical zodiac)."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    date: str = Field(
        ...,
        description="Birth date in YYYY-MM-DD format. Example: '1985-11-12'",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    time: str = Field(
        ...,
        description="Birth time in HH:MM format (24-hour). Example: '06:45'",
        pattern=r"^\d{2}:\d{2}$",
    )
    lat: float = Field(..., ge=-90.0, le=90.0,
        description="Birth latitude in decimal degrees. North positive.")
    lon: float = Field(..., ge=-180.0, le=180.0,
        description="Birth longitude in decimal degrees. East positive.")
    person_name: str = Field(
        default="Chart",
        description="Name of the person. Example: 'Arjun Mehta'",
    )
    timezone: str = Field(
        default="UTC",
        description=(
            "IANA timezone. Examples: 'Asia/Kolkata', 'America/New_York', "
            "'Europe/Rome', 'UTC'. Default: UTC"
        ),
    )
    house_system: HouseSystem = Field(
        default=HouseSystem.PLACIDUS,
        description=(
            "House system for Western chart. "
            "'placidus' (default, most common), "
            "'koch', 'equal', 'whole_sign'"
        ),
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"date must be YYYY-MM-DD. Got: {v!r}"
            ) from None
        if parsed.year < 1800:
            raise ValueError(f"date year must be 1800 or later.")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(
                f"time must be HH:MM in 24-hour format. Got: {v!r}"
            ) from None
        return v

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "name": self.person_name,
            "date": self.date,
            "time": self.time,
            "latitude": self.lat,
            "longitude": self.lon,
            "timezone": self.timezone,
            "house_system": self.house_system.value,
        }

    def to_api_dict_no_house(self) -> dict[str, Any]:
        """For endpoints that don't take house_system."""
        d = self.to_api_dict()
        d.pop("house_system", None)
        return d


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

    year: int = Field(..., ge=1900, le=2100, description="Calendar year, 1900-2100.")
    month: int = Field(..., ge=1, le=12, description="Month number 1-12.")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees, north positive.")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees, east positive.")
    timezone: str = Field(
        default="Asia/Kolkata",
        description="IANA timezone of the location, e.g. 'America/New_York'. Default: Asia/Kolkata.",
    )
    ayanamsa: AyanamsaType = Field(default=AyanamsaType.LAHIRI, description="Ayanamsa for nakshatra and yoga.")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class MuhurtaActivity(str, Enum):
    MARRIAGE = "marriage"
    GRIHA_PRAVESH = "griha_pravesh"
    BUSINESS = "business"
    TRAVEL = "travel"
    NAMING_CEREMONY = "naming_ceremony"
    VEHICLE_PURCHASE = "vehicle_purchase"
    PROPERTY_PURCHASE = "property_purchase"
    MUNDAN = "mundan"
    ANNAPRASHAN = "annaprashan"
    UPANAYANA = "upanayana"
    VIDYARAMBHA = "vidyarambha"


class MuhurtaParticipantInput(BaseModel):
    """A person whose Tarabala and Chandrabala must be favourable (e.g. bride or groom)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    label: str | None = Field(default=None, description="Name shown in the output, e.g. 'Bride'.")
    nakshatra: str | None = Field(
        default=None, description="Janma nakshatra name, e.g. 'Rohini'. Or give the birth fields instead."
    )
    moon_rashi: str | None = Field(
        default=None, description="Janma rashi (Moon sign), e.g. 'Vrishabha' or 'Taurus'. Optional with nakshatra."
    )
    birth_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Birth date YYYY-MM-DD.")
    birth_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$", description="Birth time HH:MM (24h).")
    birth_lat: float | None = Field(default=None, ge=-90.0, le=90.0, description="Birth latitude.")
    birth_lon: float | None = Field(default=None, ge=-180.0, le=180.0, description="Birth longitude.")
    birth_timezone: str | None = Field(default=None, description="IANA timezone of the birth place.")

    def to_api_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.label:
            out["label"] = self.label
        if self.nakshatra:
            out["nakshatra"] = self.nakshatra
            if self.moon_rashi:
                out["moon_rashi"] = self.moon_rashi
            return out
        out.update({
            "birth_date": self.birth_date,
            "birth_time": self.birth_time,
            "birth_latitude": self.birth_lat,
            "birth_longitude": self.birth_lon,
            "birth_timezone": self.birth_timezone,
        })
        return out


class MuhurtaInput(BaseModel):
    """Muhurta search parameters."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    activity: MuhurtaActivity = Field(..., description="Activity to find a muhurta for.")
    from_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start of the search, YYYY-MM-DD (inclusive).")
    to_date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="End of the search, YYYY-MM-DD (inclusive), at most 366 days after from_date.",
    )
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees, north positive.")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees, east positive.")
    timezone: str = Field(default="Asia/Kolkata", description="IANA timezone of the location.")
    ayanamsa: AyanamsaType = Field(default=AyanamsaType.LAHIRI, description="Ayanamsa for nakshatra and lagna.")
    top_n: int = Field(default=5, ge=1, le=50, description="Number of windows to return (1-50).")
    max_windows_per_day: int = Field(
        default=1, ge=1, le=10, description="At most this many windows per day, so results spread across dates."
    )
    participants: list[MuhurtaParticipantInput] | None = Field(
        default=None,
        max_length=2,
        description="Up to two people; adds Tarabala and Chandrabala (Naidhana or the 8th-house Moon rule a moment out).",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    def to_api_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "event_type": self.activity.value,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "latitude": self.lat,
            "longitude": self.lon,
            "timezone": self.timezone,
            "ayanamsa": self.ayanamsa.value,
            "top_n": self.top_n,
            "max_windows_per_day": self.max_windows_per_day,
        }
        if self.participants:
            body["participants"] = [p.to_api_dict() for p in self.participants]
        return body


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

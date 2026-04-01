"""Panchanga, muhurta, and timing tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from client import get_client
from models import ResponseFormat
from runtime import (
    STANDARD_ANNOTATIONS,
    format_tool_result,
    mcp_error_message,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_panchanga",
        description=(
            "Panchanga — Tithi, Vara, Nakshatra, Yoga, Karana for a date and location (fresh computation). "
            "Source: classical Panchanga rules.\n"
            "Inputs: date (YYYY-MM-DD), lat, lon, response_format.\n"
            "Returns: All five elements with timings as provided by the API."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_panchanga(
        date: str,
        lat: float,
        lon: float,
        response_format: ResponseFormat,
    ) -> str:
        """Daily Panchanga."""
        try:
            api_key = await require_api_key()
            body = {"date": date, "lat": lat, "lon": lon}
            data = await get_client().post("/v1/astro/panchanga", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Panchanga", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_choghadiya",
        description=(
            "Choghadiya muhurta slots for a day and location. Source: Muhurta tradition.\n"
            "Inputs: date, lat, lon, response_format.\n"
            "Returns: Day and night Choghadiya periods."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_choghadiya(
        date: str,
        lat: float,
        lon: float,
        response_format: ResponseFormat,
    ) -> str:
        """Choghadiya."""
        try:
            api_key = await require_api_key()
            body = {"date": date, "lat": lat, "lon": lon}
            data = await get_client().post("/v1/astro/panchanga/choghadiya", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Choghadiya", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_hora",
        description=(
            "Planetary Hora rulers for each hour of the day. Source: Hora shastra.\n"
            "Inputs: date, lat, lon, response_format.\n"
            "Returns: Hourly rulers."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_hora(
        date: str,
        lat: float,
        lon: float,
        response_format: ResponseFormat,
    ) -> str:
        """Hora table."""
        try:
            api_key = await require_api_key()
            body = {"date": date, "lat": lat, "lon": lon}
            data = await get_client().post("/v1/astro/panchanga/hora", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Hora", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_rahu_kaal",
        description=(
            "Rahu Kaal — daily inauspicious window ruled by Rahu. Source: Muhurta texts.\n"
            "Inputs: date, lat, lon, response_format.\n"
            "Returns: Start/end times."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_rahu_kaal(
        date: str,
        lat: float,
        lon: float,
        response_format: ResponseFormat,
    ) -> str:
        """Rahu Kaal."""
        try:
            api_key = await require_api_key()
            body = {"date": date, "lat": lat, "lon": lon}
            data = await get_client().post("/v1/astro/panchanga/rahu-kaal", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Rahu Kaal", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_muhurta",
        description=(
            "Auspicious muhurta (electional timing) for a given activity on a date. Source: Muhurta "
            "classics.\n"
            "Inputs: date, lat, lon, activity (e.g. marriage, business), response_format.\n"
            "Returns: Recommended windows."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_muhurta(
        date: str,
        lat: float,
        lon: float,
        activity: str,
        response_format: ResponseFormat,
    ) -> str:
        """Activity-specific muhurta."""
        try:
            api_key = await require_api_key()
            body = {"date": date, "lat": lat, "lon": lon, "activity": activity}
            data = await get_client().post("/v1/astro/muhurta", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Muhurta — {activity}", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_panchanga_calendar",
        description=(
            "Monthly Panchanga calendar — Tithi, Nakshatra, and key dates. Source: Panchanga computation.\n"
            "Inputs: year, month, lat, lon, response_format.\n"
            "Returns: Month-level calendar data."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_panchanga_calendar(
        year: int,
        month: int,
        lat: float,
        lon: float,
        response_format: ResponseFormat,
    ) -> str:
        """Panchanga calendar month."""
        try:
            api_key = await require_api_key()
            params: dict[str, Any] = {
                "year": year,
                "month": month,
                "lat": lat,
                "lon": lon,
            }
            data = await get_client().get(
                "/v1/astro/panchanga/calendar", api_key, params
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Panchanga calendar {year}-{month:02d}", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

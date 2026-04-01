"""Panchanga, muhurta, and timing tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import LocationInput, PanchangaCalendarInput
from runtime import (
    STANDARD_ANNOTATIONS,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_panchanga",
        description=(
            "Panchanga — Tithi, Vara, Nakshatra, Yoga, Karana for a date and location (fresh computation). "
            "Source: classical Panchanga rules.\n"
            "Inputs: LocationInput (date, lat, lon, response_format).\n"
            "Returns: All five elements with timings as provided by the API."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_panchanga(
        ctx: Context,
        location: LocationInput
    ) -> str:
        """Daily Panchanga."""
        try:
            api_key = await require_api_key(ctx)
            body = {"date": location.date, "lat": location.lat, "lon": location.lon}
            rf = location.response_format
            data = await get_client().post("/v1/astro/panchanga", api_key, body, timeout=10.0)
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Panchanga", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_panchanga", exc)

    @mcp.tool(
        name="asterwise_get_choghadiya",
        description=(
            "Choghadiya muhurta slots for a day and location. Source: Muhurta tradition.\n"
            "Inputs: LocationInput.\n"
            "Returns: Day and night Choghadiya periods."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_choghadiya(
        ctx: Context,
        location: LocationInput
    ) -> str:
        """Choghadiya."""
        try:
            api_key = await require_api_key(ctx)
            body = {"date": location.date, "lat": location.lat, "lon": location.lon}
            rf = location.response_format
            data = await get_client().post("/v1/astro/panchanga/choghadiya", api_key, body, timeout=10.0)
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Choghadiya", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_choghadiya", exc)

    @mcp.tool(
        name="asterwise_get_hora",
        description=(
            "Planetary Hora rulers for each hour of the day. Source: Hora shastra.\n"
            "Inputs: LocationInput.\n"
            "Returns: Hourly rulers."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_hora(
        ctx: Context,
        location: LocationInput
    ) -> str:
        """Hora table."""
        try:
            api_key = await require_api_key(ctx)
            body = {"date": location.date, "lat": location.lat, "lon": location.lon}
            rf = location.response_format
            data = await get_client().post("/v1/astro/panchanga/hora", api_key, body, timeout=10.0)
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Hora", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_hora", exc)

    @mcp.tool(
        name="asterwise_get_rahu_kaal",
        description=(
            "Rahu Kaal — daily inauspicious window ruled by Rahu. Source: Muhurta texts.\n"
            "Inputs: LocationInput.\n"
            "Returns: Start/end times."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_rahu_kaal(
        ctx: Context,
        location: LocationInput
    ) -> str:
        """Rahu Kaal."""
        try:
            api_key = await require_api_key(ctx)
            body = {"date": location.date, "lat": location.lat, "lon": location.lon}
            rf = location.response_format
            data = await get_client().post("/v1/astro/panchanga/rahu-kaal", api_key, body, timeout=10.0)
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Rahu Kaal", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_rahu_kaal", exc)

    @mcp.tool(
        name="asterwise_get_muhurta",
        description=(
            "Auspicious muhurta (electional timing) for a given activity on a date. Source: Muhurta "
            "classics.\n"
            "Inputs: LocationInput and activity (e.g. marriage, business).\n"
            "Returns: Recommended windows."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_muhurta(
        ctx: Context,
        location: LocationInput,
        activity: str
    ) -> str:
        """Activity-specific muhurta."""
        try:
            api_key = await require_api_key(ctx)
            body = {
                "date": location.date,
                "lat": location.lat,
                "lon": location.lon,
                "activity": activity,
            }
            rf = location.response_format
            data = await get_client().post("/v1/astro/muhurta", api_key, body, timeout=10.0)
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown(f"Muhurta — {activity}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_muhurta", exc)

    @mcp.tool(
        name="asterwise_get_panchanga_calendar",
        description=(
            "Monthly Panchanga calendar — Tithi, Nakshatra, and key dates. Source: Panchanga computation.\n"
            "Inputs: PanchangaCalendarInput (year, month, lat, lon, response_format).\n"
            "Returns: Month-level calendar data."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_panchanga_calendar(
        ctx: Context,
        calendar: PanchangaCalendarInput
    ) -> str:
        """Panchanga calendar month."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {
                "year": calendar.year,
                "month": calendar.month,
                "lat": calendar.lat,
                "lon": calendar.lon,
            }
            rf = calendar.response_format
            data = await get_client().get(
                "/v1/astro/panchanga/calendar", api_key, params, timeout=10.0
            )
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown(
                    f"Panchanga calendar {calendar.year}-{calendar.month:02d}", d
                ),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_panchanga_calendar", exc)

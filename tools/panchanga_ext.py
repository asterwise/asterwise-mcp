"""Tamil Panchanga and Hindu festival calendar MCP tools."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastmcp import Context, FastMCP
import mcp.types as mcp_types
from pydantic import Field

from client import get_client
from models import ResponseFormat
from tools import panchanga_texts as texts
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


class FestivalCategory(str, Enum):
    FESTIVAL = "festival"
    VRAT = "vrat"
    SANKRANTI = "sankranti"
    ECLIPSE = "eclipse"
    PERIOD = "period"


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_tamil_panchanga",
        title="Tamil Panchanga",
        description=compact_description("asterwise_get_tamil_panchanga", texts.TAMIL_PANCHANGA),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_tamil_panchanga(
        ctx: Context,
        date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date for the Tamil panchanga, YYYY-MM-DD."),
        lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees, north positive."),
        lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees, east positive."),
        timezone: str = Field(default="Asia/Kolkata", description="IANA timezone of the location."),
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Compute Tamil Panchanga for a date and location."""
        async with tool_guard("asterwise_get_tamil_panchanga"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {
                "date": date,
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone,
            }
            data = await get_client().get(
                "/v1/astro/panchanga/tamil", api_key, params, timeout=15.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Tamil Panchanga", d),
            )

    @mcp.tool(
        name="asterwise_get_festival_calendar",
        title="Festival Calendar",
        description=compact_description("asterwise_get_festival_calendar", texts.FESTIVAL_CALENDAR),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_festival_calendar(
        ctx: Context,
        year: int = Field(..., ge=1900, le=2100, description="Calendar year, e.g. 2026."),
        lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees, north positive."),
        lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees, east positive."),
        timezone: str = Field(default="Asia/Kolkata", description="IANA timezone of the location."),
        categories: list[FestivalCategory] | None = Field(
            default=None,
            description=(
                "Limit to these categories: festival, vrat, sankranti, eclipse, period. "
                "Omit for all (about 180 entries); ['festival'] gives the named festivals only."
            ),
        ),
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Compute the Hindu festival calendar for a year and location."""
        async with tool_guard("asterwise_get_festival_calendar"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {
                "year": year,
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone,
            }
            if categories:
                params["categories"] = ",".join(c.value for c in categories)
            data = await get_client().get(
                "/v1/astro/panchanga/festivals", api_key, params, timeout=120.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Hindu Festival Calendar {year}", d),
            )

    @mcp.tool(
        name="asterwise_geocode",
        title="Geocode a place",
        description=compact_description("asterwise_geocode", texts.GEOCODE),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_geocode(
        ctx: Context,
        query: str = Field(..., min_length=2, description="Place name, e.g. 'Pune' or 'Fatehabad, Haryana'."),
        limit: int = Field(default=5, ge=1, le=10, description="Maximum matches to return (1-10)."),
        country: str | None = Field(
            default=None, description="Optional ISO 3166 alpha-2 country code to narrow the search, e.g. 'in'."
        ),
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Resolve a place name to latitude, longitude and timezone."""
        async with tool_guard("asterwise_geocode"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {"q": query, "limit": limit}
            if country:
                params["country"] = country
            data = await get_client().get("/v1/utils/geocode", api_key, params, timeout=15.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Places matching '{query}'", d),
            )

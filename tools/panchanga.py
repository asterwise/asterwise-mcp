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
            "Calculate the five elements of the Panchanga for a specific date and "
            "location: Tithi (lunar day 1–30), Vara (weekday and its lord), Nakshatra "
            "(Moon's nakshatra with timings), Yoga (Sun-Moon combined nakshatra), and "
            "Karana (half-tithi). Includes sunrise, sunset, and key timing windows. "
            "Source: classical Panchanga rules. "
            "Use when a user asks about the astrological quality of a day, wants to "
            "know the current Tithi or Nakshatra, or needs a daily almanac. "
            "For muhurta (electional timing for a specific activity), use "
            "asterwise_get_muhurta instead. For just Choghadiya slots, use "
            "asterwise_get_choghadiya. For just Rahu Kaal, use asterwise_get_rahu_kaal."
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
            body = {
                "date": location.date,
                "latitude": location.lat,
                "longitude": location.lon,
                "timezone": location.timezone,
            }
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
            "Get Choghadiya (Chogadia) muhurta slots for a day — the traditional "
            "North Indian system that divides daytime and nighttime into 8 periods "
            "each, ruled by planets in a fixed sequence. Auspicious periods: Amrit, "
            "Shubh, Labh, Char. Inauspicious: Rog, Kaal, Udveg. Source: Muhurta texts. "
            "Use when the user wants to know the best time slot within a day to start "
            "an activity without specifying the activity type. "
            "Use asterwise_get_muhurta when the user has a specific activity "
            "(marriage, travel, business launch) and wants the best date-range window, "
            "not just today's slots."
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
            body = {
                "date": location.date,
                "latitude": location.lat,
                "longitude": location.lon,
                "timezone": location.timezone,
            }
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
            "Get the planetary Hora (hourly ruler) table for a day and location — "
            "each hour of the day and night is governed by a planet in a repeating "
            "sequence starting from the day's ruling planet. Used for selecting the "
            "best hour for a specific activity. Source: Hora Shastra. "
            "Use when the user wants to know which planet rules the current hour "
            "or plans to act at a specific hour and wants astrological support. "
            "Do not confuse with Horasha (birth chart) — this is about planetary "
            "hourly rulers, not natal chart analysis."
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
            body = {
                "date": location.date,
                "latitude": location.lat,
                "longitude": location.lon,
                "timezone": location.timezone,
            }
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
            "Get Rahu Kaal — the daily 90-minute inauspicious period associated with "
            "Rahu, considered unfavourable for starting new ventures. Timing varies "
            "by day of the week (Monday: morning, Tuesday: afternoon, etc.) and "
            "precise sunrise/sunset for the location. Source: Muhurta texts. "
            "Use when the user wants to avoid starting something during Rahu Kaal "
            "today, or when checking if a planned activity falls in this window. "
            "For a full day's auspicious slots, use asterwise_get_choghadiya instead."
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
            body = {
                "date": location.date,
                "latitude": location.lat,
                "longitude": location.lon,
                "timezone": location.timezone,
            }
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
            "Find auspicious muhurta windows for a specific activity type across a "
            "date range. Activity types include: marriage, travel, griha_pravesh "
            "(housewarming), business, education, medical, vehicle purchase, and others. "
            "Returns the best windows within the range with Panchanga quality scores. "
            "Source: Muhurta classics (Muhurta Chintamani, Muhurta Martanda). "
            "Use when the user needs to pick the best date for an important life event "
            "over a future period (weeks or months). "
            "Do not use this for 'what time today' questions — use "
            "asterwise_get_choghadiya for same-day slot selection."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_muhurta(
        ctx: Context,
        location: LocationInput,
        activity: str,
        from_date: str,
        to_date: str,
    ) -> str:
        """Activity-specific muhurta."""
        try:
            api_key = await require_api_key(ctx)
            body = {
                "event_type": activity,
                "from_date": from_date,
                "to_date": to_date,
                "latitude": location.lat,
                "longitude": location.lon,
                "timezone": location.timezone,
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
            "Get a full month's Panchanga calendar — Tithi, Nakshatra, and key "
            "astrological events for every day in a given month and year, for a "
            "specific location. Useful for planning across a calendar month. "
            "Source: Panchanga computation. "
            "Use when a user wants to review the whole month's astrological quality "
            "at once, or when building a monthly astrology feature. "
            "For a single day's details, use asterwise_get_panchanga instead."
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
                "latitude": calendar.lat,
                "longitude": calendar.lon,
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

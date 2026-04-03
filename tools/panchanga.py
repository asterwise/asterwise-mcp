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
        description="Calculate the five elements of the Panchanga for a specific date and\nlocation. Takes location data only — no birth data required.\n\nOUTPUT CONTRACT (response_format=json):\ndata.tithi — { number (1–30), name, paksha ('Shukla' or 'Krishna'),\n  degrees_elapsed, degrees_remaining, end_time (ISO UTC) }\ndata.vara — { number (1=Ravivar…7=Shanivar), name, lord, end_time }\ndata.nakshatra — { index (0=Ashwini…26=Revati), name, pada (1–4),\n  degrees_elapsed, degrees_remaining, end_time (ISO UTC) }\ndata.yoga — { index (0–26), name, is_inauspicious (bool),\n  degrees_elapsed, end_time (ISO UTC) }\n  NOTE: this 'yoga' is the Panchanga Yoga (Sun+Moon nakshatra sum),\n  not an astrological yoga from asterwise_get_yogas — completely\n  different calculation and data structure.\ndata.karana — { number, name, degrees_elapsed, degrees_remaining,\n  end_time (ISO UTC) }\ndata.birth_time_unknown (bool — true for location-only calls, as no\n  birth time is provided; fallback_method = 'sunrise_chart')\n\nERROR CONTRACT: Invalid date format → 422. Dates outside 1900–2100\nrange → 422. Coordinates out of range → 422.\n\nFor a single activity muhurta, use asterwise_get_muhurta.\nFor same-day slot selection, use asterwise_get_choghadiya.\nFor just Rahu Kaal, use asterwise_get_rahu_kaal.\nFor a full month, use asterwise_get_panchanga_calendar.",
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
        description="Get Choghadiya (Chogadia) muhurta slots for a day — 8 daytime and\n8 nighttime periods, each governed by a planet. Auspicious: Amrit\n(best), Shubh, Labh, Chal. Inauspicious: Rog, Kaal, Udveg.\nNo birth data required. Source: Muhurta texts.\n\nOUTPUT CONTRACT (response_format=json):\ndata.date, data.sunrise (HH:MM local), data.sunset (HH:MM local)\ndata.day_choghadiya[] — 8 objects:\n  period (int 1–8), name, type ('auspicious', 'highly auspicious',\n  or 'inauspicious'), ruling_planet, suitable_for, start (HH:MM),\n  end (HH:MM), is_current (bool)\ndata.night_choghadiya[] — 8 objects, same shape\n\nNote on DST: slot boundaries are derived from sunrise/sunset, not\nfixed clock times — DST transitions are handled automatically via the\ntimezone parameter.\n\nERROR CONTRACT: Same as asterwise_get_panchanga.\n\nUse asterwise_get_muhurta when the user has a specific activity\nand wants the best date-range window, not just today's slots.",
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
        description="Get the planetary Hora (hourly ruler) table for a day — all 24 hours\nof the day and night governed by planets in a fixed sequence starting\nfrom the weekday's ruling planet. No birth data required.\nSource: Hora Shastra.\n\nOUTPUT CONTRACT (response_format=json):\ndata.date, data.sunrise (HH:MM), data.next_sunrise (HH:MM)\ndata.horas[] — 24 objects:\n  hora (int 1–24), ruling_planet, start (HH:MM local),\n  end (HH:MM local), quality (string, describes suitable activities),\n  is_current (bool)\n\nERROR CONTRACT: Same as asterwise_get_panchanga.\n\nDo not confuse with Horasha (birth chart) — this is strictly about\nplanetary hourly rulers, not natal chart analysis.",
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
        description="Get Rahu Kaal — the daily inauspicious ~90-minute window for a date\nand location. Also returns Gulika Kaal and Yamaganda Kaal.\nNo birth data required. Source: classical Muhurta texts.\n\nOUTPUT CONTRACT (response_format=json):\ndata.date, data.sunrise (HH:MM local), data.sunset (HH:MM local)\ndata.rahu_kaal — { start (HH:MM local), end (HH:MM local),\n  duration_minutes (int, typically 93), is_active (bool) }\ndata.gulika_kaal — same shape\ndata.yamaganda_kaal — same shape\n\nEdge case: at extreme latitudes where sunrise/sunset cannot be\ncomputed (polar day/night), this tool will return an error.\n\nERROR CONTRACT: Same as asterwise_get_panchanga.\n\nFor a full day's auspicious and inauspicious slots use\nasterwise_get_choghadiya instead.",
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
        description='Find auspicious muhurta windows for a specific activity type across\na date range. Evaluates Tithi, Nakshatra, Vara, Yoga, Karana,\nChoghadiya, and special Yogas (Amrita Siddhi, Sarvartha Siddhi).\nSource: Muhurta Chintamani, Kalaprakashika, Phaladeepika 12.15.\n\nSupported activity values: marriage, travel, griha_pravesh, business,\neducation, medical, vehicle_purchase. Any other value is rejected with\n422 — the API does not fall back to generic muhurta.\n\nOUTPUT CONTRACT (response_format=json):\ndata.event_type, data.from_date, data.to_date, data.timezone,\ndata.ayanamsa, data.total_windows_evaluated (int)\ndata.top_windows[] — scored time windows:\n  date (YYYY-MM-DD), start (HH:MM local), end (HH:MM local),\n  score (int 0–100), choghadiya, choghadiya_type,\n  yoga (Panchanga yoga name), vara, vara_number (1–7),\n  tithi, tithi_number (1–30), is_rahu_kaal (bool),\n  is_abhijit (bool), is_amrita_siddhi (bool),\n  is_sarvartha_siddhi (bool), reason (string)\n\nERROR CONTRACT: Unknown activity type → 422 with details[].\nDate range errors → 422.\n\nFor same-day slot selection use asterwise_get_choghadiya.\nFor just Rahu Kaal use asterwise_get_rahu_kaal.',
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
        description="Get a full month's Panchanga calendar for every day in a given month\nand year, for a specific location. No birth data required.\n\nOUTPUT CONTRACT (response_format=json):\ndata.year (int), data.month (int), data.timezone, data.ayanamsa\ndata.days[] — 28–31 objects, one per calendar day:\n  date (YYYY-MM-DD),\n  tithi — { name, number, paksha, end_time (ISO UTC) }\n  vara — { name, number, lord }\n  nakshatra — { name, index, pada, end_time (ISO UTC) }\n  yoga — { name, index, is_inauspicious (bool), end_time (ISO UTC) }\n  karana — { name, number, end_time (ISO UTC) }\n  rahu_kaal — { start (HH:MM local), end (HH:MM local) }\n\nSupported range: year 1900–2100, month 1–12. Timezone defaults to\nAsia/Kolkata if not specified.\n\nERROR CONTRACT: year outside 1900–2100 → 422. month outside 1–12 → 422.\nCoordinates out of range → 422.\n\nFor a single day, use asterwise_get_panchanga instead.",
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

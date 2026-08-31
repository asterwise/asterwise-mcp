"""Panchanga, muhurta, and timing tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import LocationInput, PanchangaCalendarInput
from runtime import (
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
        title="Panchanga",
        description="Computes Panchanga elements for one calendar date at a geographic location and returns tithi, vara, nakshatra, yoga, karana, and end times in UTC.\n\nSECTION: WHAT THIS TOOL COVERS\nDerives classical Panchanga limbs from sidereal astronomy for the given date, latitude, longitude, and timezone — no birth time or natal chart. data.yoga here is the Panchanga Yoga (Sun+Moon nakshatra composite), wholly separate from natal yogas in asterwise_get_yogas. It does not score muhurta windows across ranges (asterwise_get_muhurta), list Choghadiya slices (asterwise_get_choghadiya), or monthly calendars (asterwise_get_panchanga_calendar).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_choghadiya — same-day slot quality for the location.\n\nSECTION: INPUT CONTRACT\ndate must be YYYY-MM-DD (Pydantic pattern on LocationInput). lat/lon bounds are validated locally. Upstream rejects calendar dates outside 1900–2100. timezone defaults to Asia/Kolkata when the caller leaves the default in LocationInput.\n\nSECTION: OUTPUT CONTRACT\ndata.tithi:\n  number (int — 1–30)\n  name (string)\n  paksha (string — 'Shukla' or 'Krishna')\n  degrees_elapsed (float)\n  degrees_remaining (float)\n  end_time (string — ISO UTC)\ndata.vara:\n  number (int — 1=Ravivar through 7=Shanivar)\n  name (string)\n  lord (string)\n  end_time (string)\ndata.nakshatra:\n  index (int — 0–26)\n  name (string)\n  pada (int — 1–4)\n  degrees_elapsed (float)\n  degrees_remaining (float)\n  end_time (string — ISO UTC)\ndata.yoga:\n  index (int — 0–26)\n  name (string)\n  is_inauspicious (bool)\n  degrees_elapsed (float)\n  end_time (string — ISO UTC)\ndata.karana:\n  number (int)\n  name (string)\n  degrees_elapsed (float)\n  degrees_remaining (float)\n  end_time (string — ISO UTC)\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — date not YYYY-MM-DD or invalid calendar day → MCP INVALID_PARAMS\n  — lat/lon outside allowed ranges → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — dates outside 1900–2100 surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Panchanga yoga is unrelated to asterwise_get_yogas natal combinations.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_yogas — natal chart yogas, not Panchanga Sun–Moon yoga.\nasterwise_get_panchanga_calendar — whole-month daily rows, not a single day.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Choghadiya",
        description="Splits a solar day into sixteen Choghadiya segments from sunrise/sunset at a location and labels each slot's quality, ruler, and local clock bounds.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes eight day and eight night Choghadiya periods with type (auspicious, highly auspicious, inauspicious), ruling planet, suitability text, and is_current flags. Boundaries follow actual sunrise/sunset for the timezone, so DST is implicit. It does not rank multi-day windows for named activities (asterwise_get_muhurta) or return full Panchanga limbs (asterwise_get_panchanga).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_rahu_kaal — optional inauspicious band overlay for the same date.\n\nSECTION: INPUT CONTRACT\nLocationInput enforces YYYY-MM-DD date and lat/lon ranges locally. All parameters are defined in the tool schema.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM local)\ndata.sunset (string — HH:MM local)\ndata.day_choghadiya[] — eight objects:\n  period (int — 1–8)\n  name (string)\n  type (string — 'auspicious', 'highly auspicious', or 'inauspicious')\n  ruling_planet (string)\n  suitable_for (string)\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  is_current (bool)\ndata.night_choghadiya[] — eight objects with the same fields\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput date or coordinates → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Slots track sunrise/sunset, not fixed civil slices.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_hora — twenty-four planetary horas, not sixteen Choghadiya.\nasterwise_get_muhurta — scored windows across a date range for named activities.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Hora",
        description="Builds the twenty-four planetary Horas between successive sunrises for a location date and tags each hour with ruler, quality text, and whether it is current.\n\nSECTION: WHAT THIS TOOL COVERS\nClassical hora muhurta: sequence restarts from the weekday lord, spans day and night until next sunrise, and exposes start/end in local time. It is not a natal divisional chart, not Choghadiya (asterwise_get_choghadiya), and not full Panchanga (asterwise_get_panchanga).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_choghadiya — alternative same-day slot system.\n\nSECTION: INPUT CONTRACT\nLocationInput date/coordinate rules apply locally (YYYY-MM-DD, bounded lat/lon).\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM)\ndata.next_sunrise (string — HH:MM)\ndata.horas[] — twenty-four objects:\n  hora (int — 1–24)\n  ruling_planet (string)\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  quality (string — suitable activities description)\n  is_current (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput fields → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Horas bridge midnight until the next sunrise reference.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_choghadiya — sixteen Choghadiya segments, not twenty-four Horas.\nasterwise_get_natal_chart — natal analysis, not hourly muhurta tables.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Rahu Kaal",
        description="Computes Rahu Kaal, Gulika Kaal, and Yamaganda Kaal intervals from diurnal length at a location and marks whether Rahu Kaal is active now in local time.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns sunrise/sunset anchors plus three inauspicious bands with start, end, duration_minutes (~93 for Rahu Kaal), and is_active on Rahu Kaal. Polar latitudes where sunrise/sunset cannot be solved fail upstream. It does not return Panchanga tithi/nakshatra (asterwise_get_panchanga) or scored muhurta search (asterwise_get_muhurta).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_choghadiya — broader auspicious/inauspicious grid for the day.\n\nSECTION: INPUT CONTRACT\nLocationInput validates date pattern and coordinates locally.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM local)\ndata.sunset (string — HH:MM local)\ndata.rahu_kaal:\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  duration_minutes (int — typically 93)\n  is_active (bool)\ndata.gulika_kaal — same shape as data.rahu_kaal\ndata.yamaganda_kaal — same shape as data.rahu_kaal\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput fields → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — polar or astronomical failures surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Polar latitudes may make sunrise/sunset undefined for the solver → MCP INTERNAL_ERROR.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_choghadiya — full day/night slot tables, not only the three kaal bands.\nasterwise_get_panchanga — Panchanga limbs, not kaal timers.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Muhurta",
        description="Searches a date span for top-scoring muhurta windows for a named activity using Panchanga, Choghadiya, and classical siddhi flags at a location.\n\nSECTION: WHAT THIS TOOL COVERS\nEvaluates marriage, travel, griha_pravesh, business, education, medical, and vehicle_purchase (exact spellings upstream). Returns scored windows with tithi, nakshatra-related yoga name (Panchanga yoga, not natal yogas), vara, choghadiya metadata, boolean guards (rahu kaal, abhijit, amrita/sarvartha siddhi), and textual reasons. Unsupported activity strings are rejected upstream. It does not return a full month calendar (asterwise_get_panchanga_calendar) or only Choghadiya rows (asterwise_get_choghadiya).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_panchanga — drill into Panchanga limbs for a chosen winning date.\n\nSECTION: INPUT CONTRACT\nactivity must be one of the supported English slugs above — not validated locally; bad values become MCP INTERNAL_ERROR. from_date/to_date ordering and span rules are enforced upstream. Location coordinates reuse LocationInput validation for lat/lon/date pattern.\n\nSECTION: OUTPUT CONTRACT\ndata.event_type (string)\ndata.from_date (string)\ndata.to_date (string)\ndata.timezone (string)\ndata.ayanamsa (string)\ndata.total_windows_evaluated (int)\ndata.top_windows[] — each:\n  date (string — YYYY-MM-DD)\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  score (int — 0–100)\n  choghadiya (string)\n  choghadiya_type (string)\n  yoga (string — Panchanga yoga name)\n  vara (string)\n  vara_number (int — 1–7)\n  tithi (string)\n  tithi_number (int — 1–30)\n  is_rahu_kaal (bool)\n  is_abhijit (bool)\n  is_amrita_siddhi (bool)\n  is_sarvartha_siddhi (bool)\n  reason (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput date/lat/lon → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — bad activity, range, or ordering surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Panchanga yoga names here are not asterwise_get_yogas natal yogas.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_choghadiya — enumerates all Choghadiya for one day without activity scoring across a span.\nasterwise_get_panchanga — single-day limb detail, not ranked muhurta search.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Panchanga Calendar",
        description="Returns one row per civil day for a calendar month at a location with condensed tithi, vara, nakshatra, yoga, karana, and rahu_kaal columns.\n\nSECTION: WHAT THIS TOOL COVERS\nMonth-wide Panchanga suitable for planners; each day includes ending times where applicable and local Rahu Kaal bounds. Year must be 1900–2100 and month 1–12 (Pydantic on PanchangaCalendarInput). It is not single-day detailed Panchanga (asterwise_get_panchanga) nor muhurta search (asterwise_get_muhurta).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_panchanga — expand any single day at full detail.\n\nSECTION: INPUT CONTRACT\nyear/month/lat/lon validated locally. Timezone handling follows upstream response fields (data.timezone echo).\n\nSECTION: OUTPUT CONTRACT\ndata.year (int)\ndata.month (int)\ndata.timezone (string)\ndata.ayanamsa (string)\ndata.days[] — 28–31 objects:\n  date (string — YYYY-MM-DD)\n  tithi — { name (string), number (int), paksha (string), end_time (string — ISO UTC) }\n  vara — { name (string), number (int), lord (string) }\n  nakshatra — { name (string), index (int), pada (int), end_time (string — ISO UTC) }\n  yoga — { name (string), index (int), is_inauspicious (bool), end_time (string — ISO UTC) }\n  karana — { name (string), number (int), end_time (string — ISO UTC) }\n  rahu_kaal — { start (string — HH:MM local), end (string — HH:MM local) }\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — year outside 1900–2100 → MCP INVALID_PARAMS\n  — month outside 1–12 → MCP INVALID_PARAMS\n  — lat/lon out of range → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — further rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Day count follows the civil month (28–31 entries).\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_panchanga — deep single-day Panchanga with degree fields, not a month grid.\nasterwise_get_muhurta — activity-ranked windows, not a passive calendar.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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

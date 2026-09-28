"""Panchanga, muhurta, and timing tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP


import mcp.types as mcp_types

from client import get_client
from models import LocationInput, MuhurtaInput, PanchangaCalendarInput
from tools import panchanga_texts as texts
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


# Fields the REST response keeps only for older integrations: `date` is the
# panchanga day and `start`/`end` are HH:MM on it, which reads as the wrong
# night for a window after midnight. The tool shows the unambiguous fields.
_MUHURTA_LEGACY_KEYS = (
    "date", "start", "end", "choghadiya_type", "reason", "is_rahu_kaal",
    "vara_number", "tithi", "tithi_number", "yoga", "yoga_number", "vara", "vara_lord",
)


def _clean_muhurta(payload: Any) -> Any:
    """Rewrite each window around start_at/end_at and grouped panchanga fields."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return payload
    windows = payload["data"].get("top_windows")
    if not isinstance(windows, list):
        return payload
    cleaned = []
    for w in windows:
        if not isinstance(w, dict) or "start_at" not in w:
            cleaned.append(w)
            continue
        out = {k: v for k, v in w.items() if k not in _MUHURTA_LEGACY_KEYS}
        out["tithi"] = {"number": w.get("tithi_number"), "name": w.get("tithi"), "paksha": w.get("paksha")}
        out.pop("paksha", None)
        out["yoga"] = {"number": w.get("yoga_number"), "name": w.get("yoga")}
        out["vara"] = {"number": w.get("vara_number"), "name": w.get("vara"), "lord": w.get("vara_lord")}
        cleaned.append(out)
    return {**payload, "data": {**payload["data"], "top_windows": cleaned}}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_panchanga",
        title="Panchanga",
        description=compact_description("asterwise_get_panchanga", texts.PANCHANGA),
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
        async with tool_guard("asterwise_get_panchanga"):
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
    @mcp.tool(
        name="asterwise_get_choghadiya",
        title="Choghadiya",
        description=compact_description("asterwise_get_choghadiya", "Splits a solar day into sixteen Choghadiya segments from sunrise/sunset at a location and labels each slot's quality, ruler, and local clock bounds.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes eight day and eight night Choghadiya periods with type (auspicious, highly auspicious, inauspicious), ruling planet, suitability text, and is_current flags. Boundaries follow actual sunrise/sunset for the timezone, so DST is implicit. It does not rank multi-day windows for named activities (asterwise_get_muhurta) or return full Panchanga limbs (asterwise_get_panchanga).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_rahu_kaal — optional inauspicious band overlay for the same date.\n\nSECTION: INPUT CONTRACT\nLocationInput enforces YYYY-MM-DD date and lat/lon ranges locally. All parameters are defined in the tool schema.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM local)\ndata.sunset (string — HH:MM local)\ndata.day_choghadiya[] — eight objects:\n  period (int — 1–8)\n  name (string)\n  type (string — 'auspicious', 'highly auspicious', or 'inauspicious')\n  ruling_planet (string)\n  suitable_for (string)\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  is_current (bool)\ndata.night_choghadiya[] — eight objects with the same fields\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput date or coordinates → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Slots track sunrise/sunset, not fixed civil slices.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_hora — twenty-four planetary horas, not sixteen Choghadiya.\nasterwise_get_muhurta — scored windows across a date range for named activities."),
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
        async with tool_guard("asterwise_get_choghadiya"):
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
    @mcp.tool(
        name="asterwise_get_hora",
        title="Hora",
        description=compact_description("asterwise_get_hora", "Builds the twenty-four planetary Horas between successive sunrises for a location date and tags each hour with ruler, quality text, and whether it is current.\n\nSECTION: WHAT THIS TOOL COVERS\nClassical hora muhurta: sequence restarts from the weekday lord, spans day and night until next sunrise, and exposes start/end in local time. It is not a natal divisional chart, not Choghadiya (asterwise_get_choghadiya), and not full Panchanga (asterwise_get_panchanga).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_choghadiya — alternative same-day slot system.\n\nSECTION: INPUT CONTRACT\nLocationInput date/coordinate rules apply locally (YYYY-MM-DD, bounded lat/lon).\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM)\ndata.next_sunrise (string — HH:MM)\ndata.horas[] — twenty-four objects:\n  hora (int — 1–24)\n  ruling_planet (string)\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  quality (string — suitable activities description)\n  is_current (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput fields → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Horas bridge midnight until the next sunrise reference.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_choghadiya — sixteen Choghadiya segments, not twenty-four Horas.\nasterwise_get_natal_chart — natal analysis, not hourly muhurta tables."),
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
        async with tool_guard("asterwise_get_hora"):
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
    @mcp.tool(
        name="asterwise_get_rahu_kaal",
        title="Rahu Kaal",
        description=compact_description("asterwise_get_rahu_kaal", "Computes Rahu Kaal, Gulika Kaal, and Yamaganda Kaal intervals from diurnal length at a location and marks whether Rahu Kaal is active now in local time.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns sunrise/sunset anchors plus three inauspicious bands with start, end, duration_minutes (~93 for Rahu Kaal), and is_active on Rahu Kaal. Polar latitudes where sunrise/sunset cannot be solved fail upstream. It does not return Panchanga tithi/nakshatra (asterwise_get_panchanga) or scored muhurta search (asterwise_get_muhurta).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_choghadiya — broader auspicious/inauspicious grid for the day.\n\nSECTION: INPUT CONTRACT\nLocationInput validates date pattern and coordinates locally.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string)\ndata.sunrise (string — HH:MM local)\ndata.sunset (string — HH:MM local)\ndata.rahu_kaal:\n  start (string — HH:MM local)\n  end (string — HH:MM local)\n  duration_minutes (int — typically 93)\n  is_active (bool)\ndata.gulika_kaal — same shape as data.rahu_kaal\ndata.yamaganda_kaal — same shape as data.rahu_kaal\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid LocationInput fields → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — polar or astronomical failures surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Polar latitudes may make sunrise/sunset undefined for the solver → MCP INTERNAL_ERROR.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_choghadiya — full day/night slot tables, not only the three kaal bands.\nasterwise_get_panchanga — Panchanga limbs, not kaal timers."),
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
        async with tool_guard("asterwise_get_rahu_kaal"):
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
    @mcp.tool(
        name="asterwise_get_muhurta",
        title="Muhurta",
        description=compact_description("asterwise_get_muhurta", texts.MUHURTA),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_muhurta(
        ctx: Context,
        request: MuhurtaInput,
    ) -> str:
        """Activity-specific muhurta."""
        async with tool_guard("asterwise_get_muhurta"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/muhurta", api_key, request.to_api_dict(), timeout=60.0
            )
            data = _clean_muhurta(data)
            return format_tool_result(
                data,
                request.response_format,
                lambda d: structured_markdown(f"Muhurta — {request.activity.value}", d),
            )
    @mcp.tool(
        name="asterwise_get_panchanga_calendar",
        title="Panchanga Calendar",
        description=compact_description("asterwise_get_panchanga_calendar", texts.PANCHANGA_CALENDAR),
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
        async with tool_guard("asterwise_get_panchanga_calendar"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {
                "year": calendar.year,
                "month": calendar.month,
                "latitude": calendar.lat,
                "longitude": calendar.lon,
                "timezone": calendar.timezone,
                "ayanamsa": calendar.ayanamsa.value,
            }
            rf = calendar.response_format
            data = await get_client().get(
                "/v1/astro/panchanga/calendar", api_key, params, timeout=30.0
            )
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown(
                    f"Panchanga calendar {calendar.year}-{calendar.month:02d}", d
                ),
            )

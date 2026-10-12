"""Lore-era Vedic tools (2026-10): tarabala, daily factors, range events,
significations, reference charts. Facts with the rule named; no weighting."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field
import mcp.types as mcp_types

from client import get_client
from models import BirthData, ResponseFormat
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)

_RO = mcp_types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
_FMT = ("SECTION: RESPONSE FORMAT\nresponse_format=json — structured data. response_format=markdown — readable report.\n\n"
        "SECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\n"
        "SECTION: ERROR CONTRACT\nINVALID_PARAMS (local): BirthData validation failures.\n"
        "INVALID_PARAMS (upstream): bad dates, a range over 31 days or an unknown timezone → 422, surfaces as MCP INTERNAL_ERROR with the API message.\n"
        "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n")


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_tarabala",
        title="Tarabala and Chandrabala",
        description=compact_description("asterwise_get_tarabala", (
            "Tarabala and Chandrabala for any date, with the Moon's star and sign change times. For 1 to 31 "
            "civil days, every Moon nakshatra and Moon sign with exact start and end (local and UTC), the tara "
            "counted from the birth nakshatra with its name and verdict, and the Moon's house from the natal "
            "Moon with the chandrabala verdict (Muhurta Chintamani).\n\n"
            "SECTION: WHAT THIS TOOL COVERS\nThe classical daily Moon strengths for one person over a range, each span timed. "
            "Without a birth time the natal Moon may be one star off; the response says so.\n\n"
            "SECTION: WORKFLOW\nBEFORE: asterwise_get_natal_chart — the birth Moon's star.\nAFTER: asterwise_get_vedic_daily_factors — every other factor of the day.\n\n"
            "SECTION: INPUT CONTRACT\nbirth — BirthData. target_date (optional YYYY-MM-DD) — first day; defaults to today in the birth timezone. "
            "days (1-31, default 1). target_timezone (optional IANA) — defines the civil days; defaults to the birth timezone.\n\n"
            "SECTION: OUTPUT CONTRACT\ndata.natal — moon_nakshatra, moon_sign\ndata.moon_nakshatras[] — index, name, start, end, start_utc, end_utc, tarabala {count_from_birth, tara_number, name, meaning, is_favorable}\n"
            "data.moon_signs[] — name, start, end, chandrabala {moon_house_from_natal, is_favorable, is_ashtama}\ndata.rules — the rules in plain words\ndata.birth_time_provided\n\n" + _FMT +
            "SECTION: DO NOT CONFUSE WITH\nasterwise_get_nakshatra_prediction — a one-day prediction, not timed spans.\nasterwise_get_gochar — all planets from the Moon, not the Moon's own tara."
        )), annotations=_RO,
    )
    async def asterwise_get_tarabala(
        ctx: Context, birth: BirthData, response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Defaults to today in the birth timezone.")] = None,
        days: Annotated[int, Field(ge=1, le=31, description="Number of civil days, 1 to 31.")] = 1,
        target_timezone: Annotated[str | None, Field(description="IANA timezone that defines the days. Defaults to the birth timezone.")] = None,
    ) -> str:
        """Tarabala and Chandrabala over a date range."""
        async with tool_guard("asterwise_get_tarabala"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "days": days}
            if target_date:
                body["target_date"] = target_date
            if target_timezone:
                body["target_timezone"] = target_timezone
            data = await get_client().post("/v1/astro/tarabala", api_key, body, timeout=20.0)
            return format_tool_result(data, response_format, lambda d: structured_markdown("Tarabala and Chandrabala", d))

    @mcp.tool(
        name="asterwise_get_vedic_daily_factors",
        title="Vedic Daily Factors",
        description=compact_description("asterwise_get_vedic_daily_factors", (
            "Every classical factor for one person on one day, in one shape, with no weighting. Each factor carries "
            "its raw value and range, its frame (from the Moon, from the Lagna, a natal planet, none), the verdict its "
            "own rule gives or null, the rule's source, signification ids, the time it holds and whether it depends on "
            "the birth time.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\nGochar with bindus and vedha, Sade Sati, Chandra Ashtama, Tarabala and Chandrabala with change times, "
            "the active dasha lords and the transits aspecting them, same-sign contacts to natal planets with the exact degree crossing, "
            "tithi, yoga, karana, vara and the Moon's phase. The caller decides what matters; counts are counts, not scores.\n\n"
            "SECTION: WORKFLOW\nBEFORE: asterwise_get_natal_chart.\nAFTER: asterwise_get_vedic_events — the same over a range, as a timeline.\n\n"
            "SECTION: INPUT CONTRACT\nbirth — BirthData. target_date (optional YYYY-MM-DD; defaults to today in the birth timezone). "
            "target_timezone (optional IANA; defaults to the birth timezone). The day's sky is read at local noon.\n\n"
            "SECTION: OUTPUT CONTRACT\ndata.factors[] — id, group, name, planet, frame, value{}, ranges{}, verdict (favorable|unfavorable|neutral|null), "
            "verdict_rule, rule_source, significations[] (ids from asterwise_get_vedic_significations), time{kind, start, end, at_utc}, depends_on_birth_time\n"
            "data.frames{}, data.counts{}, data.natal{}, data.birth_time_provided, data.instant_utc\n\n" + _FMT +
            "SECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — the transit section only, with interpretations.\nasterwise_get_horoscope — AI-written text, not factors."
        )), annotations=_RO,
    )
    async def asterwise_get_vedic_daily_factors(
        ctx: Context, birth: BirthData, response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: Annotated[str | None, Field(description="Day to read, YYYY-MM-DD. Defaults to today in the birth timezone.")] = None,
        target_timezone: Annotated[str | None, Field(description="IANA timezone of the day. Defaults to the birth timezone.")] = None,
    ) -> str:
        """Every Vedic factor for a person on a day."""
        async with tool_guard("asterwise_get_vedic_daily_factors"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            if target_date:
                body["target_date"] = target_date
            if target_timezone:
                body["target_timezone"] = target_timezone
            data = await get_client().post("/v1/astro/daily-factors", api_key, body, timeout=30.0)
            return format_tool_result(data, response_format, lambda d: structured_markdown("Vedic daily factors", d))

    @mcp.tool(
        name="asterwise_get_vedic_events",
        title="Vedic Events (date range)",
        description=compact_description("asterwise_get_vedic_events", (
            "One timeline of everything that happens to a chart over 1 to 31 days, each event with its exact time. "
            "Sidereal sign ingresses with the new sign's house from the natal Moon, stations, Moon nakshatra changes with "
            "Tarabala, Moon sign changes with Chandrabala, exact degree conjunctions with natal planets, eclipses with "
            "their contacts, and Vimshottari dasha changes (to the day). Each event carries the verdict its own rule gives, or null.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\nThe backbone for calendars and notifications: every dated event over a week or a month, in time order, UTC and local. No weighting.\n\n"
            "SECTION: WORKFLOW\nBEFORE: asterwise_get_natal_chart.\nAFTER: asterwise_get_vedic_daily_factors — the full picture of one of the days.\n\n"
            "SECTION: INPUT CONTRACT\nbirth — BirthData. from_date (optional YYYY-MM-DD; defaults to today). days (1-31, default 7). target_timezone (optional IANA; defaults to the birth timezone).\n\n"
            "SECTION: OUTPUT CONTRACT\ndata.events[] — kind (ingress|station|moon_nakshatra|moon_sign|natal_conjunction|eclipse|dasha_change), planet, title, time_utc, time_local, "
            "time_precision (second|day), detail{}, verdict, verdict_rule, rule_source, significations[], depends_on_birth_time\ndata.kinds{}, data.range_start_utc, data.range_end_utc\n\n" + _FMT +
            "SECTION: DO NOT CONFUSE WITH\nasterwise_get_transits — ingresses and stations for everyone, nothing personal.\nasterwise_get_dasha — the whole dasha tree."
        )), annotations=_RO,
    )
    async def asterwise_get_vedic_events(
        ctx: Context, birth: BirthData, response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        from_date: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Defaults to today in the birth timezone.")] = None,
        days: Annotated[int, Field(ge=1, le=31, description="Number of civil days, 1 to 31 (7 for a week, 30 for a month).")] = 7,
        target_timezone: Annotated[str | None, Field(description="IANA timezone for the days and local times. Defaults to the birth timezone.")] = None,
    ) -> str:
        """Vedic events over a date range."""
        async with tool_guard("asterwise_get_vedic_events"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "days": days}
            if from_date:
                body["from_date"] = from_date
            if target_timezone:
                body["target_timezone"] = target_timezone
            data = await get_client().post("/v1/astro/events", api_key, body, timeout=30.0)
            return format_tool_result(data, response_format, lambda d: structured_markdown("Vedic events", d))

    @mcp.tool(
        name="asterwise_get_vedic_significations",
        title="Vedic Significations (BPHS)",
        description=compact_description("asterwise_get_vedic_significations", (
            "What each house and planet signifies in Brihat Parashara Hora Shastra, as a fixed list with stable ids. "
            "Houses from chapter 11, verses 2-13; planets from chapter 3, verses 12-13 and the karaka verses of chapters 8 and 14.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\nTwo levels: a domain (relationships, work, wealth …) and the signification itself, each with its verse. "
            "Ids are never renamed or reused; a retired entry stays with deprecated=true and replaced_by. Apps map these ids to their own categories. "
            "Rahu and Ketu are left out because BPHS gives them no such verse.\n\n"
            "SECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_vedic_daily_factors — factors cite these ids.\n\n"
            "SECTION: INPUT CONTRACT\nNo inputs beyond response_format.\n\n"
            "SECTION: OUTPUT CONTRACT\ndata.domains[] — id, label\ndata.houses[] — house, id, name, significations[] {id, label, domain, source, deprecated, replaced_by}\n"
            "data.planets[] — planet, id, significations[]\ndata.version, data.source, data.id_policy\n\n" + _FMT.replace("MEDIUM_COMPUTE", "FAST_LOOKUP") +
            "SECTION: DO NOT CONFUSE WITH\nasterwise_get_western_significations — Lilly's list for the Western track.\nasterwise_get_planet_nature — a planet's nature in one chart."
        )), annotations=_RO,
    )
    async def asterwise_get_vedic_significations(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
        """BPHS significations list."""
        async with tool_guard("asterwise_get_vedic_significations"):
            api_key = await require_api_key(ctx)
            data = await get_client().get("/v1/astro/significations", api_key, timeout=10.0)
            return format_tool_result(data, response_format, lambda d: structured_markdown("Vedic significations (BPHS)", d))

    @mcp.tool(
        name="asterwise_get_reference_charts",
        title="Reference Charts",
        description=compact_description("asterwise_get_reference_charts", (
            "Published test charts with reference values from an independent source, so anyone can check the maths. "
            "They cover the 25 edge cases of the verification harness (clock changes, southern hemisphere, polar night and day, the date line, "
            "45-minute zones, historical offsets, leap day, range limits), a sample of random charts, a Moon-on-a-nakshatra-boundary case "
            "and an unknown-birth-time case.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\nFor each chart: the exact natal request, the expected sidereal longitudes, signs, nakshatras and ascendant from PyJHora "
            "(or a direct Swiss Ephemeris call), the UTC instant, the local time status, and the tolerance. Values never come from Asterwise.\n\n"
            "SECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_natal_chart — send an input and compare.\n\n"
            "SECTION: INPUT CONTRACT\nNo inputs beyond response_format.\n\n"
            "SECTION: OUTPUT CONTRACT\ndata.charts[] — id, covers, input{}, expected{utc, local_time_status, ayanamsa_true, planets{}, ascendant{}}, reference_source, tolerance{}\n"
            "data.how_to_use, data.harness\n\n" + _FMT.replace("MEDIUM_COMPUTE", "FAST_LOOKUP") +
            "SECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — computes a chart; this lists charts to check it against."
        )), annotations=_RO,
    )
    async def asterwise_get_reference_charts(ctx: Context, response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
        """Published reference charts."""
        async with tool_guard("asterwise_get_reference_charts"):
            api_key = await require_api_key(ctx)
            data = await get_client().get("/v1/astro/reference-charts", api_key, timeout=10.0)
            return format_tool_result(data, response_format, lambda d: structured_markdown("Reference charts", d))

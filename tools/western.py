"""Western astrology tools — tropical zodiac, Placidus houses."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
import mcp.types as mcp_types

from client import get_client
from models import ResponseFormat, WesternBirthData
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:

    # ─── Natal ────────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_natal",
        title="Western Natal Chart",
        description=compact_description("asterwise_get_western_natal", (
            "Calculate a complete Western natal chart using the tropical zodiac and Swiss Ephemeris. "
            "Returns 10 planet positions with Placidus (or chosen) house placements, essential "
            "dignities, all active aspects, and element/modality/hemisphere balance statistics.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Tropical natal chart: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, "
            "Neptune, Pluto. Each planet returns tropical longitude, sign, house (1–12), retrograde "
            "flag, dignity label (domicile/exaltation/detriment/fall/peregrine), dignity score "
            "(domicile +5, exaltation +4, triplicity +3, term +2, face +1, "
            "detriment -5, fall -4), is_exaltation_degree (within 1° of exact exaltation), "
            "dignity_disputed (true for outer planets where exaltation/fall is disputed among "
            "modern astrologers). Aspect orbs: conjunction/opposition 5°, "
            "square/trine 5°, sextile 3°, minor aspects 1.5°. Not Vedic sidereal (asterwise_get_natal_chart).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — this tool is standalone.\n"
            "AFTER: asterwise_get_western_transits_daily — layer current transits over this natal chart.\n"
            "AFTER: asterwise_get_western_synastry — compare this chart against a partner's chart.\n"
            "AFTER: asterwise_get_western_solar_return — annual return chart for the current year.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth.date — YYYY-MM-DD. Example: '1985-11-12'\n"
            "birth.time — HH:MM (24-hour local time). Example: '06:45'\n"
            "birth.lat — Decimal degrees, north positive. Example: 19.076 (Mumbai)\n"
            "birth.lon — Decimal degrees, east positive. Example: 72.8777 (Mumbai)\n"
            "birth.timezone — IANA timezone string. Example: 'Asia/Kolkata', 'America/New_York', "
            "'Europe/Rome', 'UTC'. Default: UTC.\n"
            "  IMPORTANT: Timezone defaults to UTC — always supply the correct local timezone "
            "for accurate house cusps. An incorrect timezone shifts the Ascendant.\n"
            "birth.house_system — 'placidus' (default, most common), 'koch', 'equal', 'whole_sign'. "
            "Placidus is standard for most Western traditions. Whole sign is traditional/Hellenistic.\n"
            "  NOTE: house_system is accepted here but silently ignored by transit, return, synastry, "
            "composite, and progression endpoints — those always use the birth location coordinates "
            "without house-system selection.\n"
            "ayanamsa — always tropical regardless of any value supplied; field is not present.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.zodiac (string — 'tropical')\n"
            "data.house_system (string — the system used)\n"
            "data.ascendant — { longitude (float), sign (string), sign_index (int 0–11), degree_in_sign (float) }\n"
            "data.mc — same shape as ascendant\n"
            "data.planets[] — 10 objects (Sun through Pluto):\n"
            "  name (string), longitude (float), sign (string), sign_index (int 0–11)\n"
            "  degree_in_sign (float), house (int 1–12)\n"
            "  is_retrograde (bool), dignity (string), dignity_score (int)\n"
            "  is_exaltation_degree (bool), dignity_disputed (bool)\n"
            "data.houses[] — 12 objects:\n"
            "  house (int 1–12), cusp_longitude (float), sign (string)\n"
            "  sign_index (int 0–11), degree_in_sign (float)\n"
            "data.aspects[] — each:\n"
            "  planet_a (string), planet_b (string), type (string)\n"
            "  exact_angle (float), orb (float), is_applying (bool)\n"
            "data.elements — { fire (int), earth (int), air (int), water (int), dominant (string) }\n"
            "data.modalities — { cardinal (int), fixed (int), mutable (int), dominant (string) }\n"
            "data.hemisphere — { eastern (int), western (int), northern (int), southern (int) }\n"
            "data.ayanamsa_value (float — 0.0 for tropical)\n"
            "data.ayanamsa_used (string — 'tropical')\n"
            "data.birth_time_provided (bool)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON — use this "
            "for programmatic parsing, typed clients, and downstream tool chaining.\n"
            "response_format=markdown renders the same data as a human-readable natal report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~300ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local — caught before upstream call):\n"
            "  — WesternBirthData Pydantic violations (date pattern, time pattern, lat/lon bounds) → MCP INVALID_PARAMS\n"
            "INVALID_PARAMS (upstream):\n"
            "  — None expected for valid coordinates and dates post-1800.\n"
            "INTERNAL_ERROR:\n"
            "  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  — Polar latitudes (above ~65°N or below ~65°S) may cause Placidus house calculation "
            "failure; use whole_sign or equal house system for polar births.\n"
            "  — time='00:00' accepted; lagna-sensitive results are unreliable for unknown birth times.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_natal_chart — Vedic sidereal chart using Lahiri ayanamsa; different zodiac, "
            "different house system, different planet set (9 grahas vs 10 tropical planets).\n"
            "asterwise_get_western_aspects — takes raw longitudes as input; use when you already have "
            "positions and don't need full chart computation."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_natal(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western tropical natal chart."""
        async with tool_guard("asterwise_get_western_natal"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/western/natal", api_key, birth.to_api_dict(), timeout=20.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western natal chart", d),
            )
    # ─── Moon Phase ───────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_moon_phase",
        title="Western Moon Phase",
        description=compact_description("asterwise_get_western_moon_phase", (
            "Calculates the tropical lunar phase for any date using Swiss Ephemeris. "
            "Returns the phase name, phase angle, illumination percentage, Moon age in days, "
            "and the next major phase transition.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Eight-phase tropical lunar cycle: New Moon (0°), Waxing Crescent, First Quarter (90°), "
            "Waxing Gibbous, Full Moon (180°), Waning Gibbous, Last Quarter (270°), Waning Crescent. "
            "Phase angle is Sun–Moon elongation in degrees (0–360). Illumination percentage is "
            "derived from the phase angle using the cosine formula. Moon age is days since "
            "last New Moon.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_western_moon_calendar — get the full month's phase data.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date (optional string YYYY-MM-DD) — Date to compute phase for. Defaults to today.\n"
            "  Example: '2026-05-01'\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date (string — YYYY-MM-DD)\n"
            "data.phase_name (string — one of the eight canonical phase names)\n"
            "data.phase_angle (float — 0–360°, Sun–Moon elongation)\n"
            "data.illumination_pct (float — 0–100)\n"
            "data.moon_age_days (float — days since New Moon)\n"
            "data.moon_longitude (float — tropical ecliptic longitude)\n"
            "data.sun_longitude (float — tropical ecliptic longitude)\n"
            "data.is_waxing (bool — true from New to Full Moon)\n"
            "data.next_phase_name (string — next major phase)\n"
            "data.next_phase_date (string — approximate YYYY-MM-DD of next major phase)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured phase data.\n"
            "response_format=markdown — human-readable moon report.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — date validated upstream.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_moon_calendar — full monthly day-by-day phase table.\n"
            "asterwise_get_panchanga — Vedic tithi system (lunar day based on 12° arc increments)."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_moon_phase(
        ctx: Context,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        date: str | None = None,
    ) -> str:
        """Western moon phase for a date."""
        async with tool_guard("asterwise_get_western_moon_phase"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if date:
                params["date"] = date
            data = await get_client().get(
                "/v1/western/moon/phase", api_key, params, timeout=15.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Moon phase", d),
            )
    # ─── Moon Calendar ────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_moon_calendar",
        title="Western Moon Calendar",
        description=compact_description("asterwise_get_western_moon_calendar", (
            "Returns lunar phase data for every day in a calendar month as a structured array. "
            "Each element is a complete daily phase object identical to asterwise_get_western_moon_phase.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Month-at-a-glance lunar calendar for any year/month combination. Useful for "
            "building moon phase widgets, identifying full and new moon dates, planning "
            "tools based on lunar cycles, and content calendars. Defaults to the current month.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "year (optional int) — Target year. Defaults to current year. Example: 2026\n"
            "month (optional int 1–12) — Target month. Defaults to current month.\n"
            "  Example: 5 (May)\n"
            "  Values outside 1–12 are rejected locally with MCP INVALID_PARAMS.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — array of daily phase objects, one per calendar day in the month.\n"
            "  Each object is identical to asterwise_get_western_moon_phase output.\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — array of daily phase objects.\n"
            "response_format=markdown — month view with day-by-day phases.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~500ms for 30 days)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local):\n"
            "  — month outside 1–12 → MCP INVALID_PARAMS immediately.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_moon_phase — single-day phase only."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_moon_calendar(
        ctx: Context,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        year: int | None = None,
        month: int | None = None,
    ) -> str:
        """Monthly moon phase calendar."""
        async with tool_guard("asterwise_get_western_moon_calendar"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if year:
                params["year"] = year
            if month:
                if not 1 <= month <= 12:
                    invalid_params("month must be between 1 and 12.")
                params["month"] = month
            data = await get_client().get(
                "/v1/western/moon/calendar", api_key, params, timeout=20.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Moon phase calendar", d),
            )
    # ─── Aspects ──────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_aspects",
        title="Western Aspects",
        description=compact_description("asterwise_get_western_aspects", (
            "Calculates all active aspects between a supplied set of planetary longitudes. "
            "Accepts a dictionary of body name to tropical ecliptic longitude and returns "
            "every aspect within standard natal orbs.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Flexible aspect calculator that works with any set of positions — natal planets, "
            "transit planets, progressed planets, or custom hypothetical points. Aspect orbs: "
            "conjunction/opposition 5°, square/trine 5°, sextile 3°, "
            "semisextile/quincunx/semisquare/sesquiquadrate 1.5°. Returns is_applying based "
            "on relative speeds if speeds are provided, otherwise assumed separating.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone; or use asterwise_get_western_natal to get positions first.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "positions — dict mapping planet/body name (string) to tropical longitude (float 0–360).\n"
            "  Must contain at least 2 entries.\n"
            "  Example: {'Sun': 229.6, 'Moon': 221.8, 'Mars': 189.6, 'Jupiter': 309.6}\n"
            "  Names can be any string — the tool does not enforce planet names.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.aspects[] — each:\n"
            "  planet_a (string), planet_b (string), type (string — aspect name)\n"
            "  exact_angle (float), orb (float), is_applying (bool)\n"
            "data.orbs_used — dict of aspect type to orb value used\n"
            "data.body_count (int — number of input bodies)\n"
            "data.aspect_count (int — number of aspects found)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — aspect grid object.\n"
            "response_format=markdown — formatted aspect table.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local):\n"
            "  — fewer than 2 bodies in positions dict → MCP INVALID_PARAMS immediately.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_natal — computes both positions and aspects from birth data.\n"
            "asterwise_get_western_synastry — inter-chart aspects between two people."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_aspects(
        ctx: Context,
        positions: dict[str, float],
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western aspect grid from raw positions."""
        async with tool_guard("asterwise_get_western_aspects"):
            api_key = await require_api_key(ctx)
            if len(positions) < 2:
                invalid_params(
                    "positions must contain at least two bodies with longitudes for aspects."
                )
            data = await get_client().post(
                "/v1/western/aspects", api_key,
                {"positions": positions}, timeout=15.0,
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western aspects", d),
            )
    # ─── Transits ─────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_transits_daily",
        title="Western Daily Transits",
        description=compact_description("asterwise_get_western_transits_daily", (
            "Current sky positions vs natal chart for a single day. Returns all 10 planets with "
            "tropical longitudes and active aspects to natal positions using transit orbs: "
            "major 3°, sextile 2°, minor 1°. Provide start_date for "
            "a specific day; defaults to today.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Single-day transit snapshot: where each planet is now versus where each natal planet "
            "was at birth, with applying/separating transit-to-natal aspects using tighter transit "
            "orbs than natal chart orbs. Excludes progressions and solar arc — pure transit ephemeris.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal — establish natal chart first.\n"
            "AFTER: asterwise_get_western_transits_weekly — for week view.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData (date, time, lat, lon, timezone). house_system ignored for this endpoint.\n"
            "start_date (optional YYYY-MM-DD) — defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date, data.transit_planets[] — name, longitude, sign, is_retrograde, aspects_to_natal[]\n"
            "data.aspects[] — transit_planet, natal_planet, type, orb, is_applying\n"
            "data.total_aspects\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~400ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Transit orbs are smaller than natal orbs: major 3°, sextile 2°, minor 1°.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_transits_weekly — 7 days vs 1 day.\n"
            "asterwise_get_western_transits_monthly — 30-day window vs single day."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_transits_daily(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        start_date: str | None = None,
    ) -> str:
        """Daily Western transits vs natal."""
        async with tool_guard("asterwise_get_western_transits_daily"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if start_date:
                body["start_date"] = start_date
            data = await get_client().post(
                "/v1/western/transits/daily", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Daily transits", d),
            )
    @mcp.tool(
        name="asterwise_get_western_transits_weekly",
        title="Western Weekly Transits",
        description=compact_description("asterwise_get_western_transits_weekly", (
            "7-day transit window vs natal chart. Returns day-by-day transit snapshots plus peak "
            "aspects (active 4+ days in the window). Use start_date to set the week start; defaults "
            "to today.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Rolling seven-day transit analysis with one snapshot per day (same structure as daily "
            "transits) plus peak_aspects highlighting aspects that persist across multiple days.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: asterwise_get_western_transits_monthly — for full month.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData. house_system ignored.\n"
            "start_date (optional YYYY-MM-DD) — week start; defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.start_date, data.end_date\n"
            "data.days[] — 7 daily transit objects (same shape as daily transits)\n"
            "data.peak_aspects[] — aspects active on 4 or more days\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~2s for 7 days)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_transits_daily — single day.\n"
            "asterwise_get_western_transits_monthly — 30 days vs 7."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_transits_weekly(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        start_date: str | None = None,
    ) -> str:
        """Weekly Western transits vs natal."""
        async with tool_guard("asterwise_get_western_transits_weekly"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if start_date:
                body["start_date"] = start_date
            data = await get_client().post(
                "/v1/western/transits/weekly", api_key, body, timeout=30.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Weekly transits", d),
            )
    @mcp.tool(
        name="asterwise_get_western_transits_monthly",
        title="Western Monthly Transits",
        description=compact_description("asterwise_get_western_transits_monthly", (
            "30-day transit window vs natal chart. Returns day-by-day transit snapshots plus peak "
            "aspects (active 10+ days in the window). Use start_date to set the month start; defaults "
            "to today.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Full-month transit calendar: 30 consecutive daily snapshots vs the same natal chart, "
            "with peak_aspects for long-duration hits. Largest payload of the transit trio.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData. house_system ignored.\n"
            "start_date (optional YYYY-MM-DD) — month start; defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.start_date, data.end_date\n"
            "data.days[] — 30 daily transit objects\n"
            "data.peak_aspects[] — aspects active on 10 or more days\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "SLOW_COMPUTE (~15s for 30 days)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Large payload — 30 daily snapshots. Use json format for downstream processing.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_transits_daily — 1 day.\n"
            "asterwise_get_western_transits_weekly — 7 days."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_transits_monthly(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        start_date: str | None = None,
    ) -> str:
        """Monthly Western transits vs natal."""
        async with tool_guard("asterwise_get_western_transits_monthly"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if start_date:
                body["start_date"] = start_date
            data = await get_client().post(
                "/v1/western/transits/monthly", api_key, body, timeout=60.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Monthly transits", d),
            )
    # ─── Synastry & Compatibility ─────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_synastry",
        title="Western Synastry",
        description=compact_description("asterwise_get_western_synastry", (
            "Aspect grid between two natal charts using the tropical zodiac. Returns all inter-chart "
            "aspects using standard inter-chart orbs. Useful for relationship compatibility analysis.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Bidirectional aspect matrix: every person1 planet to every person2 planet within orb. "
            "Does not produce a compatibility score — raw geometry only. House overlays are not included.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal per person — understand charts individually first.\n"
            "AFTER: asterwise_get_western_composite — midpoint chart for the relationship itself.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "person1, person2 — each WesternBirthData (date, time, lat, lon, timezone). "
            "house_system ignored for synastry payload.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.aspects[] — person1_planet, person2_planet, type, exact_angle, orb\n"
            "data.total_aspects\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~600ms, two natal charts + aspect grid)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_composite — one merged midpoint chart vs synastry (two charts overlaid).\n"
            "asterwise_get_western_compatibility — numeric 0–100 score vs raw aspects."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_synastry(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western synastry aspect grid."""
        async with tool_guard("asterwise_get_western_synastry"):
            api_key = await require_api_key(ctx)
            body = {
                "person1": person1.to_api_dict_no_house(),
                "person2": person2.to_api_dict_no_house(),
            }
            data = await get_client().post(
                "/v1/western/synastry", api_key, body, timeout=25.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western synastry", d),
            )
    @mcp.tool(
        name="asterwise_get_western_composite",
        title="Western Composite",
        description=compact_description("asterwise_get_western_composite", (
            "Midpoint composite chart for two people. Each composite planet is "
            "the midpoint of the two natal positions. Returns composite planets with dignities and "
            "internal aspects.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Single synthetic chart representing the relationship as its own entity — not person A vs "
            "person B overlaid. Midpoints handle wrap-around at 360° correctly.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_synastry — examine inter-chart aspects before composite.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "person1, person2 — WesternBirthData each. house_system ignored.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.planets[] — 10 composite planets with name, longitude, sign, degree_in_sign, dignity, dignity_score\n"
            "data.ascendant_longitude, data.ascendant_sign, data.ascendant_sign_index\n"
            "data.aspects[] — internal aspects within the composite chart\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~600ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_synastry — two charts, inter-chart aspects vs composite (one midpoint chart).\n"
            "asterwise_get_western_compatibility — numeric score vs structural composite chart."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_composite(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western composite midpoint chart."""
        async with tool_guard("asterwise_get_western_composite"):
            api_key = await require_api_key(ctx)
            body = {
                "person1": person1.to_api_dict_no_house(),
                "person2": person2.to_api_dict_no_house(),
            }
            data = await get_client().post(
                "/v1/western/composite", api_key, body, timeout=25.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Composite chart", d),
            )
    @mcp.tool(
        name="asterwise_get_western_compatibility",
        title="Western Compatibility",
        description=compact_description("asterwise_get_western_compatibility", (
            "Overall compatibility score (0–100) between two natal charts. Scores element affinity, "
            "synastry aspects between personal planets (Sun, Moon, Venus, Mars), and Sun/Moon/rising "
            "sign comparisons.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Weighted scoring model combining elemental harmony, personal-planet synastry "
            "hits, and luminaries/rising affinity labels. Higher score = more harmonious synergy — "
            "interpret relatively, not as fate.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal per person optional.\n"
            "AFTER: asterwise_get_western_synastry — drill into raw aspects if score needs detail.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "person1, person2 — WesternBirthData each.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.overall_score (int 0-100)\n"
            "data.element_score (int 0-100)\n"
            "data.aspect_score (int 0-100)\n"
            "data.sun_sign_affinity, data.moon_sign_affinity, data.rising_sign_affinity — "
            "'harmonious'|'neutral'|'challenging'\n"
            "data.person1_sun, data.person2_sun, data.person1_moon, data.person2_moon\n"
            "data.key_aspects[] — aspects between personal planets\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Score reflects multiple weighted factors. Use for relative comparison between "
            "charts, not as an absolute outcome predictor.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_synastry — raw aspects, no score.\n"
            "asterwise_get_western_zodiac_compatibility — sign-only, no birth data."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_compatibility(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western compatibility score (0-100)."""
        async with tool_guard("asterwise_get_western_compatibility"):
            api_key = await require_api_key(ctx)
            body = {
                "person1": person1.to_api_dict_no_house(),
                "person2": person2.to_api_dict_no_house(),
            }
            data = await get_client().post(
                "/v1/western/compatibility", api_key, body, timeout=25.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western compatibility", d),
            )
    @mcp.tool(
        name="asterwise_get_western_zodiac_compatibility",
        title="Western Zodiac Compatibility",
        description=compact_description("asterwise_get_western_zodiac_compatibility", (
            "Sign-to-sign compatibility without birth data. Based on element and modality affinity. "
            "Fast — no ephemeris calculation required.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Lookup table compatibility using sign elements (fire/earth/air/water) and modalities "
            "(cardinal/fixed/mutable). No houses, no Moon phase, no Venus Mars geometry.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — no birth data needed.\n"
            "AFTER: asterwise_get_western_compatibility — when full charts are available.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "sign1, sign2 — English zodiac names (Aries … Pisces).\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.sign1, data.sign2\n"
            "data.element1, data.element2\n"
            "data.modality1, data.modality2\n"
            "data.element_affinity, data.modality_affinity — 'harmonious'|'neutral'|'challenging'\n"
            "data.overall_score (int 0-100)\n"
            "data.description (string)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — no ephemeris, pure table lookup.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — sign validation upstream.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_compatibility — requires full birth data, more accurate.\n"
            "asterwise_get_western_synastry — aspect geometry between two full charts."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_zodiac_compatibility(
        ctx: Context,
        sign1: str,
        sign2: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Zodiac sign-to-sign compatibility."""
        async with tool_guard("asterwise_get_western_zodiac_compatibility"):
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/western/compatibility/zodiac", api_key,
                {"sign1": sign1, "sign2": sign2}, timeout=10.0,
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(
                    f"Zodiac compatibility: {sign1} + {sign2}", d
                ),
            )
    # ─── Returns ──────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_solar_return",
        title="Western Solar Return",
        description=compact_description("asterwise_get_western_solar_return", (
            "Solar return chart for a given year. Finds the exact moment the Sun returns to its natal "
            "tropical longitude and builds a complete Western natal chart for that moment at the birth "
            "location. Provide the year as an integer (e.g. 2026).\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Annual solar return — the chart cast for the precise instant the transiting Sun reaches "
            "the natal Sun's longitude, relocated to birth place (not relocated charts). The embedded "
            "data.chart is a full tropical chart at that instant.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal — understand natal chart before reading return.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData. house_system ignored (chart uses return computation defaults).\n"
            "year (int) — calendar year of the return (e.g. 2026), not age.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.planet — 'Sun'\n"
            "data.natal_longitude (float — natal Sun tropical longitude)\n"
            "data.return_utc (string — ISO 8601 UTC moment of return)\n"
            "data.return_jd (float — Julian Day of return)\n"
            "data.chart — full Western natal chart at return moment\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~800ms, iterative Sun longitude search)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  year param is the calendar year of the return (e.g., 2026), not the age. "
            "Feeding age instead of year silently produces the wrong return chart.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_lunar_return — Moon return, ~monthly.\n"
            "asterwise_get_varshaphal — Vedic Tajika solar return — different system."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_solar_return(
        ctx: Context,
        birth: WesternBirthData,
        year: int,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Western solar return chart."""
        async with tool_guard("asterwise_get_western_solar_return"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict_no_house(), "year": year}
            data = await get_client().post(
                "/v1/western/solar-return", api_key, body, timeout=30.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"Solar return {year}", d),
            )
    @mcp.tool(
        name="asterwise_get_western_lunar_return",
        title="Western Lunar Return",
        description=compact_description("asterwise_get_western_lunar_return", (
            "Next lunar return chart after a given date. Finds the next moment the Moon returns to its "
            "natal tropical longitude (approximately every 27.3 days) and builds a complete Western "
            "natal chart for that moment at the birth location.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Monthly emotional reset chart — similar workflow to solar return but cadence is lunar "
            "synodic month, not tropical year.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData.\n"
            "after_date (optional YYYY-MM-DD) — find next return after this date. Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Same shape as solar return: planet='Moon', natal_longitude, return_utc, return_jd, chart\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~500ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Returns the NEXT lunar return after after_date — if after_date is omitted, "
            "returns the next return from today.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_solar_return — annual Sun return vs lunar_return (monthly Moon return)."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_lunar_return(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        after_date: str | None = None,
    ) -> str:
        """Western lunar return chart."""
        async with tool_guard("asterwise_get_western_lunar_return"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if after_date:
                body["after_date"] = after_date
            data = await get_client().post(
                "/v1/western/lunar-return", api_key, body, timeout=30.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Lunar return", d),
            )
    @mcp.tool(
        name="asterwise_get_western_planetary_return",
        title="Western Planetary Return",
        description=compact_description("asterwise_get_western_planetary_return", (
            "Next return chart for any planet after a given date. Finds the exact moment the specified "
            "planet returns to its natal tropical longitude and builds a complete Western natal chart "
            "for that moment at the birth location.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Generalised return for any of the 10 classical tropical bodies — Mercury returns "
            "(yearly-ish), Venus (~1 year), Mars (~2 years), Jupiter (~12 years), Saturn (~29 years), "
            "through Pluto (~248 years).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData.\n"
            "planet — one of Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto.\n"
            "after_date (optional YYYY-MM-DD) — defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Same shape as solar return: planet name, natal_longitude, return_utc, return_jd, chart\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "SLOW_COMPUTE for outer planets (Jupiter+ return can search years ahead)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local):\n"
            "  planet not in the valid 10-planet set → MCP INVALID_PARAMS locally.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Neptune return takes ~165 years — only useful for generational analysis, "
            "not individual lifetime prediction. Pluto return: ~248 years, never completes in one lifetime.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_solar_return — Sun-only shortcut.\n"
            "asterwise_get_western_lunar_return — Moon-only shortcut."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_planetary_return(
        ctx: Context,
        birth: WesternBirthData,
        planet: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        after_date: str | None = None,
    ) -> str:
        """Western planetary return chart."""
        async with tool_guard("asterwise_get_western_planetary_return"):
            api_key = await require_api_key(ctx)
            valid_planets = {
                "Sun", "Moon", "Mercury", "Venus", "Mars",
                "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
            }
            if planet not in valid_planets:
                invalid_params(
                    f"planet must be one of: {', '.join(sorted(valid_planets))}. "
                    f"Got: {planet!r}"
                )
            body = {**birth.to_api_dict_no_house(), "planet": planet}
            if after_date:
                body["after_date"] = after_date
            data = await get_client().post(
                "/v1/western/planetary-return", api_key, body, timeout=60.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"{planet} return", d),
            )
    # ─── Progressions ─────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_secondary_progressions",
        title="Western Secondary Progressions",
        description=compact_description("asterwise_get_western_secondary_progressions", (
            "Secondary progressed chart using the day-for-a-year method. Each day after birth "
            "symbolises one year of life (1 ephemeris day = 1 tropical year = 365.2421904 days). "
            "Returns all 10 progressed planet positions, progressed Ascendant and MC, and the solar arc.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Secondary directions: Moon advances ~12°/year of life, Mercury/Venus track "
            "close to Sun speed, outer planets crawl. Includes progressed lunation phases internally.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: asterwise_get_western_solar_arc — compare uniform arc vs individual motion.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData.\n"
            "target_date (optional YYYY-MM-DD) — the date to progress to. Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.target_date, data.progressed_jd, data.age_years\n"
            "data.solar_arc (float — ~1° per year)\n"
            "data.natal_sun_longitude, data.progressed_sun_longitude\n"
            "data.progressed_planets[] — 10 objects: name, longitude, sign, degree_in_sign, is_retrograde, dignity, dignity_score\n"
            "data.progressed_ascendant, data.progressed_ascendant_sign\n"
            "data.progressed_mc, data.progressed_mc_sign\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~400ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  Progressed ASC uses the actual house calculation at progressed JD (not solar arc "
            "approximation) for higher accuracy. Progressed MC uses natal MC + solar arc.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_solar_arc — all planets move by one uniform arc.\n"
            "asterwise_get_western_transits_daily — real-time sky, not symbolic progression."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_secondary_progressions(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: str | None = None,
    ) -> str:
        """Secondary progressed chart (day-for-a-year)."""
        async with tool_guard("asterwise_get_western_secondary_progressions"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if target_date:
                body["target_date"] = target_date
            data = await get_client().post(
                "/v1/western/progressions/secondary", api_key, body, timeout=25.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Secondary progressions", d),
            )

    @mcp.tool(
        name="asterwise_get_western_solar_arc",
        title="Western Solar Arc",
        description=compact_description("asterwise_get_western_solar_arc", (
            "Solar Arc Directions for a target date. The solar arc (progressed Sun minus natal Sun) is "
            "applied uniformly to every natal planet and angle — approximately 1° per year. Unlike "
            "secondary progressions, all planets advance at the same rate.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Solar arc directions — one delta longitude applied to every natal body and "
            "the angles. Classic predictive technique for timing outer events.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_western_natal.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — WesternBirthData.\n"
            "target_date (optional YYYY-MM-DD) — defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.target_date, data.solar_arc, data.age_years\n"
            "data.natal_sun_longitude, data.progressed_sun_longitude\n"
            "data.directed_planets[] — 10 objects: name, natal_longitude, directed_longitude, sign, degree_in_sign, dignity, dignity_score\n"
            "data.directed_ascendant, data.directed_ascendant_sign\n"
            "data.directed_mc, data.directed_mc_sign\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "MEDIUM_COMPUTE (~400ms)\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): WesternBirthData validation failures.\n"
            "INTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\n"
            "Edge cases:\n"
            "  All planets advance at the same rate (solar arc ≈ 1°/year). This is Solar Arc Directions — "
            "different from secondary progressions where each planet moves at its own astronomical speed.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_secondary_progressions — each planet moves at its own rate.\n"
            "asterwise_get_western_transits_daily — real-time transits, not arc directions."
        )),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_western_solar_arc(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: str | None = None,
    ) -> str:
        """Solar Arc Directions."""
        async with tool_guard("asterwise_get_western_solar_arc"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict_no_house()
            if target_date:
                body["target_date"] = target_date
            data = await get_client().post(
                "/v1/western/progressions/solar-arc", api_key, body, timeout=25.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Solar Arc directions", d),
            )
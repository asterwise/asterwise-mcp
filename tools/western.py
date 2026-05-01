"""Western astrology tools — tropical zodiac, Placidus houses."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from mcp.shared.exceptions import McpError
import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import ResponseFormat, WesternBirthData
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

    # ─── Natal ────────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_natal",
        description=(
            "Calculate a complete Western natal chart using the tropical zodiac "
            "and Swiss Ephemeris. Returns 10 planet positions (Sun through Pluto) "
            "with tropical longitudes, Placidus (or chosen) house placements, "
            "essential dignities per Ptolemy/Lilly/Hand, all active aspects using "
            "Robert Hand Table 2 orbs, and element/modality/hemisphere statistics.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Tropical natal chart: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, "
            "Uranus, Neptune, Pluto. Each planet returns longitude, sign, house, "
            "retrograde flag, dignity label (domicile/exaltation/detriment/fall/peregrine), "
            "dignity score (Lilly weights), is_exaltation_degree, dignity_disputed "
            "(true for outer planet exaltation/fall). Aspects use Hand Table 2 orbs: "
            "major 5°, sextile 3°, minor 1.5°. Includes elements, modalities, "
            "hemisphere balance.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth.date YYYY-MM-DD, birth.time HH:MM, birth.lat, birth.lon, "
            "birth.timezone (IANA). house_system: placidus (default), koch, "
            "equal, whole_sign. ayanamsa is ignored — always tropical.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.zodiac (string — 'tropical')\n"
            "data.house_system (string)\n"
            "data.ascendant — longitude, sign, sign_index, degree_in_sign\n"
            "data.mc — same shape\n"
            "data.planets[] — 10 objects:\n"
            "  name, longitude, sign, sign_index, degree_in_sign, house (int 1-12),\n"
            "  is_retrograde, dignity, dignity_score, is_exaltation_degree, "
            "dignity_disputed\n"
            "data.houses[] — 12 objects: house, cusp_longitude, sign, sign_index, "
            "degree_in_sign\n"
            "data.aspects[] — type, planet_a, planet_b, exact_angle, orb, is_applying\n"
            "data.elements — fire, earth, air, water, dominant\n"
            "data.modalities — cardinal, fixed, mutable, dominant\n"
            "data.hemisphere — eastern, western, northern, southern\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_natal_chart — Vedic sidereal, not tropical Western."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_natal(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Western tropical natal chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/western/natal", api_key, birth.to_api_dict(), timeout=20.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western natal chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_natal", exc)

    # ─── Moon Phase ───────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_moon_phase",
        description=(
            "Calculate the lunar phase for any date using the tropical zodiac. "
            "Returns phase name (New Moon, Waxing Crescent, First Quarter, "
            "Waxing Gibbous, Full Moon, Waning Gibbous, Last Quarter, Waning Crescent), "
            "phase angle, illumination percentage, moon age in days, and next major "
            "phase estimate. Defaults to today if no date given.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date, data.phase_name, data.phase_angle (0-360°), "
            "data.illumination_pct (0-100), data.moon_age_days, "
            "data.moon_longitude, data.sun_longitude, data.is_waxing, "
            "data.next_phase_name, data.next_phase_date (YYYY-MM-DD estimate)\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_panchanga — Vedic tithi system, not tropical phase angles."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_moon_phase(
        ctx: Context,
        response_format: ResponseFormat,
        date: str | None = None,
    ) -> str:
        """Western moon phase for a date."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_moon_phase", exc)

    # ─── Moon Calendar ────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_moon_calendar",
        description=(
            "Returns lunar phase data for every day in a given month. "
            "Useful for building moon phase calendars, identifying full/new moons, "
            "and auspicious timing tools. "
            "Defaults to current month if no year/month given.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — array of daily phase objects, each identical to "
            "asterwise_get_western_moon_phase output."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_moon_calendar(
        ctx: Context,
        response_format: ResponseFormat,
        year: int | None = None,
        month: int | None = None,
    ) -> str:
        """Monthly moon phase calendar."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_moon_calendar", exc)

    # ─── Aspects ──────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_aspects",
        description=(
            "Calculate all active aspects between any set of planetary positions. "
            "Provide a dictionary of body names to tropical ecliptic longitudes (0-360). "
            "Uses Robert Hand Table 2 orbs by default: major 5°, sextile 3°, minor 1.5°.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "positions: dict of planet_name → longitude float (0-360). "
            "Example: {'Sun': 229.6, 'Moon': 221.8, 'Mars': 189.6}\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.aspects[] — planet_a, planet_b, type, exact_angle, orb, is_applying\n"
            "data.orbs_used — dict of aspect type to orb used\n"
            "data.body_count, data.aspect_count\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_natal — computes aspects from birth data automatically."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_aspects(
        ctx: Context,
        positions: dict[str, float],
        response_format: ResponseFormat,
    ) -> str:
        """Western aspect grid from raw positions."""
        try:
            api_key = await require_api_key(ctx)
            if not positions:
                invalid_params("positions must contain at least one planet longitude.")
            data = await get_client().post(
                "/v1/western/aspects", api_key,
                {"positions": positions}, timeout=15.0,
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Western aspects", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_aspects", exc)

    # ─── Transits ─────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_transits_daily",
        description=(
            "Current sky positions vs natal chart for a single day. "
            "Returns all 10 planets with tropical longitudes and active aspects "
            "to natal positions using transit orbs (Hand Planets in Transit): "
            "major 3°, sextile 2°, minor 1°. "
            "Provide start_date for a specific day; defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date, data.transit_planets[] — name, longitude, sign, "
            "is_retrograde, aspects_to_natal[]\n"
            "data.aspects[] — transit_planet, natal_planet, type, orb, is_applying\n"
            "data.total_aspects"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_transits_daily(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        start_date: str | None = None,
    ) -> str:
        """Daily Western transits vs natal."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_transits_daily", exc)

    @mcp.tool(
        name="asterwise_get_western_transits_weekly",
        description=(
            "7-day transit window vs natal chart. "
            "Returns day-by-day transit snapshots plus peak aspects "
            "(active 4+ days in the window). "
            "Use start_date to set the week start; defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.start_date, data.end_date\n"
            "data.days[] — 7 daily transit objects (same shape as daily transits)\n"
            "data.peak_aspects[] — aspects active on 4 or more days"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_transits_weekly(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        start_date: str | None = None,
    ) -> str:
        """Weekly Western transits vs natal."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_transits_weekly", exc)

    @mcp.tool(
        name="asterwise_get_western_transits_monthly",
        description=(
            "30-day transit window vs natal chart. "
            "Returns day-by-day transit snapshots plus peak aspects "
            "(active 10+ days in the window). "
            "Use start_date to set the month start; defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.start_date, data.end_date\n"
            "data.days[] — 30 daily transit objects\n"
            "data.peak_aspects[] — aspects active on 10 or more days"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_transits_monthly(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        start_date: str | None = None,
    ) -> str:
        """Monthly Western transits vs natal."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_transits_monthly", exc)

    # ─── Synastry & Compatibility ─────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_synastry",
        description=(
            "Aspect grid between two natal charts using the tropical zodiac. "
            "Returns all inter-chart aspects using Robert Hand Table 2 orbs. "
            "Useful for relationship compatibility analysis.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "person1 and person2: each a WesternBirthData object with date, time, "
            "lat, lon, timezone.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.aspects[] — person1_planet, person2_planet, type, exact_angle, orb\n"
            "data.total_aspects"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_synastry(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Western synastry aspect grid."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_synastry", exc)

    @mcp.tool(
        name="asterwise_get_western_composite",
        description=(
            "Midpoint composite chart for two people (Robert Hand method). "
            "Each composite planet is the midpoint of the two natal positions. "
            "Returns composite planets with dignities and internal aspects.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.planets[] — 10 composite planets with name, longitude, sign, "
            "degree_in_sign, dignity, dignity_score\n"
            "data.ascendant_longitude, data.ascendant_sign, data.ascendant_sign_index\n"
            "data.aspects[] — internal aspects within the composite chart"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_composite(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Western composite midpoint chart."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_composite", exc)

    @mcp.tool(
        name="asterwise_get_western_compatibility",
        description=(
            "Overall compatibility score (0-100) between two natal charts. "
            "Scores element affinity, synastry aspects between personal planets "
            "(Sun, Moon, Venus, Mars), and Sun/Moon/rising sign comparisons.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.overall_score (int 0-100)\n"
            "data.element_score (int 0-100)\n"
            "data.aspect_score (int 0-100)\n"
            "data.sun_sign_affinity, data.moon_sign_affinity, "
            "data.rising_sign_affinity — 'harmonious'|'neutral'|'challenging'\n"
            "data.person1_sun, data.person2_sun, data.person1_moon, data.person2_moon\n"
            "data.key_aspects[] — aspects between personal planets"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_compatibility(
        ctx: Context,
        person1: WesternBirthData,
        person2: WesternBirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Western compatibility score (0-100)."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_compatibility", exc)

    @mcp.tool(
        name="asterwise_get_western_zodiac_compatibility",
        description=(
            "Sign-to-sign compatibility without birth data. "
            "Based on element and modality affinity. "
            "Fast — no ephemeris calculation required.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "sign1 and sign2: English zodiac sign names (Aries, Taurus, Gemini, "
            "Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, "
            "Aquarius, Pisces).\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.sign1, data.sign2\n"
            "data.element1, data.element2\n"
            "data.modality1, data.modality2\n"
            "data.element_affinity, data.modality_affinity — "
            "'harmonious'|'neutral'|'challenging'\n"
            "data.overall_score (int 0-100)\n"
            "data.description (string)"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_zodiac_compatibility(
        ctx: Context,
        sign1: str,
        sign2: str,
        response_format: ResponseFormat,
    ) -> str:
        """Zodiac sign-to-sign compatibility."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_zodiac_compatibility", exc)

    # ─── Returns ──────────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_solar_return",
        description=(
            "Solar return chart for a given year. "
            "Finds the exact moment the Sun returns to its natal tropical longitude "
            "and builds a complete Western natal chart for that moment at the "
            "birth location. Provide the year as an integer (e.g. 2026).\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.planet — 'Sun'\n"
            "data.natal_longitude (float — natal Sun tropical longitude)\n"
            "data.return_utc (string — ISO 8601 UTC moment of return)\n"
            "data.return_jd (float — Julian Day of return)\n"
            "data.chart — full Western natal chart at return moment"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_solar_return(
        ctx: Context,
        birth: WesternBirthData,
        year: int,
        response_format: ResponseFormat,
    ) -> str:
        """Western solar return chart."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict_no_house(), "year": year}
            data = await get_client().post(
                "/v1/western/solar-return", api_key, body, timeout=30.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"Solar return {year}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_solar_return", exc)

    @mcp.tool(
        name="asterwise_get_western_lunar_return",
        description=(
            "Next lunar return chart after a given date. "
            "Finds the next moment the Moon returns to its natal tropical longitude "
            "(approximately every 27.3 days) and builds a complete Western natal "
            "chart for that moment at the birth location.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "after_date (optional YYYY-MM-DD): find next return after this date. "
            "Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Same shape as solar return: planet='Moon', natal_longitude, "
            "return_utc, return_jd, chart"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_lunar_return(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        after_date: str | None = None,
    ) -> str:
        """Western lunar return chart."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_lunar_return", exc)

    @mcp.tool(
        name="asterwise_get_western_planetary_return",
        description=(
            "Next return chart for any planet after a given date. "
            "Finds the exact moment the specified planet returns to its natal "
            "tropical longitude and builds a complete Western natal chart for "
            "that moment at the birth location.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "planet: one of Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, "
            "Uranus, Neptune, Pluto.\n"
            "after_date (optional YYYY-MM-DD): defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Same shape as solar return: planet name, natal_longitude, "
            "return_utc, return_jd, chart"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_planetary_return(
        ctx: Context,
        birth: WesternBirthData,
        planet: str,
        response_format: ResponseFormat,
        after_date: str | None = None,
    ) -> str:
        """Western planetary return chart."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_planetary_return", exc)

    # ─── Progressions ─────────────────────────────────────────────

    @mcp.tool(
        name="asterwise_get_western_secondary_progressions",
        description=(
            "Secondary progressed chart using the day-for-a-year method. "
            "Each day after birth symbolises one year of life "
            "(1 ephemeris day = 1 tropical year = 365.2421904 days). "
            "Returns all 10 progressed planet positions, progressed Ascendant "
            "and MC (True Quotidian method), and the solar arc.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "target_date (optional YYYY-MM-DD): the date to progress to. "
            "Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.target_date, data.progressed_jd, data.age_years\n"
            "data.solar_arc (float — ~1° per year)\n"
            "data.natal_sun_longitude, data.progressed_sun_longitude\n"
            "data.progressed_planets[] — 10 objects: name, longitude, sign, "
            "degree_in_sign, is_retrograde, dignity, dignity_score\n"
            "data.progressed_ascendant, data.progressed_ascendant_sign\n"
            "data.progressed_mc, data.progressed_mc_sign\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_solar_arc — moves all planets by same arc; "
            "secondary progressions move each planet at its own rate."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_secondary_progressions(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        target_date: str | None = None,
    ) -> str:
        """Secondary progressed chart (day-for-a-year)."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error(
                "asterwise_get_western_secondary_progressions", exc
            )

    @mcp.tool(
        name="asterwise_get_western_solar_arc",
        description=(
            "Solar Arc Directions for a target date. "
            "The solar arc (progressed Sun minus natal Sun) is applied uniformly "
            "to every natal planet and angle — approximately 1° per year. "
            "Unlike secondary progressions, all planets advance at the same rate.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "target_date (optional YYYY-MM-DD): defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.target_date, data.solar_arc, data.age_years\n"
            "data.natal_sun_longitude, data.progressed_sun_longitude\n"
            "data.directed_planets[] — 10 objects: name, natal_longitude, "
            "directed_longitude, sign, degree_in_sign, dignity, dignity_score\n"
            "data.directed_ascendant, data.directed_ascendant_sign\n"
            "data.directed_mc, data.directed_mc_sign\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_western_secondary_progressions — each planet moves "
            "at its own astronomical speed."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        ),
    )
    async def asterwise_get_western_solar_arc(
        ctx: Context,
        birth: WesternBirthData,
        response_format: ResponseFormat,
        target_date: str | None = None,
    ) -> str:
        """Solar Arc Directions."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_solar_arc", exc)

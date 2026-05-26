"""Vedic reference data and prediction tools."""

from __future__ import annotations

from typing import Any, Optional
from datetime import date

from fastmcp import Context, FastMCP
from mcp.shared.exceptions import McpError
import mcp.types as mcp_types
from pydantic import Field, ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat
from runtime import (
    format_tool_result,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_planet_nature",
        description=(
            "Returns classical graha (planet) properties for all nine planets or a single planet "
            "per classical Vedic tradition.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Returns tattva (element), guna (Sattvic/Rajasic/Tamasic), gender, caste/varna, "
            "natural benefic/malefic nature, direction, color, presiding deity, ruling day of week, "
            "metal, body part governed, and naisargika maitri (natural friends, enemies, neutrals) "
            "for each of the nine grahas: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. "
            "Rahu and Ketu include note explaining reference-table limits for shadow nodes.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone reference.\n"
            "AFTER: asterwise_get_puja_suggestions — propitiation for a specific graha.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "planet (optional): One of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. "
            "Omit to get all nine planets.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Single planet: data.planet, data.tattva, data.guna, data.gender, data.caste, "
            "data.nature, data.direction, data.color, data.deity, data.day, data.metal, "
            "data.body_part, data.friends[], data.enemies[], data.neutrals[]\n"
            "All planets: data.planets{} — object keyed by planet name, each with above fields\n\n"
            "SECTION: COMPUTE CLASS\nFAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (upstream): Unknown planet name → MCP INTERNAL_ERROR\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_puja_suggestions — ritual propitiation per planet, not properties.\n"
            "asterwise_get_rudraksha — bead recommendations per planet, not natal properties."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_planet_nature(
        ctx: Context,
        response_format: ResponseFormat,
        planet: Optional[str] = None,
    ) -> str:
        """Graha properties — all nine or one planet."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if planet:
                params["planet"] = planet
            data = await get_client().get(
                "/v1/astro/planet-nature", api_key, params, timeout=10.0
            )
            title = f"Planet Nature — {planet}" if planet else "Planet Nature — All Grahas"
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(title, d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_planet_nature", exc)

    @mcp.tool(
        name="asterwise_get_puja_suggestions",
        description=(
            "Returns puja (ritual worship) recommendations for planetary propitiation per graha.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "For each of the nine grahas, returns: puja name, presiding deity, day of week, "
            "specific offerings (flowers, grains, incense), grain associated, and beej mantra. "
            "Used by practitioners to recommend planetary remedies based on chart analysis.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_natal_chart — identify afflicted planets before recommending pujas.\n"
            "AFTER: asterwise_get_rudraksha — complementary bead-based remedy.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "planet (optional): One of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. "
            "Omit to get all nine planets.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Single planet: data.planet, data.puja_name, data.deity, data.day, "
            "data.offerings[], data.grain, data.mantra\n"
            "All planets: data.planets{} — object keyed by planet name\n\n"
            "SECTION: COMPUTE CLASS\nFAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (upstream): Unknown planet name → MCP INTERNAL_ERROR\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_remedies — personalised remedies from natal chart analysis.\n"
            "asterwise_get_rudraksha — bead recommendations, not puja rituals."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_puja_suggestions(
        ctx: Context,
        response_format: ResponseFormat,
        planet: Optional[str] = None,
    ) -> str:
        """Classical puja recommendations per planet."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if planet:
                params["planet"] = planet
            data = await get_client().get(
                "/v1/astro/puja-suggestions", api_key, params, timeout=10.0
            )
            title = f"Puja Suggestions — {planet}" if planet else "Puja Suggestions — All Planets"
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(title, d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_puja_suggestions", exc)

    @mcp.tool(
        name="asterwise_get_rudraksha",
        description=(
            "Returns Rudraksha bead recommendations per planet.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "For each of the nine planets, returns: mukhi (face count), presiding deity, "
            "exact beej mantra, recommended metal for stringing, wearing day, mala bead count "
            "(108), recommended wearing finger, and spiritual benefits.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: asterwise_get_natal_chart — identify planets needing support.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "planet (optional): One of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. "
            "Omit to get all nine planets.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "Single planet: data.planet, data.mukhi (int), data.presiding_deity, data.mantra, "
            "data.metal, data.wearing_day, data.mala_beads (int), data.wearing_finger, "
            "data.benefits\n"
            "All planets: data.planets{} — object keyed by planet name\n\n"
            "SECTION: COMPUTE CLASS\nFAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (upstream): Unknown planet name → MCP INTERNAL_ERROR\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_gemstone_recommendations — Ratna-style gemstones from natal chart.\n"
            "asterwise_get_puja_suggestions — ritual worship, not bead recommendations."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_rudraksha(
        ctx: Context,
        response_format: ResponseFormat,
        planet: Optional[str] = None,
    ) -> str:
        """Rudraksha bead recommendations per planet."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if planet:
                params["planet"] = planet
            data = await get_client().get(
                "/v1/astro/rudraksha", api_key, params, timeout=10.0
            )
            title = f"Rudraksha — {planet}" if planet else "Rudraksha — All Planets"
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(title, d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_rudraksha", exc)

    @mcp.tool(
        name="asterwise_get_ayanamsha",
        description=(
            "Returns ayanamsha values for all four supported systems "
            "(Lahiri, Raman, KP, Tropical) for a given date.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Ayanamsha is the angular difference between the tropical and sidereal zodiacs "
            "due to the precession of the equinoxes (~50.3\" per year). "
            "Returns each system's value in decimal degrees and DMS "
            "(degrees/minutes/seconds) format, with a description of each system's tradition. "
            "Lahiri (Chitrapaksha) is the Indian government standard. "
            "KP ayanamsha is used for Krishnamurti Paddhati calculations. "
            "Computed using Swiss Ephemeris DE431.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone reference.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date (optional): Date in YYYY-MM-DD format. Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date (string)\n"
            "data.ayanamsha{}: lahiri, raman, kp, tropical — each:\n"
            "  value_decimal (float), degrees (int), minutes (int), seconds (float),\n"
            "  dms (string e.g. '24° 13' 29.82\"'), description (string)\n"
            "data.note (string — recommendation to use Lahiri for Jyotish)\n\n"
            "SECTION: COMPUTE CLASS\nFAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_natal_chart — applies Lahiri ayanamsha automatically to natal positions.\n"
            "asterwise_get_western_natal — uses tropical zodiac (ayanamsha = 0)."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_ayanamsha(
        ctx: Context,
        response_format: ResponseFormat,
        date: Optional[str] = Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
    ) -> str:
        """Ayanamsha values for all four systems for a given date."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {}
            if date:
                params["date"] = date
            data = await get_client().get(
                "/v1/astro/ayanamsha", api_key, params, timeout=10.0
            )
            title = f"Ayanamsha — {date}" if date else "Ayanamsha — Today"
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(title, d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ayanamsha", exc)

    @mcp.tool(
        name="asterwise_get_biorhythm",
        description=(
            "Computes physical (23-day), emotional (28-day), and intellectual (33-day) "
            "biorhythm cycles for a birth date.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Returns cycle values (-1.0 to +1.0), percentage, phase label "
            "(High/Rising/Falling/Low), and critical day flags for each cycle. "
            "Critical days occur when a cycle crosses the zero line — these represent "
            "instability and vulnerability to poor judgment or accidents. "
            "Supports single-day snapshot (days=1) and multi-day range (up to 90 days). "
            "Formula: sin(2π × t / cycle_length) where t = days since birth. "
            "Also returns composite_score (average of three cycles) and has_critical_day flag. "
            "Biorhythm is a Western concept — Vedic equivalents are Tarabala and Chandrabala "
            "(use asterwise_get_nakshatra_prediction for the Vedic equivalent).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_nakshatra_prediction — for the Vedic personalized daily prediction.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth_date (required): Date of birth in YYYY-MM-DD format.\n"
            "target_date (optional): Date to compute for. Defaults to today.\n"
            "days (optional int 1-90): Number of consecutive days. Default 1.\n\n"
            "SECTION: OUTPUT CONTRACT (single day)\n"
            "data.birth_date, data.target_date, data.days_since_birth (int)\n"
            "data.cycles{}: physical, emotional, intellectual — each:\n"
            "  value (float -1.0 to +1.0), percentage (float), phase (string),\n"
            "  is_critical (bool), cycle_length_days (int), description (string)\n"
            "data.critical_today[] (string array of cycle names that are critical)\n"
            "data.has_critical_day (bool)\n"
            "data.composite_score (float — average of three cycles)\n"
            "data.note (string — explains Vedic equivalents)\n\n"
            "SECTION: OUTPUT CONTRACT (date range, days > 1)\n"
            "data.birth_date, data.start_date, data.end_date, data.days\n"
            "data.daily[] — array of day objects each with date, cycles{}, critical[], composite_score\n\n"
            "SECTION: COMPUTE CLASS\nFAST_LOOKUP — pure math, no ephemeris.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (upstream): birth_date after target_date → INTERNAL_ERROR\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_nakshatra_prediction — Vedic Tarabala/Chandrabala daily prediction.\n"
            "asterwise_get_panchanga — Vedic daily panchanga elements, not biorhythm cycles."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_biorhythm(
        ctx: Context,
        birth_date: str,
        response_format: ResponseFormat,
        target_date: Optional[str] = None,
        days: int = 1,
    ) -> str:
        """Biorhythm cycles — physical, emotional, intellectual."""
        try:
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = {"birth_date": birth_date}
            if target_date:
                body["target_date"] = target_date
            if days != 1:
                body["days"] = days
            data = await get_client().post(
                "/v1/western/biorhythm", api_key, body, timeout=10.0
            )
            title = f"Biorhythm — {target_date or 'Today'}"
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(title, d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_biorhythm", exc)

    @mcp.tool(
        name="asterwise_get_nakshatra_prediction",
        description=(
            "Returns a personalised daily prediction using Tarabala and Chandrabala.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Computes the individual's daily auspiciousness score by:\n"
            "1. TARABALA: Counts from birth nakshatra to today's transit Moon nakshatra (inclusive). "
            "The remainder mod 9 gives the Tara (1=Janma, 2=Sampat/Wealth, 3=Vipat/Danger, "
            "4=Kshema/Prosperity, 5=Pratyak/Obstacle, 6=Sadhana/Achievement, "
            "7=Naidhana/Destruction, 8=Mitra/Friend, 9=Ati-Mitra/Great Friend).\n"
            "2. CHANDRABALA: Transit Moon's house from natal Moon (favorable in houses 1,3,6,7,10,11).\n"
            "3. TRANSIT NAKSHATRA QUALITY: The type of today's Moon nakshatra "
            "(Dhruva/Chara/Ugra/Tikshna/Kshipra/Mridu/Mishra) with auspicious and "
            "inauspicious activities.\n"
            "Combined daily score out of 4 with label (Excellent/Good/Moderate/Challenging).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — birth data computes everything needed.\n"
            "AFTER: asterwise_get_panchanga — for full daily panchanga context.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — BirthData (date, time, lat, lon, timezone).\n"
            "target_date (optional): YYYY-MM-DD. Defaults to today.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.target_date (string)\n"
            "data.birth_nakshatra{}: name (string), index (int 0-26)\n"
            "data.natal_moon_sign_index (int 0-11)\n"
            "data.transit_moon{}: nakshatra (string), nakshatra_index (int), rashi_index (int)\n"
            "data.tarabala{}: tara_number (int 1-9), count_from_birth (int),\n"
            "  name (string), meaning (string), is_favorable (bool),\n"
            "  interpretation (string)\n"
            "data.chandrabala{}: moon_house_from_natal (int 1-12),\n"
            "  is_favorable (bool), favorable_houses[] (int array)\n"
            "data.daily_score{}: score (int 0-4), max_score (4), label (string)\n"
            "data.transit_nakshatra_quality{}: nakshatra (string), quality_type (string),\n"
            "  english (string), auspicious_for[] (string array),\n"
            "  inauspicious_for[] (string array)\n"
            "data.nakshatra_activities{}: favorable[] (string array),\n"
            "  unfavorable[] (string array)\n"
            "SECTION: COMPUTE CLASS\nMEDIUM_COMPUTE — natal chart + ephemeris Moon position.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): BirthData Pydantic violations → MCP INVALID_PARAMS\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_nakshatra_details — static nakshatra reference, not personalised prediction.\n"
            "asterwise_get_panchanga — daily panchanga (tithi, yoga, karana), not Tarabala scoring.\n"
            "asterwise_get_biorhythm — Western biorhythm cycles, not classical Vedic prediction."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_nakshatra_prediction(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        target_date: Optional[str] = Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
    ) -> str:
        """Personalised Tarabala + Chandrabala daily prediction."""
        try:
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            if target_date:
                body["target_date"] = target_date
            data = await get_client().post(
                "/v1/astro/nakshatra/prediction", api_key, body, timeout=15.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Nakshatra Prediction (Tarabala)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_nakshatra_prediction", exc)

    @mcp.tool(
        name="asterwise_get_pitra_dosha",
        description=(
            "Detects and analyses Pitru Dosha (Pitru Shapa — Ancestral Curse) using "
            "all five classical Pitru Dosha combinations.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Standalone Pitru Dosha endpoint with deeper analysis than the pitru_dosha "
            "field inside asterwise_get_doshas. Returns: presence flag, severity "
            "(mild/moderate/severe), which of the 5 classical combinations triggered, "
            "Sun analysis (house, sign, debilitation, afflictions), 9th lord analysis "
            "(identity, house, debilitation, afflictions), all contributing factors, "
            "cancellation conditions (Jupiter protective), classical symptoms, and remedies.\n"
            "Primary classical symptom for Purvajanma Shapa (karmic affliction): "
            "denial of progeny or difficulties with children. "
            "Afflicting planets: Saturn, Rahu, Mars, Ketu.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — birth data computes everything needed.\n"
            "AFTER: asterwise_get_puja_suggestions — recommend remedial pujas for Sun/Mars.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — BirthData (date, time, lat, lon, timezone).\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.present (bool)\n"
            "data.severity (string — 'mild', 'moderate', 'severe', or null)\n"
            "data.severity_note (string or null)\n"
            "data.bphs_combinations_triggered[] — each: combination (string), "
            "description (string), factors[] (string array), weight (int)\n"
            "data.bphs_combinations_count (int)\n"
            "data.sun_analysis{}: house (int), sign_index (int), debilitated (bool), "
            "afflictions[] (string array)\n"
            "data.ninth_lord_analysis{}: planet (string), house (int), sign_index (int), "
            "debilitated (bool), afflictions[] (string array)\n"
            "data.all_factors[] (string array — deduplicated list of all triggers)\n"
            "data.cancellations[] (string array — Jupiter protective conditions)\n"
            "data.interpretation (string)\n"
            "data.classical_symptoms[] (string array)\n"
            "data.remedies[] (string array)\n"
            "data.classical_source (string)\n\n"
            "SECTION: COMPUTE CLASS\nMEDIUM_COMPUTE — natal chart computation.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): BirthData Pydantic violations → MCP INVALID_PARAMS\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_doshas — returns pitru_dosha as one of twelve doshas with "
            "less detail. Use this tool when dedicated Pitru Dosha analysis is needed."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_pitra_dosha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Standalone Pitru Dosha analysis — all five classical combinations."""
        try:
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            data = await get_client().post(
                "/v1/astro/pitra-dosha", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Pitru Dosha Analysis", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_pitra_dosha", exc)

    @mcp.tool(
        name="asterwise_get_ghat_chakra",
        description=(
            "Returns the four Ghatak (inauspicious) timing parameters for a native "
            "based on their Janma Rasi (natal Moon sign).\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Ghat Chakra identifies the four parameters that are persistently "
            "inauspicious for a native based on their Janma Rasi:\n"
            "1. Ghatak Masa — the lunar month to avoid for major events\n"
            "2. Ghatak Tithi — the lunar day group (Nanda/Bhadra/Jaya/Rikta/Purna)\n"
            "3. Ghatak Vara — the weekday to avoid for major events\n"
            "4. Ghatak Nakshatra — the transit Moon nakshatra to avoid\n"
            "When transit periods align with these parameters, the native should avoid "
            "starting new ventures, surgery, travel, or auspicious ceremonies. "
            "When multiple Ghatak parameters coincide simultaneously, the period "
            "is considered extremely inauspicious.\n"
            "Source: classical muhurta tradition Ch.1 (Shubhashubha Prakarana); "
            "classical text Ch.26 (Gocharaphala).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — birth data computes everything needed.\n"
            "AFTER: asterwise_get_nakshatra_prediction — for today's personalized "
            "daily auspiciousness score.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "birth — BirthData (date, time, lat, lon, timezone). "
            "Moon sign is computed from birth data.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.janma_rasi (string — Sanskrit Moon sign name)\n"
            "data.janma_rasi_index (int 0-11)\n"
            "data.ghatak_parameters{}:\n"
            "  masa{}: name (string), description (string)\n"
            "  tithi{}: group (string), tithi_numbers[] (int array), "
            "description (string)\n"
            "  vara{}: day (string), description (string)\n"
            "  nakshatra{}: name (string), description (string)\n"
            "data.guidance (string)\n"
            "data.avoidance_guidance[] (string array)\n"
            "data.classical_source (string)\n\n"
            "SECTION: COMPUTE CLASS\nMEDIUM_COMPUTE — natal chart for Moon sign.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): BirthData Pydantic violations → MCP INVALID_PARAMS\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_nakshatra_prediction — personalised daily Tarabala score, "
            "not static Ghatak parameters.\n"
            "asterwise_get_panchanga — daily panchanga elements, not Ghat Chakra lookup."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_ghat_chakra(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Ghat Chakra — four Ghatak timing parameters from Janma Rasi."""
        try:
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            data = await get_client().post(
                "/v1/astro/ghat-chakra", api_key, body, timeout=15.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Ghat Chakra", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ghat_chakra", exc)

"""Natal chart and extended chart tools (BPHS / Parashari foundations)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import (
    BirthData,
    DivisionalChartType,
    PrashnaInput,
    ResponseFormat,
    prashna_dict,
)
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


def _natal_table_md(data: dict[str, Any]) -> str:
    planets = data.get("planets") or data.get("positions")
    if planets is None and isinstance(data.get("chart"), dict):
        planets = data["chart"].get("planets")
    if isinstance(planets, list) and planets and isinstance(planets[0], dict):
        rows = []
        for p in planets:
            name = p.get("planet") or p.get("name") or p.get("graha") or "—"
            sign = p.get("sign") or p.get("rashi") or "—"
            house = p.get("house") or p.get("bhava") or "—"
            nak = p.get("nakshatra") or p.get("nakshatra_name") or "—"
            flags = []
            for k in (
                "combust",
                "retrograde",
                "vargottama",
                "debilitated",
                "exalted",
            ):
                if p.get(k):
                    flags.append(k.replace("_", " "))
            flag_s = ", ".join(flags) if flags else "—"
            rows.append(f"| {name} | {sign} | {house} | {nak} | {flag_s} |")
        if rows:
            return (
                "## Natal chart — planet table\n\n"
                "| Planet | Sign | House | Nakshatra | Flags |\n"
                "|--------|------|-------|-----------|-------|\n"
                + "\n".join(rows)
                + "\n\n### Full response\n\n"
                + structured_markdown("Details", data)
            )
    return structured_markdown("Natal chart", data)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_natal_chart",
        description=(
            "Compute the complete Vedic birth chart (Janam Kundali) for a person. "
            "Returns all nine planets (Grahas) with their sign, house, nakshatra, "
            "pada, combustion status, retrogression, Vargottama, and Dig Bala flags; "
            "the ascendant (Lagna) with exact degree; all twelve house cusps; and the "
            "Avakahada table (Varna, Vashya, Yoni, Gana, Nadi). Source: Swiss "
            "Ephemeris with Lahiri ayanamsa (or as specified). "
            "Use this as the mandatory first call for any personalised Jyotish "
            "analysis — every other natal tool depends on data this returns. "
            "Do not call strength, yogas, doshas, or dasha without calling this first."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_natal_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Compute full natal chart from BPHS-style calculations."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/natal", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                _natal_table_md,
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_natal_chart", exc)

    @mcp.tool(
        name="asterwise_get_divisional_chart",
        description=(
            "Compute a specific divisional (Varga) chart for a person. Each division "
            "reveals a distinct life domain: D2 (Hora) wealth polarity, D3 (Drekkana) "
            "siblings and courage, D4 (Chaturthamsa) property, D7 (Saptamsa) children, "
            "D9 (Navamsa) spouse and dharma — the most important varga after D1, "
            "D10 (Dasamsa) career and public standing, D12 (Dvadasamsa) parents, "
            "D16 (Shodasamsa) vehicles and comforts, D20 (Vimshamsa) spiritual "
            "practice, D24 (Chaturvimshamsa) education, D27 (Nakshatramsa) strengths, "
            "D30 (Trimshamsa) misfortunes and health, D40 (Khavedamsa) auspiciousness, "
            "D45 (Akshavedamsa) character, D60 (Shashtiamsa) past karma. "
            "Source: BPHS varga chapters. "
            "Use when you need to assess a specific domain rather than the whole chart."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_divisional_chart(
        ctx: Context,
        birth: BirthData,
        chart_type: DivisionalChartType,
        response_format: ResponseFormat
    ) -> str:
        """Compute divisional (varga) chart."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "chart_type": chart_type.value}
            data = await get_client().post("/v1/astro/divisional", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Divisional chart {chart_type.value}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_divisional_chart", exc)

    @mcp.tool(
        name="asterwise_get_chart_strength",
        description=(
            "Calculate Shadbala (six-fold planetary strength) and Bhavbala (house "
            "strength) for the natal chart. Shadbala measures each planet across six "
            "sources: Sthana (positional), Dig (directional), Kala (temporal), Chesta "
            "(motional), Naisargika (natural), and Drik (aspectual). Bhavbala measures "
            "each house. Source: BPHS strength chapters. "
            "Use when you need to rank planets by power, identify the strongest and "
            "weakest influences, or support a yoga/dasha assessment with quantitative "
            "backing. Do not confuse with asterwise_get_yogas — yogas identify "
            "configurations, strength measures raw planetary power."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_chart_strength(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Shadbala and Bhavbala."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/strength", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Chart strength (Shadbala / Bhavbala)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_chart_strength", exc)

    @mcp.tool(
        name="asterwise_get_special_ascendants",
        description=(
            "Get two key spiritual significators from the chart in a single call: "
            "(1) Atmakaraka — the planet with the highest degree in any sign, "
            "representing the soul's desire in this life (Jaimini system); "
            "(2) Ishta Devata — the personal deity revealed by the 12th lord from "
            "the Atmakaraka's Navamsa position (BPHS/Jaimini). "
            "Use when the user asks about spiritual path, personal deity, soul purpose, "
            "or life mission. This is a spiritual tool, not a predictive one. "
            "Do not call this for timing, health, career, or matchmaking questions."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_special_ascendants(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Atmakaraka and Ishta Devata (two API calls)."""
        try:
            api_key = await require_api_key(ctx)
            bd = birth.to_api_dict()
            atm = await get_client().post("/v1/astro/atmakaraka", api_key, bd, timeout=20.0)
            ishta = await get_client().post("/v1/astro/ishta-devta", api_key, bd, timeout=20.0)
            merged = {"atmakaraka": atm, "ishta_devata": ishta}

            def _md(d: dict[str, Any]) -> str:
                parts = [
                    "## Atmakaraka",
                    structured_markdown("Atmakaraka", atm),
                    "",
                    "## Ishta Devata",
                    structured_markdown("Ishta Devata", ishta),
                ]
                return "\n".join(parts)

            return format_tool_result(merged, response_format, _md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_special_ascendants", exc)

    @mcp.tool(
        name="asterwise_get_nakshatra_details",
        description=(
            "Look up reference information for any of the 27 nakshatras by name: "
            "ruling planet (Nakshatra lord), deity, symbol, Gana (Deva/Manushya/Rakshasa), "
            "Varna, Yoni, Nadi, pada meanings, and classical qualities. "
            "Source: Vedanga Jyotisha and classical nakshatra texts. "
            "Use when explaining a person's Moon nakshatra or Lagna nakshatra, when "
            "assessing nakshatra compatibility in matchmaking, or when a user asks "
            "about nakshatra symbolism. This is a reference lookup — it does not "
            "require birth data."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_nakshatra_details(
        ctx: Context,
        nakshatra_name: str,
        response_format: ResponseFormat
    ) -> str:
        """Nakshatra reference details."""
        try:
            api_key = await require_api_key(ctx)
            path = f"/v1/astro/nakshatra/{safe_segment(nakshatra_name)}"
            data = await get_client().get(path, api_key, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Nakshatra: {nakshatra_name}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_nakshatra_details", exc)

    @mcp.tool(
        name="asterwise_check_sade_sati",
        description=(
            "Check Sade Sati status — Saturn's 7.5-year transit through the sign "
            "before, the sign of, and the sign after the natal Moon. Returns: "
            "active/inactive status, current phase (rising/peak/setting if active), "
            "intensity score, start date, and projected end date. Always computed "
            "for today's date — not configurable for past or future dates. "
            "Use specifically when the user is experiencing unexplained delays, "
            "setbacks, or pressure and wants to know if Saturn is the cause. "
            "Do not use asterwise_get_gochar for this — Gochar shows all transits; "
            "this focuses exclusively on Saturn's Moon transit with full phase detail. "
            "Source: classical transit texts."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_check_sade_sati(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Sade Sati check."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/sade-sati", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Sade Sati", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_check_sade_sati", exc)

    @mcp.tool(
        name="asterwise_get_prashna_chart",
        description=(
            "Generate a Prashna (horary) chart for a question asked at this moment. "
            "Prashna Jyotish derives answers from the planetary positions at the time "
            "and place the question is asked — no birth chart required. Valid question "
            "categories: self (health/personality), wealth, siblings, property, "
            "children, health, marriage, death, travel, career, gains, loss. "
            "Source: Prashna Marga and classical horary texts. "
            "Use when the person has no birth data, or when they want an answer to a "
            "specific burning question independent of their natal chart. "
            "Do not use for ongoing life analysis — use asterwise_get_natal_chart for that."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_prashna_chart(
        ctx: Context,
        prashna: PrashnaInput
    ) -> str:
        """Prashna horary chart."""
        try:
            api_key = await require_api_key(ctx)
            rf = prashna.response_format
            data = await get_client().post(
                "/v1/astro/prashna", api_key, prashna_dict(prashna),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Prashna chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_prashna_chart", exc)

    @mcp.tool(
        name="asterwise_get_varshaphal",
        description=(
            "Calculate the Varshaphal (Solar Return) chart — cast for the exact "
            "moment the Sun returns to its natal degree each year. Reveals the year "
            "lord (Varsha Pati), Muntha position, and dominant planetary configuration "
            "for that twelve-month period. "
            "year parameter: pass the calendar year as a 4-digit integer (e.g. 2026), "
            "NOT the person's age. Passing age instead of year will produce incorrect "
            "results. "
            "Use when the user asks what a particular year holds. "
            "Do not confuse with asterwise_get_dasha (lifetime timing cycles) or "
            "asterwise_get_transits (transit events over a date range). "
            "Source: Varshaphal tradition (Tajika system)."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_varshaphal(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat
    ) -> str:
        """Varshaphal solar return."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "target_year": year}
            data = await get_client().post("/v1/astro/varshaphal", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Varshaphal ({year})", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_varshaphal", exc)

    @mcp.tool(
        name="asterwise_get_lal_kitab_chart",
        description=(
            "Get the Lal Kitab chart — a North Indian astrological tradition with its "
            "own distinct house placement rules, planet interpretation, and debt (Rin) "
            "analysis system. Planets placed in houses take on meanings specific to "
            "the Lal Kitab framework, which differs substantially from BPHS. "
            "Source: Lal Kitab (1952 edition). "
            "Use only when the user explicitly asks for Lal Kitab analysis or when "
            "a Lal Kitab-based app is being built. "
            "Do not mix Lal Kitab placements with BPHS interpretations — they use "
            "different logic and combining them produces incorrect analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_lal_kitab_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Lal Kitab chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/chart", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lal Kitab chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lal_kitab_chart", exc)

    @mcp.tool(
        name="asterwise_get_lal_kitab_remedies",
        description=(
            "Lal Kitab remedies per planet and house — includes debt (Rin) clearance "
            "rituals, charity prescriptions (feeding specific animals, distributing "
            "specific items), household-level practical actions, and planetary "
            "appeasement methods. Structurally different from classical Jyotish "
            "remedies — Lal Kitab does not use Sanskrit mantras or gemstones in the "
            "same framework. "
            "Use after asterwise_get_lal_kitab_chart for Lal Kitab-specific remedial "
            "measures. Do not use as a replacement for asterwise_get_remedies — "
            "that provides BPHS/Parashari remedies; this provides Lal Kitab remedies. "
            "Source: Lal Kitab texts (1952 edition)."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_lal_kitab_remedies(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Lal Kitab remedies."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/remedies", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lal Kitab remedies", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lal_kitab_remedies", exc)

    @mcp.tool(
        name="asterwise_get_kp_chart",
        description=(
            "Get the KP (Krishnamurti Paddhati) chart — a precision system for event "
            "timing that divides each nakshatra into sub-lords using the Vimshottari "
            "Dasha proportions. Returns planet positions with their star lord and "
            "sub-lord chains. Source: K.S. Krishnamurti's KP system. "
            "Use when the user needs precise timing of events (will the marriage happen "
            "this year? when will the job come?) rather than general life reading. "
            "KP is for event prediction with yes/no precision; BPHS is for character "
            "and life theme analysis. Use asterwise_get_kp_significators after this "
            "to get the house-wise event indicators."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_kp_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """KP chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/kp/chart", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_chart", exc)

    @mcp.tool(
        name="asterwise_get_kp_significators",
        description=(
            "Get KP house significators — for each house (or a specific house 1–12), "
            "the chain of planets that signify its matters through star-lord and "
            "sub-lord relationships. Source: KP system. "
            "Use after asterwise_get_kp_chart when you need to determine which planets "
            "are activated for a specific house matter (e.g. house 7 for marriage, "
            "house 10 for career, house 11 for gains). "
            "Omit house_number to get all twelve houses at once; specify it to focus "
            "on one house."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_kp_significators(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        house_number: int | None = None
    ) -> str:
        """KP significators."""
        try:
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = birth.to_api_dict()
            if house_number is not None:
                body["house_number"] = house_number
            data = await get_client().post("/v1/astro/kp/significators", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP significators", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_significators", exc)

    @mcp.tool(
        name="asterwise_get_kp_ruling_planets",
        description=(
            "Get the KP ruling planets for the current moment at a given location — "
            "the Moon's sign lord, star lord, and sub lord; the ascendant's sign lord, "
            "star lord, and sub lord. These six planets govern the moment and are used "
            "in KP to validate chart readings and timing. Source: KP ruling planets method. "
            "Use when doing a Prashna in the KP system, or when a KP astrologer needs "
            "the ruling planets for the moment. This tool takes only location (lat/lon), "
            "not birth data — it is about the current moment, not a natal chart."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_kp_ruling_planets(
        ctx: Context,
        lat: float,
        lon: float,
        response_format: ResponseFormat
    ) -> str:
        """KP ruling planets (time/location)."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/kp/ruling-planets",
                api_key,
                {"lat": lat, "lon": lon},
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP ruling planets", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_ruling_planets", exc)

    @mcp.tool(
        name="asterwise_get_ashtakavarga",
        description=(
            "Calculate Ashtakavarga — returns three layers: "
            "(1) Bhinna Ashtakavarga — per-planet Bindu scores in each sign; "
            "(2) Sarvashtakavarga — combined totals per sign (28+ Bindus = strong "
            "transit support; below 25 = difficulty for transiting planets); "
            "(3) Trikona and Ekadhipatya reduced tables — the tables most Jyotishis "
            "use for refined transit prediction. "
            "Use when assessing transit quality or building a transit strength feature. "
            "Do not confuse with asterwise_get_chart_strength — Shadbala measures "
            "natal planetary strength; Ashtakavarga measures transit receptivity. "
            "Source: BPHS Ashtakavarga chapters."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_ashtakavarga(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Ashtakavarga."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/ashtakavarga", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Ashtakavarga", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ashtakavarga", exc)

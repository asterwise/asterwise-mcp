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
    birth_dict,
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
            "Compute a complete Vedic natal chart (Kundli) for a person. Returns planet positions, "
            "signs, houses, nakshatras, combustion flags, Vargottama markers, Dig Bala, and ascendant "
            "details. Source: Brihat Parashara Hora Shastra (BPHS). Use this as the foundation for any "
            "Jyotish analysis.\n"
            "Inputs: BirthData (date, time, lat, lon, ayanamsa) and response_format.\n"
            "Returns: Markdown planet table or full JSON from the API."
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
                "/v1/astro/natal", api_key, birth_dict(birth),
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
            "Compute a specific divisional chart (Varga) for deeper analysis. D9 (Navamsa) for "
            "marriage/dharma, D10 (Dasamsa) for career, D7 for children, etc. Source: BPHS varga chapters.\n"
            "Inputs: BirthData, chart_type (D1–D60), response_format.\n"
            "Returns: Planet positions in the chosen divisional chart."
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
            body = {**birth_dict(birth), "chart_type": chart_type.value}
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
            "Calculate Shadbala (six-fold strength) and Bhavbala (house strength) for a natal chart. "
            "Reveals which planets and houses are powerful vs weak. Source: BPHS strength chapters.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Strength scores per planet and house."
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
            data = await get_client().post("/v1/astro/strength", api_key, birth_dict(birth),
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
            "Get Atmakaraka (soul significator planet) and Ishta Devata (personal deity) from the natal "
            "chart. Used for spiritual guidance and deeper self-understanding. Source: Jaimini / BPHS "
            "significator principles.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Combined atmakaraka and ishta devata sections."
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
            bd = birth_dict(birth)
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
            "Get detailed information about a specific nakshatra — deity, symbol, qualities, ruling "
            "planet, pada meanings, and classical interpretations. Source: Vedanga Jyotisha / classical "
            "nakshatra lists.\n"
            "Inputs: nakshatra_name, response_format.\n"
            "Returns: Nakshatra profile."
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
            "Check if a person is currently in Sade Sati (Saturn's 7.5-year transit over natal Moon). "
            "Returns phase (rising/peak/setting), intensity, and duration. Source: classical transit "
            "texts.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Sade Sati status and details."
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
            data = await get_client().post("/v1/astro/sade-sati", api_key, birth_dict(birth),
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
            "Generate a Prashna (horary) chart for a question asked at a specific moment. Prashna Jyotish "
            "answers questions from planetary positions at the moment of asking, without requiring a birth "
            "chart. Source: Prashna classics.\n"
            "Inputs: question, date, time, lat, lon, ayanamsa, response_format.\n"
            "Returns: Prashna chart and interpretation payload."
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
            "Calculate Varshaphal (Solar Return chart) — the chart cast for the moment the Sun returns to "
            "its natal degree each year. Reveals themes and events for that year of life. Source: "
            "Varshaphal tradition.\n"
            "Inputs: BirthData, year (age/year of interest), response_format.\n"
            "Returns: Solar return chart data."
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
            body = {**birth_dict(birth), "year": year}
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
            "Get Lal Kitab chart — a distinct North Indian astrological tradition with unique house "
            "placement rules and debt (rin) analysis. Source: Lal Kitab tradition.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Lal Kitab chart with planet placements."
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
                "/v1/astro/lal-kitab/chart", api_key, birth_dict(birth),
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
            "Get Lal Kitab remedies — practical remedies specific to the Lal Kitab tradition. Source: "
            "Lal Kitab texts.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Remedies per planet / house as returned by the API."
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
                "/v1/astro/lal-kitab/remedies", api_key, birth_dict(birth),
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
            "Get KP (Krishnamurti Paddhati) chart — sub-lord based astrology for event timing. Source: KP "
            "system.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: KP chart with sub-lords."
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
            data = await get_client().post("/v1/astro/kp/chart", api_key, birth_dict(birth),
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
            "Get KP significators for each house — sub-lord chains signifying house matters. Source: KP.\n"
            "Inputs: BirthData, optional house_number 1–12 (omit for all houses), response_format.\n"
            "Returns: Significator chains."
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
            body: dict[str, Any] = birth_dict(birth)
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
            "Get KP ruling planets for the current moment — Moon sign/star/sub lords and ascendant lords. "
            "Source: KP ruling planets method.\n"
            "Inputs: lat, lon, response_format.\n"
            "Returns: Current ruling planets."
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
            "Calculate Ashtakavarga — eightfold benefic points per sign for each planet and "
            "Sarvashtakavarga totals. Source: BPHS Ashtakavarga chapters.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Ashtakavarga tables."
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
            data = await get_client().post("/v1/astro/ashtakavarga", api_key, birth_dict(birth),
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

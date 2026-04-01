"""Numerology tools (Pythagorean, Chaldean, Lo Shu, and utilities)."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import ResponseFormat
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
        name="asterwise_get_numerology_profile",
        description=(
            "Full numerology profile — Life Path, Destiny, Soul Urge, Personality, Birthday, Personal Year. "
            "Source: Pythagorean numerology.\n"
            "Inputs: name (full at birth), date (YYYY-MM-DD), response_format.\n"
            "Returns: Core numbers with interpretations."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_numerology_profile(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Pythagorean profile."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/profile",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Numerology profile", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_numerology_profile", exc)

    @mcp.tool(
        name="asterwise_get_numerology_compatibility",
        description=(
            "Numerology compatibility from Life Path and Destiny numbers. Source: Pythagorean pairing rules.\n"
            "Inputs: person1_name, person1_date, person2_name, person2_date, response_format.\n"
            "Returns: Compatibility narrative."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_numerology_compatibility(
        ctx: Context,
        person1_name: str,
        person1_date: str,
        person2_name: str,
        person2_date: str,
        response_format: ResponseFormat
    ) -> str:
        """Two-person numerology compatibility."""
        try:
            api_key = await require_api_key(ctx)
            body = {
                "person1_name": person1_name,
                "person1_date": person1_date,
                "person2_name": person2_name,
                "person2_date": person2_date,
            }
            data = await get_client().post("/v1/numerology/compatibility", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Numerology compatibility", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_numerology_compatibility", exc)

    @mcp.tool(
        name="asterwise_get_chaldean_numerology",
        description=(
            "Chaldean numerology chart — distinct letter values from Pythagorean. Source: Chaldean system.\n"
            "Inputs: name, date, response_format.\n"
            "Returns: Chaldean analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_chaldean_numerology(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Chaldean chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/chaldean",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Chaldean numerology", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_chaldean_numerology", exc)

    @mcp.tool(
        name="asterwise_get_lo_shu_grid",
        description=(
            "Lo Shu magic square grid — missing/repeated digits and impact. Source: Chinese Lo Shu "
            "numerology.\n"
            "Inputs: date (YYYY-MM-DD), response_format.\n"
            "Returns: Grid analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_lo_shu_grid(
        ctx: Context,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Lo Shu grid."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/lo-shu",
                api_key,
                {"date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lo Shu grid", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lo_shu_grid", exc)

    @mcp.tool(
        name="asterwise_get_name_correction",
        description=(
            "Name correction suggestions for better harmony with birth date. Source: numerological name "
            "balancing.\n"
            "Inputs: name, date, response_format.\n"
            "Returns: Analysis and suggested spellings."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_name_correction(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Name correction."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/name-correction",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Name correction", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_name_correction", exc)

    @mcp.tool(
        name="asterwise_get_lucky_numbers",
        description=(
            "Lucky numbers derived from the numerology profile. Source: standard reduction methods.\n"
            "Inputs: name, date, response_format.\n"
            "Returns: Numbers and explanations."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_lucky_numbers(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Lucky numbers."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/lucky-numbers",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lucky numbers", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lucky_numbers", exc)

    @mcp.tool(
        name="asterwise_get_personal_year",
        description=(
            "Personal Year number — annual cycle theme. Source: Pythagorean yearly cycle.\n"
            "Inputs: name, date, response_format.\n"
            "Returns: Personal year and interpretation."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_personal_year(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Personal year."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/personal-year",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Personal year", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_personal_year", exc)

    @mcp.tool(
        name="asterwise_get_number_meaning",
        description=(
            "Meaning of numbers 1–9 and master numbers 11, 22, 33. Source: modern numerology synthesis.\n"
            "Inputs: number (1–33), response_format.\n"
            "Returns: Detailed meaning."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_number_meaning(
        ctx: Context,
        number: int,
        response_format: ResponseFormat
    ) -> str:
        """Number dictionary entry."""
        try:
            if number < 1 or number > 33:
                invalid_params(
                    "number must be between 1 and 33 (including master numbers 11, 22, 33)."
                )
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                f"/v1/numerology/meaning/{safe_segment(str(number))}",
                api_key,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Meaning of {number}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_number_meaning", exc)

    @mcp.tool(
        name="asterwise_check_mobile_number",
        description=(
            "Mobile number numerology vs owner profile. Source: digit-sum and Chaldean/Pythagorean checks.\n"
            "Inputs: mobile_number, name, date, response_format.\n"
            "Returns: Compatibility analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_check_mobile_number(
        ctx: Context,
        mobile_number: str,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Mobile number check."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/mobile-number",
                api_key,
                {"number": mobile_number, "name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Mobile number analysis", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_check_mobile_number", exc)

    @mcp.tool(
        name="asterwise_check_vehicle_number",
        description=(
            "Vehicle registration number vs owner numerology. Source: digit analysis.\n"
            "Inputs: vehicle_number, name, date, response_format.\n"
            "Returns: Compatibility analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_check_vehicle_number(
        ctx: Context,
        vehicle_number: str,
        name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Vehicle number check."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/vehicle-number",
                api_key,
                {"number": vehicle_number, "name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Vehicle number analysis", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_check_vehicle_number", exc)

    @mcp.tool(
        name="asterwise_get_business_name_analysis",
        description=(
            "Business name numerology vs founder birth date. Source: expression and compatibility checks.\n"
            "Inputs: business_name, date (founder), response_format.\n"
            "Returns: Business name report."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_business_name_analysis(
        ctx: Context,
        business_name: str,
        date: str,
        response_format: ResponseFormat
    ) -> str:
        """Business name."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/business-name",
                api_key,
                {"name": business_name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Business name analysis", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_business_name_analysis", exc)

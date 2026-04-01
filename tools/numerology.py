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
            "Calculate the complete Pythagorean numerology profile for a person: "
            "Life Path number (most important — derived from birth date by full "
            "reduction), Destiny/Expression number (full birth name), Soul Urge "
            "number (vowels only), Personality number (consonants only), Birthday "
            "number (day of birth), Maturity number (Life Path + Destiny), and "
            "Personal Year number for the current year. Source: Pythagorean system. "
            "Use this as the primary numerology tool — call this first for any "
            "comprehensive numerology reading. "
            "Use asterwise_get_chaldean_numerology if the user specifically asks for "
            "Chaldean analysis (different letter values, different results)."
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
            "Calculate numerology compatibility between two people based on their "
            "Life Path and Destiny numbers — which combinations are naturally "
            "harmonious, which require work, and which are challenging. "
            "Source: Pythagorean pairing compatibility tradition. "
            "Use when a user asks how two people are numerologically matched, or "
            "when building a numerology-based compatibility feature. "
            "This does not require birth time or location — name and date only."
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
            "Calculate Chaldean numerology — an older system originating in ancient "
            "Babylon with different letter-number assignments than Pythagorean. "
            "In Chaldean, letters 1–8 are used (9 is sacred and not assigned); "
            "the name compound number and root number carry distinct meanings. "
            "Source: Chaldean system. "
            "Use when the user specifically asks for Chaldean numerology, or when "
            "cross-checking a Pythagorean reading with the older system. "
            "Do not use as a replacement for asterwise_get_numerology_profile — "
            "the two systems give different results and serve different purposes."
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
            "Calculate the Lo Shu magic square grid from a birth date — arranging "
            "the digits of the date in a 3x3 grid. Missing numbers indicate absent "
            "qualities; repeated numbers indicate overemphasis. Used in Chinese "
            "numerology and also in some modern Jyotish systems. "
            "Source: Chinese Lo Shu tradition. "
            "Use when the user asks for Lo Shu analysis specifically. "
            "This takes only a date — no name required."
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
            "Analyse whether the current spelling of a name is numerologically "
            "harmonious with the birth date, and suggest corrected or alternative "
            "spellings that create better alignment. Based on Life Path compatibility "
            "with the Expression number. Source: numerological name balancing tradition. "
            "Use when the user wants to know if their name's numerology supports "
            "their birth number, or when they want to try alternative spellings "
            "for better energy alignment."
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
            "Derive lucky numbers for a person from their numerology profile — "
            "primary lucky number (Life Path), secondary numbers, and numbers to "
            "avoid. Source: standard Pythagorean reduction methods. "
            "Use when the user asks for their lucky numbers, or when building a "
            "feature that incorporates personalised numerology guidance."
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
            "Calculate the Personal Year number for a specific year — derived from "
            "the birth month, birth day, and the target year. Each number 1–9 "
            "represents a distinct annual theme: 1 (new beginnings), 2 (cooperation), "
            "3 (creativity), 4 (foundation), 5 (change), 6 (responsibility), "
            "7 (reflection), 8 (power and material), 9 (completion). "
            "Source: Pythagorean annual cycle. "
            "Use when a user asks 'what kind of year is this for me?' or 'what "
            "does my numerology say about 2026?' "
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
            "Look up the classical meaning of a specific number (1–9) or master "
            "number (11, 22, 33) — including its core qualities, strengths, "
            "challenges, life themes, and archetypal character. "
            "Source: modern numerology synthesis. "
            "Use as a reference lookup when explaining what a Life Path 7 means, "
            "or what master number 11 represents. This does not require name or date."
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
            "Analyse whether a mobile phone number is numerologically compatible "
            "with its owner — by reducing the number to its root and checking "
            "alignment with the owner's Life Path and Destiny numbers. "
            "Source: Pythagorean and Chaldean digit analysis. "
            "Use when a user wants to know if their mobile number is lucky for them, "
            "or when helping someone choose between two phone numbers."
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
            "Analyse whether a vehicle registration number is numerologically "
            "compatible with its owner. Source: digit-sum analysis. "
            "Use when a user wants to know if their vehicle number suits them, "
            "or when choosing between registration options."
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
            "Analyse whether a business name is numerologically favourable for a "
            "founder — checking the Expression number of the business name against "
            "the founder's Life Path and Destiny numbers. Suggests adjustments if "
            "the alignment is weak. Source: expression and compatibility numerology. "
            "Use when a user is naming a new business or rebranding and wants "
            "numerological validation of the name choice."
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

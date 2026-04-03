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
        description='Calculate the complete Pythagorean numerology profile: Life Path\n(birth date full reduction), Destiny/Expression (full name), Soul Urge\n(vowels), Personality (consonants), Birthday (day of birth), and\nPinnacles/Challenges cycle. Use this as the primary numerology tool —\ncall first for any comprehensive numerology reading.\n\nOUTPUT CONTRACT (response_format=json):\ndata.life_path — { number, reduced_number, is_master_number (bool),\n  is_karmic_debt (bool), karmic_debt_number (int or null),\n  interpretation, keywords[] }\nSame shape for: data.expression, data.soul_urge, data.personality,\ndata.birth_day\ndata.personal_year — currently null (use asterwise_get_personal_year\n  for Personal Year calculation)\ndata.pinnacles[] — 4 objects: number, start_age, end_age,\n  interpretation, focus_areas[]\ndata.challenges[] — 4 objects: same shape\ndata.lucky_numbers[] (int array)\ndata.summary (string), data.key_traits[] (string array)\n\nERROR CONTRACT: Invalid date format → 422. Empty name → 422.\n\nUse asterwise_get_chaldean_numerology if the user specifically asks\nfor Chaldean analysis. Do not confuse — Pythagorean and Chaldean use\ndifferent letter assignments and produce different results.',
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
        description="Calculate numerology compatibility between two people based on their\nLife Path numbers. Returns a compatibility score, level, strengths,\nchallenges, and advice. Name and date only — no birth time or location\nrequired. Source: Pythagorean pairing compatibility tradition.\n\nOUTPUT CONTRACT (response_format=json):\ndata.life_path_1 (int), data.life_path_2 (int)\ndata.compatibility_score (int 1–10)\ndata.compatibility_level (string: 'Excellent', 'Good', 'Average',\n  'Challenging')\ndata.interpretation (string)\ndata.strengths[] (string array)\ndata.challenges[] (string array)\ndata.advice (string)\n\nERROR CONTRACT: Invalid date format → 422. Empty name → 422.\n\nFor astrological compatibility use asterwise_get_compatibility,\nasterwise_get_porutham, or asterwise_get_dashakoot.",
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
        description="Calculate Chaldean numerology — the ancient Babylonian system where\nletters are assigned values 1–8 (9 is sacred and unassigned). Returns\nthe compound number and root number for the name, plus the birth number.\nSource: Chaldean system.\n\nOUTPUT CONTRACT (response_format=json):\ndata.system ('chaldean'), data.full_name, data.birth_date\ndata.name_number — { raw (int, compound), reduced (int, root),\n  theme, keywords[], interpretation }\ndata.birth_number — { raw, reduced, theme, keywords[], interpretation }\ndata.compound_number — { raw (name+birth combined), reduced,\n  theme, keywords[], interpretation }\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nUse as a secondary system alongside asterwise_get_numerology_profile,\nnot as a replacement. The two systems produce different results.",
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
        description="Calculate the Lo Shu magic square grid from a birth date — the Chinese\n3×3 numerological grid. Missing numbers indicate absent qualities;\nrepeated numbers indicate overemphasis. Date only — no name required.\nSource: Chinese Lo Shu tradition.\n\nOUTPUT CONTRACT (response_format=json):\ndata.birth_date\ndata.grid — 3×3 nested int array (row-major, top-to-bottom). Each\n  cell contains a count of how many times that position's number\n  appears in the birth date digits. 0 = number absent.\n  Grid positions map to: row0=[4,9,2], row1=[3,5,7], row2=[8,1,6]\ndata.present_numbers[] (int array)\ndata.missing_numbers[] (int array)\ndata.repeated_numbers[] (int array — numbers appearing 2+ times)\ndata.plane_analysis — { thought_plane, will_plane, action_plane,\n  golden_yod, silver_yod } — each: numbers[], description,\n  complete (bool)\ndata.number_analysis{} — keyed by '1'–'9': count (int), plane,\n  trait, status ('missing', 'present', or 'strong'), note\n\nEdge case: birth dates with zeros (e.g. 2000-01-01) — zeros are not\nplaced in the grid (Lo Shu uses digits 1–9 only).\n\nERROR CONTRACT: Invalid date → 422.",
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
        description="Analyse whether the current spelling of a name is numerologically\nharmonious with the birth date, and suggest alternative spellings\nwith better alignment. Based on Life Path vs Expression number\ncompatibility. Source: numerological name balancing tradition.\n\nOUTPUT CONTRACT (response_format=json):\ndata.full_name, data.birth_date, data.life_path (int)\ndata.current_name — { name, expression (int), soul_urge (int),\n  personality (int), is_master (bool), karmic_debt (int or null),\n  compatibility (string: 'harmonious', 'neutral', or 'challenging'),\n  harmony_score (int 1–5) }\ndata.alternatives[] — array of alternative spellings, each with\n  same shape as current_name. If no better-aligned alternative exists,\n  alternatives is an empty array — not an error.\ndata.recommendation (currently null — stub)\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nFor business name analysis use asterwise_get_business_name_analysis.",
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
        description='Derive lucky numbers for a person from their numerology profile —\nprimary lucky number (Life Path), secondary lucky numbers, and numbers\nto avoid. Source: Pythagorean reduction methods.\n\nOUTPUT CONTRACT (response_format=json):\ndata.lucky_numbers[] (int array — primary and secondary lucky numbers)\ndata.power_number (int — the Life Path number, most significant)\ndata.date_specific (bool — false; numbers are derived from the profile,\n  not a specific date)\ndata.interpretation (string)\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nNote: asterwise_get_numerology_profile already returns lucky_numbers[]\nin the same format. Use this tool when you need only the lucky numbers\nwithout the full profile to reduce response size.',
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
        description="Calculate the Personal Year number for a specific target year —\nderived from birth month, birth day, and the target year. Each number\n1–9 represents a distinct annual theme. Source: Pythagorean annual cycle.\n\nOUTPUT CONTRACT: Schema not yet confirmed from live response —\nendpoint was recently fixed. Expected fields based on the tool design:\npersonal_year_number, theme, interpretation, advice,\nfavorable_actions[], challenges[].\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nNote: asterwise_get_numerology_profile already returns the current\nyear's Personal Year in the personal_year field when implemented.\nUse this tool specifically when you need the Personal Year for a\ndifferent target year.",
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
        description="Look up the classical meaning of a specific number (1–9) or master\nnumber (11, 22, 33) — core qualities, life themes, strengths,\nchallenges, and archetypal character. No name or date required.\nSource: modern numerology synthesis.\n\nOUTPUT CONTRACT (response_format=json):\ndata.number (int)\ndata.context ('general')\ndata.interpretation (string)\ndata.keywords[] (string array)\ndata.theme (currently null — stub)\ndata.opportunities[] (currently empty — stub)\ndata.challenges[] (currently empty — stub)\ndata.advice (currently null — stub)\n\nERROR CONTRACT: Number outside supported range → 422.",
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
        description="Analyse whether a mobile phone number is numerologically compatible\nwith its owner — reduces the number to its root digit and checks\nalignment with the owner's Life Path and Destiny numbers.\nSource: Pythagorean and Chaldean digit analysis.\n\nAccepts multiple formats: '9876543210', '+91-9876543210', '+91 98765 43210'.\nNon-digit characters (spaces, dashes, plus signs) are stripped before\nreduction. The country code digits (+91) ARE included in the reduction.\n\nOUTPUT CONTRACT (response_format=json):\ndata.input (the number as submitted)\ndata.input_type ('mobile')\ndata.total (int — sum of all digits)\ndata.single_digit (int — Pythagorean root, 1–9)\ndata.is_master (bool — true if total reduces to 11, 22, or 33)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int 1–10)\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nUse asterwise_check_vehicle_number for vehicle registration numbers.",
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
        description="Analyse whether a vehicle registration number is numerologically\ncompatible with its owner. Source: digit-sum analysis.\n\nAccepts standard Indian registration format (e.g. MH01AB1234) and\ninternational formats. Non-digit characters are stripped; only the\nnumeric portion is used for reduction.\n\nOUTPUT CONTRACT (response_format=json):\ndata.input (the number as submitted)\ndata.input_type ('vehicle')\ndata.total (int — sum of numeric digits only)\ndata.single_digit (int — root number)\ndata.is_master (bool)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int 1–10)\n\nERROR CONTRACT: Same as asterwise_get_numerology_profile.\n\nUse asterwise_check_mobile_number for phone numbers.",
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
        description="Analyse whether a business name is numerologically favourable for\na founder — computes the Expression number of the business name\nand checks alignment with the founder's birth date numerology.\nSource: numerological name compatibility tradition.\n\nOUTPUT CONTRACT (response_format=json):\ndata.input (the business name as submitted)\ndata.input_type ('business_name')\ndata.expression_number (int, full compound before reduction)\ndata.single_digit (int, reduced root number — may equal expression_number\n  for master numbers 11, 22, 33)\ndata.is_master (bool — true for 11, 22, 33)\ndata.theme (string)\ndata.favourable_for[] (string array, suitable business domains)\ndata.caution (string, guidance on the number's challenges)\ndata.harmony_score (int 1–10)\n\nERROR CONTRACT: Empty business_name → 422. Invalid date → 422.\nBusiness names with numbers or special characters are accepted —\nnon-letter characters are stripped before numerological reduction.\n\nFor personal name analysis use asterwise_get_name_correction.",
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

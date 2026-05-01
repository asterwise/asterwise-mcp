"""Numerology tools (Pythagorean, Chaldean, Lo Shu, and utilities)."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import ResponseFormat
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
    @mcp.tool(
        name="asterwise_get_numerology_profile",
        description="Builds a Pythagorean numerology profile from a legal name and birth date and returns core numbers, cycles, lucky digits, and summary copy.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes Life Path, Expression, Soul Urge, Personality, Birthday, Pinnacles, Challenges, lucky_numbers[], summary, and key_traits via the upstream profile engine. data.personal_year is currently null — use asterwise_get_personal_year for the dedicated Personal Year endpoint. It is not Chaldean mapping (asterwise_get_chaldean_numerology), Lo Shu grids (asterwise_get_lo_shu_grid), or paired compatibility (asterwise_get_numerology_compatibility).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_personal_year — fills Personal Year when needed.\n\nSECTION: INPUT CONTRACT\nname and date strings are forwarded without extra local validation; malformed payloads fail upstream.\n\nSECTION: OUTPUT CONTRACT\nFor each of data.life_path, data.expression, data.soul_urge, data.personality, data.birth_day:\n  number (int)\n  reduced_number (int)\n  is_master_number (bool)\n  is_karmic_debt (bool)\n  karmic_debt_number (int or null)\n  interpretation (string)\n  keywords[] (string array)\ndata.personal_year — currently null — use asterwise_get_personal_year for Personal Year calculation\ndata.pinnacles[] — four objects: number (int), start_age (int), end_age (int), interpretation (string), focus_areas[] (string array)\ndata.challenges[] — four objects with the same shape as pinnacles[]\ndata.lucky_numbers[] (int array)\ndata.summary (string)\ndata.key_traits[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — personal_year field is null here by design.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_chaldean_numerology — Chaldean letter values and compound structure, not Pythagorean cores.\nasterwise_get_lucky_numbers — lightweight lucky list without the full profile payload.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Compares two people on Pythagorean Life Path numbers derived from their names and birth dates and returns a score, tier label, narrative, strengths, challenges, and advice.\n\nSECTION: WHAT THIS TOOL COVERS\nPairwise numerology only — no charts, rashis, or kootas. Outputs discrete compatibility_score 1..10 with textual bands. It does not run asterwise_get_compatibility (Jyotish matchmaking) or regional porutham tools.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile per person — sanity-check Life Paths before comparing.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nFour strings (two names, two dates) are passed through without local guards.\n\nSECTION: OUTPUT CONTRACT\ndata.life_path_1 (int)\ndata.life_path_2 (int)\ndata.compatibility_score (int — 1 through 10)\ndata.compatibility_level (string — 'Excellent', 'Good', 'Average', or 'Challenging')\ndata.interpretation (string)\ndata.strengths[] (string array)\ndata.challenges[] (string array)\ndata.advice (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — For Vedic matching, use asterwise_get_compatibility instead.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_compatibility — sidereal koota scoring, not numerology integers.\nasterwise_get_numerology_profile — single-person profile, not dyad scoring.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Reduces a name and birth date through the Chaldean letter-value system and returns name, birth, and combined compound analyses with themes and keywords.\n\nSECTION: WHAT THIS TOOL COVERS\nChaldean assigns letters values one through eight (nine treated as sacred/unassigned in tradition). Response includes data.system 'chaldean', echoed full_name and birth_date, plus three parallel number objects (name, birth, compound) each with raw compound, reduced root, theme, keywords, interpretation. It does not output Pythagorean Life Path blocks (asterwise_get_numerology_profile) or Lo Shu grids.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_numerology_profile — compare against Pythagorean cores if needed.\n\nSECTION: INPUT CONTRACT\nname and date forwarded as-is; no local validation.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'chaldean')\ndata.full_name (string)\ndata.birth_date (string)\ndata.name_number:\n  raw (int — compound)\n  reduced (int — root)\n  theme (string)\n  keywords[] (string array)\n  interpretation (string)\ndata.birth_number — same shape as data.name_number\ndata.compound_number — same shape; raw combines name and birth\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Chaldean and Pythagorean numbers disagree by design — never merge blindly.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — Pythagorean Life Path / Expression stack, not Chaldean compounds.\nasterwise_get_lo_shu_grid — digit placement magic square, not Chaldean name reduction.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Derives a Lo Shu three-by-three frequency grid from birth-date digits and annotates planes, missing or repeated digits, and per-digit traits.\n\nSECTION: WHAT THIS TOOL COVERS\nChinese Lo Shu analysis: counts how often each digit one through nine appears in the date string, lays counts into the classical magic-square positions, and adds plane_analysis plus number_analysis entries keyed by digit strings '1'..'9'. Zero digits are ignored for placement. It does not compute Pythagorean Life Path (asterwise_get_numerology_profile) or Chaldean compounds.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\ndate string only; validated upstream.\n\nSECTION: OUTPUT CONTRACT\ndata.birth_date (string)\ndata.grid — three-by-three nested int array (row-major):\n  row positions map to numbers [4,9,2], [3,5,7], [8,1,6] respectively; cell value = count of that digit in the date (0 if absent)\ndata.present_numbers[] (int array)\ndata.missing_numbers[] (int array)\ndata.repeated_numbers[] (int array — digits appearing at least twice)\ndata.plane_analysis:\n  thought_plane — { numbers[] (int array), description (string), complete (bool) }\n  will_plane — same shape\n  action_plane — same shape\n  golden_yod — same shape\n  silver_yod — same shape\ndata.number_analysis{} — keys '1' through '9' (string keys):\n  count (int)\n  plane (string)\n  trait (string)\n  status (string — 'missing', 'present', or 'strong')\n  note (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Zeros in ISO dates are skipped — only digits one through nine populate the grid.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — letter-based Western numbers, not digit-frequency Lo Shu.\nasterwise_get_name_correction — spelling harmonics, not birth-date grids.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Scores the current spelling of a personal name against the birth-date Life Path, suggests alternate spellings with harmony metrics, and echoes recommendation stub fields.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns data.current_name metrics (expression, soul urge, personality, master and karmic flags, compatibility band, harmony_score 1..5) plus data.alternatives[] with identical shape per suggestion. data.recommendation is currently null (stub). Empty alternatives[] means no better spelling was found — still success. Not for business entities (asterwise_get_business_name_analysis) or mobile/vehicle checks.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — baseline numbers before renaming advice.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nname and date strings only; upstream validates.\n\nSECTION: OUTPUT CONTRACT\ndata.full_name (string)\ndata.birth_date (string)\ndata.life_path (int)\ndata.current_name:\n  name (string)\n  expression (int)\n  soul_urge (int)\n  personality (int)\n  is_master (bool)\n  karmic_debt (int or null)\n  compatibility (string — 'harmonious', 'neutral', or 'challenging')\n  harmony_score (int — 1 through 5)\ndata.alternatives[] — objects matching data.current_name shape\ndata.recommendation (currently null — stub)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Empty alternatives[] is valid when no improvement exists.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_business_name_analysis — entity Expression scan, not personal spelling alternatives.\nasterwise_get_chaldean_numerology — Chaldean compounds, not harmony-scored spelling list.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Fetches condensed lucky-number guidance for a name and birth date including primary and secondary picks, power number, interpretation, and a date_specific flag.\n\nSECTION: WHAT THIS TOOL COVERS\nThin numerology endpoint mirroring lucky_numbers[] from the full profile but omitting pinnacles, challenges, and long interpretations. data.date_specific is always false (profile-derived). Use when payload size matters. It is not the full profile (asterwise_get_numerology_profile) nor Lo Shu counts (asterwise_get_lo_shu_grid).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_numerology_profile — if deeper context is required.\n\nSECTION: INPUT CONTRACT\nname and date forwarded upstream without local checks.\n\nSECTION: OUTPUT CONTRACT\ndata.lucky_numbers[] (int array — primary and secondary values)\ndata.power_number (int — Life Path anchor)\ndata.date_specific (bool — always false; derived from profile)\ndata.interpretation (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Duplicates asterwise_get_numerology_profile lucky list — choose this tool for smaller JSON only.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — full multi-section profile, not lucky-number-only payload.\nasterwise_get_number_meaning — dictionary entry for one integer, not personalised lucky sets.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Looks up the Personal Year theme for the current calendar cycle from a name and birth date using only month and day inputs server-side.\n\nSECTION: WHAT THIS TOOL COVERS\nEndpoint returns Personal Year data derived from birth month/day against the running calendar year on the server — there is no extra year argument in the tool schema. Expected response keys (pending live confirmation): personal_year_number (int), theme (string), interpretation (string), advice (string), favorable_actions[] (string array), challenges[] (string array). asterwise_get_numerology_profile leaves personal_year null; use this tool when Personal Year detail is required.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — see other core numbers first.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nOnly name and date are submitted; the active calendar year is chosen upstream automatically.\n\nSECTION: OUTPUT CONTRACT\npersonal_year_number (int) — expected\ntheme (string) — expected\ninterpretation (string) — expected\nadvice (string) — expected\nfavorable_actions[] (string array) — expected\nchallenges[] (string array) — expected\n(Schema not yet confirmed from live response; fields above reflect tool design.)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Cannot request arbitrary calendar years via this tool — only the server-selected current year.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — personal_year field there is null; this endpoint supplies the annual theme.\nasterwise_get_varshaphal — Vedic solar return, not Pythagorean Personal Year.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Returns dictionary-style numerology copy for a single integer, including interpretation, keywords, and stubbed extended fields.\n\nSECTION: WHAT THIS TOOL COVERS\nStatic reference for any whole number from one through thirty-three inclusive (includes master numbers eleven, twenty-two, thirty-three plus every intermediate value). No name or date. data.theme, data.advice, data.opportunities[], and data.challenges[] are stubs (null or empty). Not personalised profiling (asterwise_get_numerology_profile).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nnumber must pass local guard: inclusive range one through thirty-three; values outside that band raise MCP INVALID_PARAMS before the HTTP call.\n\nSECTION: OUTPUT CONTRACT\ndata.number (int)\ndata.context (string — 'general')\ndata.interpretation (string)\ndata.keywords[] (string array)\ndata.theme (currently null — stub)\ndata.opportunities[] (currently empty — stub)\ndata.challenges[] (currently empty — stub)\ndata.advice (currently null — stub)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — number less than 1 or greater than 33 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — further rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Accepts every integer in the inclusive one..thirty-three range, not only master numbers.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — computes personal numbers from name and date, not a static dictionary row.\nasterwise_get_lucky_numbers — personalised lucky list, not reference meanings.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Digit-strips a mobile string (keeping country code digits), reduces it with the owner's name and birth date, and returns harmonic scoring plus interpretive copy.\n\nSECTION: WHAT THIS TOOL COVERS\nAccepts formats like bare ten digits, plus-country-code with spaces or hyphens; all non-digits drop out before summation and country code digits count toward totals. Compares against owner numerology via upstream rules. Not for vehicle plates (asterwise_check_vehicle_number) or business names.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — anchor Life Path before judging the line.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nFormatting noise is ignored; only digits contribute. Country code digits are included in the reduction sum.\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — submitted number)\ndata.input_type (string — 'mobile')\ndata.total (int — sum of all retained digits)\ndata.single_digit (int — Pythagorean root, one through nine)\ndata.is_master (bool — true when total reduces to eleven, twenty-two, or thirty-three)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Plus signs and punctuation do not affect digit extraction.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_check_vehicle_number — plate digit rules, not SIM numbering.\nasterwise_get_business_name_analysis — letter Expression scan, not phone roots.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Strips non-digits from a vehicle registration token, reduces the numeric run with owner name and birth date, and returns the same harmony schema as mobile analysis.\n\nSECTION: WHAT THIS TOOL COVERS\nHandles Indian pattern plates (e.g. MH01AB1234) and international variants; only digits feed totals. Produces vehicle-specific input_type. Does not analyse phone numbers (asterwise_check_mobile_number) or business names.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — owner baseline.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nLetters and separators are ignored; reduction uses numeric digits only.\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — submitted plate)\ndata.input_type (string — 'vehicle')\ndata.total (int — sum of numeric digits)\ndata.single_digit (int — root)\ndata.is_master (bool)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Alphabetic segments are decorative for numerology here — only digits matter.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_check_mobile_number — phone digit rules including country codes.\nasterwise_get_business_name_analysis — evaluates business Expression, not registration digits.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Reduces a business name to Expression and root digits against a founder birth date and returns thematic suitability lists plus a harmony score.\n\nSECTION: WHAT THIS TOOL COVERS\nAllows numerals and punctuation in the brand string — non-letters drop before letter-value reduction. Returns business-facing favourable domains, caution copy, and scoring. Not personal spelling optimisation (asterwise_get_name_correction) nor vehicle or phone checks.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_name_correction — if the entity is a person, not a brand.\n\nSECTION: INPUT CONTRACT\nSpecial characters and digits are acceptable; reduction strips non-letters per upstream rules. No local validation on name or date.\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — business name as submitted)\ndata.input_type (string — 'business_name')\ndata.expression_number (int — compound before reduction)\ndata.single_digit (int — reduced root; equals expression_number for master totals eleven, twenty-two, thirty-three)\ndata.is_master (bool)\ndata.theme (string)\ndata.favourable_for[] (string array — suitable domains)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Brand strings with emojis or digits still flow through upstream stripping rules.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_name_correction — personal spelling alternatives, not corporate Expression scoring.\nasterwise_check_mobile_number — numeric line analysis, not brand letters.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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

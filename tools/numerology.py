"""Numerology tools (Pythagorean, Chaldean, Lo Shu, and utilities)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from fastmcp import Context, FastMCP
from pydantic import Field


import mcp.types as mcp_types

from client import get_client, safe_segment
from models import ResponseFormat
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_numerology_profile",
        title="Numerology Profile",
        description=compact_description("asterwise_get_numerology_profile", "Builds a Pythagorean numerology profile from a legal name and birth date and returns core numbers, cycles, lucky digits, and summary copy.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes Life Path, Expression, Soul Urge, Personality, Birthday, Pinnacles, Challenges, lucky_numbers[], summary, and key_traits via the upstream profile engine. data.personal_year is currently null — use asterwise_get_personal_year for the dedicated Personal Year endpoint. It is not Chaldean mapping (asterwise_get_chaldean_numerology), Lo Shu grids (asterwise_get_lo_shu_grid), or paired compatibility (asterwise_get_numerology_compatibility).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_personal_year — fills Personal Year when needed.\n\nSECTION: INPUT CONTRACT\nname and date strings are forwarded without extra local validation; malformed payloads fail upstream.\n\nSECTION: OUTPUT CONTRACT\nFor each of data.life_path, data.expression, data.soul_urge, data.personality, data.birth_day:\n  number (int, or a string like '13/4' when a karmic debt is present)\n  reduced_number (int)\n  is_master_number (bool)\n  is_karmic_debt (bool)\n  karmic_debt_number (int or null — 13/14/16/19 met anywhere in the reduction; when present, number is a string like '13/4')\n  interpretation (string)\n  keywords[] (string array)\ndata.personal_year — currently null — use asterwise_get_personal_year for Personal Year calculation\ndata.pinnacles[] — four objects: number (int), start_age (int), end_age (int), interpretation (string), focus_areas[] (string array)\ndata.challenges[] — four objects with the same shape as pinnacles[]\ndata.lucky_numbers[] (int array)\ndata.summary (string)\ndata.key_traits[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error with details[].issue = no_letters when the name has no letters A-Z (e.g. '123', '!!!', or a name written only in a non-Latin script) — ask the user for the name spelled in Latin letters; this is not a server fault.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — personal_year field is null here by design.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_chaldean_numerology — Chaldean letter values and compound structure, not Pythagorean cores.\nasterwise_get_lucky_numbers — lightweight lucky list without the full profile payload."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_numerology_profile(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Pythagorean profile."""
        async with tool_guard("asterwise_get_numerology_profile"):
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
    @mcp.tool(
        name="asterwise_get_numerology_compatibility",
        title="Numerology Compatibility",
        description=compact_description("asterwise_get_numerology_compatibility", "Compares two people on Pythagorean Life Path numbers derived from their names and birth dates and returns a score, tier label, narrative, strengths, challenges, and advice.\n\nSECTION: WHAT THIS TOOL COVERS\nPairwise numerology only — no charts, rashis, or kootas. Outputs discrete compatibility_score 1..10 with textual bands. It does not run asterwise_get_compatibility (Jyotish matchmaking) or regional porutham tools.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile per person — sanity-check Life Paths before comparing.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nFour strings (two names, two dates) are passed through without local guards.\n\nSECTION: OUTPUT CONTRACT\ndata.life_path_1 (int)\ndata.life_path_2 (int)\ndata.compatibility_score (int — 1 through 10)\ndata.compatibility_level (string — 'Excellent', 'Good', 'Average', or 'Challenging')\ndata.interpretation (string)\ndata.strengths[] (string array)\ndata.challenges[] (string array)\ndata.advice (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — For Vedic matching, use asterwise_get_compatibility instead.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_compatibility — sidereal koota scoring, not numerology integers.\nasterwise_get_numerology_profile — single-person profile, not dyad scoring."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_numerology_compatibility(
        ctx: Context,
        person1_name: str,
        person1_date: str,
        person2_name: str,
        person2_date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Two-person numerology compatibility."""
        async with tool_guard("asterwise_get_numerology_compatibility"):
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
    @mcp.tool(
        name="asterwise_get_chaldean_numerology",
        title="Chaldean Numerology",
        description=compact_description("asterwise_get_chaldean_numerology", "Reduces a name and birth date through the Chaldean letter-value system and returns name, birth, and combined compound analyses with themes and keywords.\n\nSECTION: WHAT THIS TOOL COVERS\nChaldean assigns letters values one through eight (nine treated as sacred/unassigned in tradition). Response includes data.system 'chaldean', echoed full_name and birth_date, plus three parallel number objects (name, birth, compound) each with raw compound, reduced root, theme, keywords, interpretation. It does not output Pythagorean Life Path blocks (asterwise_get_numerology_profile) or Lo Shu grids.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_numerology_profile — compare against Pythagorean cores if needed.\n\nSECTION: INPUT CONTRACT\nname and date forwarded as-is; no local validation.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'chaldean')\ndata.full_name (string)\ndata.birth_date (string)\ndata.name_number:\n  raw (int — compound)\n  reduced (int — root)\n  theme (string)\n  keywords[] (string array)\n  interpretation (string)\ndata.birth_number — same shape as data.name_number\ndata.compound_number — same shape; raw combines name and birth\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error with details[].issue = no_letters when the name has no letters A-Z (e.g. '123', '!!!', or a name written only in a non-Latin script) — ask the user for the name spelled in Latin letters; this is not a server fault.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Chaldean and Pythagorean numbers disagree by design — never merge blindly.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — Pythagorean Life Path / Expression stack, not Chaldean compounds.\nasterwise_get_lo_shu_grid — digit placement magic square, not Chaldean name reduction."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_chaldean_numerology(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Chaldean chart."""
        async with tool_guard("asterwise_get_chaldean_numerology"):
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
    @mcp.tool(
        name="asterwise_get_lo_shu_grid",
        title="Lo Shu Grid",
        description=compact_description("asterwise_get_lo_shu_grid", "Derives a Lo Shu three-by-three frequency grid from birth-date digits and annotates planes, missing or repeated digits, and per-digit traits.\n\nSECTION: WHAT THIS TOOL COVERS\nChinese Lo Shu analysis: counts how often each digit one through nine appears in the date string, lays counts into the classical magic-square positions, and adds plane_analysis plus number_analysis entries keyed by digit strings '1'..'9'. Zero digits are ignored for placement. It does not compute Pythagorean Life Path (asterwise_get_numerology_profile) or Chaldean compounds.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\ndate string only; validated upstream.\n\nSECTION: OUTPUT CONTRACT\ndata.birth_date (string)\ndata.grid — three-by-three nested int array (row-major):\n  row positions map to numbers [4,9,2], [3,5,7], [8,1,6] respectively; cell value = count of that digit in the date (0 if absent)\ndata.present_numbers[] (int array)\ndata.missing_numbers[] (int array)\ndata.repeated_numbers[] (int array — digits appearing at least twice)\ndata.plane_analysis — the eight lines of the Lo Shu square 4 9 2 / 3 5 7 / 8 1 6:\n  mental_plane (top row 4-9-2) — { numbers[] (int array), description (string), complete (bool) }\n  emotional_plane (middle row 3-5-7) — same shape\n  practical_plane (bottom row 8-1-6) — same shape\n  thought_plane (left column 4-3-8) — same shape\n  will_plane (centre column 9-5-1) — same shape\n  action_plane (right column 2-7-6) — same shape\n  diagonal_4_5_6 — same shape\n  diagonal_2_5_8 — same shape\n  golden_yod (3-5-7), silver_yod (1-5-9) — deprecated duplicates of emotional_plane and will_plane, kept for compatibility\ndata.number_analysis{} — keys '1' through '9' (string keys):\n  count (int)\n  plane (string — legacy grouping: 1-3 mental, 4-6 physical, 7-9 spiritual)\n  lo_shu_plane (string — row of the square: mental 4-9-2, emotional 3-5-7, practical 8-1-6)\n  trait (string)\n  status (string — 'missing', 'present', or 'strong')\n  note (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Zeros in ISO dates are skipped — only digits one through nine populate the grid.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — letter-based Western numbers, not digit-frequency Lo Shu.\nasterwise_get_name_correction — spelling harmonics, not birth-date grids."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_lo_shu_grid(
        ctx: Context,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Lo Shu grid."""
        async with tool_guard("asterwise_get_lo_shu_grid"):
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
    @mcp.tool(
        name="asterwise_get_name_correction",
        title="Name Correction",
        description=compact_description("asterwise_get_name_correction", "Scores the current spelling of a personal name against the birth-date Life Path, suggests alternate spellings with harmony metrics, and names the best alternative when one scores higher.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns data.current_name metrics (expression, soul urge, personality, master and karmic flags, compatibility band, harmony_score 1..5) plus data.alternatives[] with identical shape per suggestion. Expression, Soul Urge and Personality are worked part by part, the same as asterwise_get_expression_number. data.recommendation names the best alternative spelling that scores higher than the current name, or is null. Empty alternatives[] means no better spelling was found — still success. Not for business entities (asterwise_get_business_name_analysis) or mobile/vehicle checks.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — baseline numbers before renaming advice.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nname and date strings only; upstream validates.\n\nSECTION: OUTPUT CONTRACT\ndata.full_name (string)\ndata.birth_date (string)\ndata.life_path (int)\ndata.current_name:\n  name (string)\n  expression (int)\n  soul_urge (int)\n  personality (int)\n  is_master (bool — Expression is 11/22/33)\n  karmic_debt (int or null — the Expression number's karmic debt)\n  expression_karmic_debt (int or null — same as karmic_debt)\n  soul_urge_karmic_debt (int or null)\n  personality_karmic_debt (int or null)\n  compatibility (string — 'harmonious', 'neutral', or 'challenging')\n  harmony_score (int — 1 through 5)\ndata.alternatives[] — objects matching data.current_name shape\ndata.recommendation (string or null — the highest-scoring alternative that beats the current name's harmony_score; null when none does)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error with details[].issue = no_letters when the name has no letters A-Z (e.g. '123', '!!!', or a name written only in a non-Latin script) — ask the user for the name spelled in Latin letters; this is not a server fault.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Empty alternatives[] is valid when no improvement exists.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_business_name_analysis — entity Expression scan, not personal spelling alternatives.\nasterwise_get_chaldean_numerology — Chaldean compounds, not harmony-scored spelling list."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_name_correction(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Name correction."""
        async with tool_guard("asterwise_get_name_correction"):
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
    @mcp.tool(
        name="asterwise_get_lucky_numbers",
        title="Lucky Numbers",
        description=compact_description("asterwise_get_lucky_numbers", "Fetches condensed lucky-number guidance for a name and birth date including primary and secondary picks, power number, interpretation, and a date_specific flag.\n\nSECTION: WHAT THIS TOOL COVERS\nThin numerology endpoint mirroring lucky_numbers[] from the full profile but omitting pinnacles, challenges, and long interpretations. data.date_specific is always false (profile-derived). Use when payload size matters. It is not the full profile (asterwise_get_numerology_profile) nor Lo Shu counts (asterwise_get_lo_shu_grid).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_numerology_profile — if deeper context is required.\n\nSECTION: INPUT CONTRACT\nname and date forwarded upstream without local checks.\n\nSECTION: OUTPUT CONTRACT\ndata.lucky_numbers[] (int array — primary and secondary values)\ndata.power_number (int — Life Path anchor)\ndata.date_specific (bool — always false; derived from profile)\ndata.interpretation (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error with details[].issue = no_letters when the name has no letters A-Z (e.g. '123', '!!!', or a name written only in a non-Latin script) — ask the user for the name spelled in Latin letters; this is not a server fault.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Duplicates asterwise_get_numerology_profile lucky list — choose this tool for smaller JSON only.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — full multi-section profile, not lucky-number-only payload.\nasterwise_get_number_meaning — dictionary entry for one integer, not personalised lucky sets."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_lucky_numbers(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Lucky numbers."""
        async with tool_guard("asterwise_get_lucky_numbers"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/lucky-numbers",
                api_key,
                {"name": name, "date": date},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lucky numbers", d),
            )
    @mcp.tool(
        name="asterwise_get_personal_year",
        title="Personal Year",
        description=compact_description("asterwise_get_personal_year", "Looks up the Personal Year theme for the current calendar year from a birth date (its month and day).\n\nSECTION: WHAT THIS TOOL COVERS\nEndpoint returns Personal Year data derived from birth month/day against the running calendar year on the server — there is no extra year argument in the tool schema. Response keys: year (int), personal_year_number (int), theme (string), interpretation (string), opportunities[] (string array), challenges[] (string array), advice (string). asterwise_get_numerology_profile leaves personal_year null; use this tool when Personal Year detail is required.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — see other core numbers first.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nOnly the birth date is sent; name is optional and not used. The active calendar year is chosen upstream automatically.\n\nSECTION: OUTPUT CONTRACT\nyear (int — the calendar year interpreted)\npersonal_year_number (int)\ntheme (string)\ninterpretation (string)\nopportunities[] (string array)\nchallenges[] (string array)\nadvice (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Cannot request arbitrary calendar years via this tool — only the server-selected current year.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — personal_year field there is null; this endpoint supplies the annual theme.\nasterwise_get_varshaphal — Vedic solar return, not Pythagorean Personal Year."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_personal_year(
        ctx: Context,
        date: str,
        name: str | None = None,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Personal year."""
        async with tool_guard("asterwise_get_personal_year"):
            api_key = await require_api_key(ctx)
            # Send the year explicitly: a body without it is cached upstream
            # as "this year" and could outlive New Year.
            data = await get_client().post(
                "/v1/numerology/personal-year",
                api_key,
                {"date": date, "year": datetime.now(UTC).year},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Personal year", d),
            )
    @mcp.tool(
        name="asterwise_get_number_meaning",
        title="Number Meaning",
        description=compact_description("asterwise_get_number_meaning", "Returns dictionary-style numerology copy for a single integer, including interpretation, keywords, and stubbed extended fields.\n\nSECTION: WHAT THIS TOOL COVERS\nStatic reference for 1-9 and the master numbers 11, 22, 33. No name or date. data.theme, data.advice, data.opportunities[], and data.challenges[] are stubs (null or empty). Not personalised profiling (asterwise_get_numerology_profile).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nnumber must pass local guard: one of 1-9, 11, 22 or 33; any other value raises MCP INVALID_PARAMS before the HTTP call.\n\nSECTION: OUTPUT CONTRACT\ndata.number (int)\ndata.context (string — 'general')\ndata.interpretation (string)\ndata.keywords[] (string array)\ndata.theme (currently null — stub)\ndata.opportunities[] (currently empty — stub)\ndata.challenges[] (currently empty — stub)\ndata.advice (currently null — stub)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — number not in 1-9, 11, 22, 33 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — Unsupported number → 422 validation_error with the allowed values, surfaces as MCP INTERNAL_ERROR with the API message.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_numerology_profile — computes personal numbers from name and date, not a static dictionary row.\nasterwise_get_lucky_numbers — personalised lucky list, not reference meanings."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_number_meaning(
        ctx: Context,
        number: int,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Number dictionary entry."""
        async with tool_guard("asterwise_get_number_meaning"):
            if not (1 <= number <= 9 or number in (11, 22, 33)):
                invalid_params(
                    "number must be 1-9 or a master number 11, 22 or 33."
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
    @mcp.tool(
        name="asterwise_check_mobile_number",
        title="Mobile Number Check",
        description=compact_description("asterwise_check_mobile_number", "Sums the digits of the national number (country code left out), reduces them to a single number, and returns harmonic scoring plus interpretive copy.\n\nSECTION: WHAT THIS TOOL COVERS\nAccepts formats like bare ten digits, plus-country-code with spaces or hyphens; non-digits are ignored. Valid numbers written with '+' or '00' are parsed and the country code and trunk prefix are dropped. Without a prefix, pass country so the number is read as dialled in that country; with no country, only India's 12-digit 91… form is shortened and every other number is summed exactly as written. The result depends only on the digits; owner name and birth date are optional and not used. Not for vehicle plates (asterwise_check_vehicle_number) or business names.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — anchor Life Path before judging the line.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nOnly digits count; the country calling code is never counted. Numbers written with '+' or '00' use the national number. Without a prefix, pass country (ISO 3166 alpha-2, e.g. IN, US, CN) so the number is read as dialled in that country; with no country, only India's 12-digit 91… form is shortened and every other number is summed exactly as written (e.g. 14155552671 without country sums all 11 digits = 42; with country=US it is 41). With country, the number is read as dialled there first, international dialling prefix included (e.g. AU 0011, US 011). A '+'/'00' number drops its country code only when it is a valid number: an invalid '+' number sums every digit after '+', an invalid '00' number is summed as written.\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — submitted number)\ndata.input_type (string — 'mobile')\ndata.total (int — sum of data.digits_used)\ndata.single_digit (int — Pythagorean root, one through nine)\ndata.is_master (bool — true when the total or a step of its reduction is 11, 22 or 33)\ndata.master_number (int — that master number; omitted when none)\ndata.digits_used (string — the digits summed: the national number without the country code)\ndata.country_code (int — calling code left out of the sum; omitted when none was left out)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — country not two letters → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error when the number has no digits or only zeros (details[].issue no_digits | digits_sum_to_zero), or country is unknown (issue unknown_country); surfaces as MCP INTERNAL_ERROR with the API message.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Punctuation is ignored; a leading '+' or '00' marks an international number whose country code is dropped.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_check_vehicle_number — plate digit rules, not SIM numbering.\nasterwise_get_business_name_analysis — letter Expression scan, not phone roots."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_check_mobile_number(
        ctx: Context,
        mobile_number: str,
        name: str | None = None,
        date: str | None = None,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        country: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{2}$"),
    ) -> str:
        """Mobile number check."""
        # name and date are accepted so older calls keep working; the API
        # analyses only the digits.
        del name, date
        async with tool_guard("asterwise_check_mobile_number"):
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = {"number": mobile_number}
            if country is not None:
                body["country"] = country
            data = await get_client().post(
                "/v1/numerology/mobile-number",
                api_key,
                body,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Mobile number analysis", d),
            )
    @mcp.tool(
        name="asterwise_check_vehicle_number",
        title="Vehicle Number Check",
        description=compact_description("asterwise_check_vehicle_number", "Strips non-digits from a vehicle registration token, reduces the numeric run to a single number, and returns the same harmony schema as mobile analysis.\n\nSECTION: WHAT THIS TOOL COVERS\nHandles Indian pattern plates (e.g. MH01AB1234) and international variants; only digits feed totals. Produces vehicle-specific input_type. Does not analyse phone numbers (asterwise_check_mobile_number) or business names.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — owner baseline.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nLetters and separators are ignored; reduction uses numeric digits only. Owner name and birth date are optional and not used.\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — submitted plate)\ndata.input_type (string — 'vehicle')\ndata.total (int — sum of data.digits_used)\ndata.single_digit (int — root)\ndata.is_master (bool — true when the total or a step of its reduction is 11, 22 or 33, e.g. DL01AB1234 totals 11)\ndata.master_number (int — that master number; omitted when none)\ndata.digits_used (string — every digit on the plate)\ndata.theme (string)\ndata.favourable_for[] (string array)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error when the plate has no digits or only zeros (details[].issue no_digits | digits_sum_to_zero) — ask the user for the plate's digits.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Alphabetic segments are decorative for numerology here — only digits matter.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_check_mobile_number — phone digit rules (national number, country code left out).\nasterwise_get_business_name_analysis — evaluates business Expression, not registration digits."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_check_vehicle_number(
        ctx: Context,
        vehicle_number: str,
        name: str | None = None,
        date: str | None = None,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Vehicle number check."""
        # name and date are accepted so older calls keep working; the API
        # analyses only the digits.
        del name, date
        async with tool_guard("asterwise_check_vehicle_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/vehicle-number",
                api_key,
                {"number": vehicle_number},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Vehicle number analysis", d),
            )
    @mcp.tool(
        name="asterwise_get_business_name_analysis",
        title="Business Name Analysis",
        description=compact_description("asterwise_get_business_name_analysis", "Reduces a business name to Expression and root digits and returns thematic suitability lists plus a harmony score. Uses the name only; no founder birth date is involved.\n\nSECTION: WHAT THIS TOOL COVERS\nAllows numerals and punctuation in the brand string — non-letters drop before letter-value reduction. Returns business-facing favourable domains, caution copy, and scoring. Not personal spelling optimisation (asterwise_get_name_correction) nor vehicle or phone checks.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_name_correction — if the entity is a person, not a brand.\n\nSECTION: INPUT CONTRACT\nbusiness_name (required): special characters and digits are acceptable; reduction strips non-letters per upstream rules. date: not used; omit it (accepted only so older calls keep working).\n\nSECTION: OUTPUT CONTRACT\ndata.input (string — business name as submitted)\ndata.input_type (string — 'business_name')\ndata.expression_number (int — the Expression number, worked part by part like asterwise_get_expression_number: each word reduced, 11/22/33 kept; same value as single_digit)\ndata.single_digit (int — same as expression_number: 1-9 or master 11, 22, 33)\ndata.is_master (bool)\ndata.theme (string)\ndata.favourable_for[] (string array — suitable domains)\ndata.caution (string)\ndata.harmony_score (int — one through ten)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — 422 validation_error with details[].issue = no_letters when the name has no letters A-Z (e.g. '123', '!!!', or a name written only in a non-Latin script) — ask the user for the name spelled in Latin letters; this is not a server fault.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Brand strings with emojis or digits still flow through upstream stripping rules.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_name_correction — personal spelling alternatives, not corporate Expression scoring.\nasterwise_check_mobile_number — numeric line analysis, not brand letters."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_business_name_analysis(
        ctx: Context,
        business_name: str,
        date: str | None = None,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Business name."""
        # `date` is accepted so older calls keep working; the analysis uses
        # only the name (the API has no date input). POST keeps the name out
        # of the URL.
        del date
        async with tool_guard("asterwise_get_business_name_analysis"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/business-name",
                api_key,
                {"name": business_name},
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Business name analysis", d),
            )
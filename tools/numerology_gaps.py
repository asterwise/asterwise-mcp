"""New numerology gap tools — expression, soul urge, personality, maturity,
balance, karmic lessons, personal cycles."""

from __future__ import annotations

from fastmcp import Context, FastMCP
import mcp.types as mcp_types

from client import get_client
from models import ResponseFormat
from runtime import (
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_expression_number",
        title="Expression Number",
        description=(
            "Calculates the Expression (Destiny) number from the full name using Pythagorean "
            "letter values. Reduces each name part separately before summing — this is the "
            "Goodwin/Balliett per-part method which preserves the vibrational weight of "
            "compound numbers within each name segment. Master numbers 11, 22, 33 are "
            "preserved and not further reduced.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Expression number describes the natural talents, abilities, and shortcomings "
            "a person brought into this life — what they are capable of becoming. It differs "
            "from the Soul Urge (inner motivation) and Personality (outer mask). Uses all "
            "letters A–Z mapped to Pythagorean values 1–9. Not Chaldean "
            "(asterwise_get_chaldean_numerology).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — this tool is standalone.\n"
            "AFTER: asterwise_get_soul_urge_number — complete the core trinity (Expression, Soul Urge, Personality).\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth. Include all name parts separated by spaces.\n"
            "  Example: 'Arjun Mehta', 'Sofia Rossi', 'James Carter'\n"
            "  Format: string, any case (uppercase/lowercase both accepted)\n"
            "  Constraint: at least one alphabetic character required\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number (int — Expression number; may be 11, 22, or 33 for master numbers)\n"
            "data.is_master_number (bool — true when number is 11, 22, or 33)\n"
            "data.karmic_debt_number (int or null — the karmic debt root if present; null otherwise)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON — use this "
            "for programmatic parsing, typed clients, and downstream tool chaining.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data — no fields are added, removed, "
            "or filtered by either mode.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local — caught before upstream call):\n"
            "  None — validation is upstream.\n"
            "INTERNAL_ERROR:\n"
            "  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_soul_urge_number — vowels only, not all letters.\n"
            "asterwise_get_personality_number — consonants only, not all letters.\n"
            "asterwise_get_numerology_profile — returns Expression plus all other core numbers, "
            "pinnacles, challenges, and lucky numbers in one call.\n"
            "asterwise_get_chaldean_numerology — different letter-value system (Chaldean 1–8)."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_expression_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Expression (Destiny) number from name."""
        async with tool_guard("asterwise_get_expression_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/expression", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Expression number", d),
            )
    @mcp.tool(
        name="asterwise_get_soul_urge_number",
        title="Soul Urge Number",
        description=(
            "Calculates the Soul Urge (Heart's Desire) number from vowels in the full name. "
            "Only A, E, I, O, U are treated as vowels — Y is always a consonant in this system. "
            "Reduces each name part separately before summing, preserving master numbers 11, 22, 33.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Soul Urge reveals the inner motivation — what the soul craves, what drives choices "
            "at the deepest level. It is the hidden engine beneath the Expression. This is the most "
            "private of the three core name numbers.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_personality_number — complete the name number trinity.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth.\n"
            "  Example: 'Arjun Mehta', 'Sofia Rossi'\n"
            "  Y is always treated as a consonant — not a vowel.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number (int — Soul Urge number; 11/22/33 preserved as master)\n"
            "data.is_master_number (bool)\n"
            "data.karmic_debt_number (int or null)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete response as indented JSON — use this "
            "for programmatic parsing, typed clients, and downstream tool chaining.\n"
            "response_format=markdown renders the same data as a human-readable report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — validation is upstream.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_expression_number — all letters, not vowels only.\n"
            "asterwise_get_personality_number — consonants only, not vowels."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_soul_urge_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Soul Urge number from vowels."""
        async with tool_guard("asterwise_get_soul_urge_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/soul-urge", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Soul Urge number", d),
            )
    @mcp.tool(
        name="asterwise_get_personality_number",
        title="Personality Number",
        description=(
            "Calculates the Personality number from consonants in the full name. "
            "All non-vowels (BCDFGHJKLMNPQRSTVWXYZ) contribute — Y is always a consonant. "
            "Reduces each name part separately, preserving master numbers 11, 22, 33.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Personality number is the outer mask — how others perceive you before they "
            "know you well. It governs first impressions, physical presentation, and the "
            "social interface between the private self (Soul Urge) and the world.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_numerology_profile — see all five core numbers together.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth.\n"
            "  Example: 'Arjun Mehta', 'Sofia Rossi'\n"
            "  Y is always a consonant — not treated as a vowel.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number (int — Personality number; master numbers 11/22/33 preserved)\n"
            "data.is_master_number (bool)\n"
            "data.karmic_debt_number (int or null)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured JSON. response_format=markdown — human-readable.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None. INTERNAL_ERROR: upstream failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_expression_number — all letters (Expression = Soul Urge + Personality).\n"
            "asterwise_get_soul_urge_number — vowels only."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_personality_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Personality number from consonants."""
        async with tool_guard("asterwise_get_personality_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/personality", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Personality number", d),
            )
    @mcp.tool(
        name="asterwise_get_maturity_number",
        title="Maturity Number",
        description=(
            "Calculates the Maturity number as the sum of Life Path and Expression numbers, "
            "reduced to a single digit or master number. Represents the underlying wish or "
            "true desire that becomes conscious around age 35 and fully emerges by midlife.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Maturity number is sometimes called the True Goal — the final attainment "
            "that Life Path and Expression together point toward. It becomes increasingly "
            "dominant after age 35 and is the most important number for understanding "
            "the second half of life.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: RECOMMENDED — asterwise_get_numerology_profile — confirm Life Path and Expression "
            "before interpreting their sum.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth. Example: 'Arjun Mehta'\n"
            "date — Birth date in YYYY-MM-DD format. Example: '1985-11-12'\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.maturity_number (int — LP + Expression, reduced; master numbers preserved)\n"
            "data.life_path_number (int — component)\n"
            "data.expression_number (int — component)\n"
            "data.is_master_number (bool — true if maturity is 11, 22, or 33)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured JSON. response_format=markdown — human-readable.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None. INTERNAL_ERROR: upstream failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_numerology_profile — returns maturity_number as part of the full profile.\n"
            "asterwise_get_personal_cycles — temporal cycles that change annually, not a fixed number."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_maturity_number(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat,
    ) -> str:
        """Maturity number (Life Path + Expression)."""
        async with tool_guard("asterwise_get_maturity_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/maturity", api_key, {"name": name, "date": date}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Maturity number", d),
            )
    @mcp.tool(
        name="asterwise_get_balance_number",
        title="Balance Number",
        description=(
            "Calculates the Balance number from the first letter of each name part, using "
            "Pythagorean values. A three-part name yields three initials summed and reduced. "
            "The Balance number describes how a person handles emotional crises and unresolved "
            "inner conflict.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Balance number is consulted specifically in times of stress. It does not describe "
            "everyday personality but rather the instinctive crisis-management style. A person "
            "with Balance 1 instinctively becomes self-reliant under pressure; Balance 2 seeks "
            "partnership; Balance 8 attempts to assert control.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth. The first letter of each space-separated "
            "part contributes one value.\n"
            "  Example: 'Arjun Mehta' → A(1) + M(4) = 5\n"
            "  Example: 'James Earl Carter' → J(1) + E(5) + C(3) = 9\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number (int — Balance number 1–9, or master 11/22)\n"
            "data.is_master_number (bool)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured JSON. response_format=markdown — human-readable.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None. INTERNAL_ERROR: upstream failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_expression_number — uses all letters, not just initials.\n"
            "asterwise_get_karmic_lessons — identifies absent digits across all letters."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_balance_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Balance number from initials."""
        async with tool_guard("asterwise_get_balance_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/balance", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Balance number", d),
            )
    @mcp.tool(
        name="asterwise_get_karmic_lessons",
        title="Karmic Lessons",
        description=(
            "Identifies karmic lessons by scanning all letter values in the full name and "
            "finding which digits 1–9 are absent. Each missing digit represents an area "
            "where experience is thin and development is needed in this lifetime.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Every letter in the name maps to a digit 1–9. Digits that never appear indicate "
            "karmic lessons — life areas the soul has not yet fully explored. A person missing "
            "the digit 4 (associated with system-building, discipline, endurance) will find "
            "practical organisation a recurring challenge. Missing multiple digits intensifies "
            "the developmental pressure in those areas.\n"
            "Digit zero is not used — only 1 through 9.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_numerology_profile — see karmic lessons alongside all core numbers.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "name — Full legal name as used at birth.\n"
            "  Example: 'Arjun Mehta' — scan all 9 letters for their Pythagorean digit values.\n"
            "  Letters present: A=1, R=9, J=1, U=3, N=5, M=4, E=5, H=8, T=2, A=1\n"
            "  Digits present: {1,2,3,4,5,8,9} → Missing: {6,7}\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.karmic_lessons (int array — missing digits 1–9, sorted ascending; empty if none missing)\n"
            "data.has_karmic_lessons (bool — false when all nine digits are present)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured JSON. response_format=markdown — human-readable.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None. INTERNAL_ERROR: upstream failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_balance_number — uses only first letters (initials), not all letters.\n"
            "asterwise_get_expression_number — reduces all letters to a single number; does not "
            "scan for absent digits."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_karmic_lessons(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Karmic lessons from name."""
        async with tool_guard("asterwise_get_karmic_lessons"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/karmic-lessons", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Karmic lessons", d),
            )
    @mcp.tool(
        name="asterwise_get_personal_cycles",
        title="Personal Cycles",
        description=(
            "Returns the Personal Year, Personal Month, and Personal Day numbers for a given "
            "birth date and optional target date. All three cycle numbers are derived from the "
            "birth month, birth day, and the target calendar date.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Personal cycles are the Pythagorean timing system. The Personal Year (1–9) sets "
            "the annual theme. The Personal Month refines it to a 30-day window. The Personal "
            "Day gives the daily energy flavour. A Personal Year 1 favours new beginnings; a 9 "
            "favours completion and release. Cycles nest: the same number in Year, Month, and "
            "Day simultaneously creates a peak intensity day.\n\n"
            "Formula:\n"
            "  Personal Year = birth_month_reduced + birth_day_reduced + target_year_reduced\n"
            "  Personal Month = Personal Year + target_month, reduced\n"
            "  Personal Day = Personal Month + target_day, reduced\n"
            "Master numbers 11 and 22 are preserved where they arise.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_numerology_profile — see personal cycles alongside core numbers.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date — Birth date in YYYY-MM-DD format. Example: '1985-11-12'\n"
            "year (optional int) — Target year. Defaults to current calendar year.\n"
            "  Example: 2026\n"
            "month (optional int 1–12) — Target month. Defaults to current month.\n"
            "  Example: 5\n"
            "day (optional int 1–31) — Target day. Personal Day is only returned when day "
            "is provided. Defaults to null (Personal Day omitted).\n"
            "  Example: 1\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.personal_year (int — 1–9 or master 11/22)\n"
            "data.personal_month (int — 1–9 or master 11/22)\n"
            "data.personal_day (int or null — null when day parameter is not provided)\n"
            "data.target_year (int — echoed)\n"
            "data.target_month (int — echoed)\n"
            "data.target_day (int or null — echoed)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured JSON. response_format=markdown — human-readable.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — all validation is upstream.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_personal_year — returns Personal Year only, no month or day breakdown.\n"
            "asterwise_get_numerology_profile — core name numbers; personal_year field is null there."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_personal_cycles(
        ctx: Context,
        date: str,
        response_format: ResponseFormat,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> str:
        """Personal Year, Month, and Day cycles."""
        async with tool_guard("asterwise_get_personal_cycles"):
            api_key = await require_api_key(ctx)
            body: dict = {"date": date}
            if year is not None:
                body["year"] = year
            if month is not None:
                body["month"] = month
            if day is not None:
                body["day"] = day
            data = await get_client().post(
                "/v1/numerology/personal-cycles", api_key, body
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Personal cycles", d),
            )
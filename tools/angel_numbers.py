"""Angel numbers MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
import mcp.types as mcp_types

from client import get_client, safe_segment
from models import ResponseFormat
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_angel_number_today",
        title="Angel Number Today",
        description=compact_description("asterwise_get_angel_number_today", "Returns today's angel number computed from the current date. All digits of the date are summed and reduced to a single digit (1-9), then the triple sequence of that digit is returned (e.g. digit 9 → angel number 999).\n\nSECTION: WHAT THIS TOOL COVERS\nAngel numbers are repeated digit sequences interpreted as synchronistic messages in modern spiritual practice. The daily angel number is the same for all callers on the same date — it is a collective daily energy, not personal. Returns the angel number sequence, its theme, primary message, actionable guidance, and associated life areas. Life Path 3 → 333 (creative expression). Today's digit is derived from the date's digit sum.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_angel_number_personal — for a personalised angel number from birth date.\n\nSECTION: INPUT CONTRACT\nNo required parameters — today's date is used automatically.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string — YYYY-MM-DD)\ndata.daily_digit (int — reduced digit 1-9)\ndata.angel_number (string — e.g. '999')\ndata.number (string — same as angel_number)\ndata.theme (string)\ndata.message (string)\ndata.guidance (string)\ndata.areas[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON. response_format=markdown renders a human-readable report. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP — pure math, no ephemeris.\n\nSECTION: ERROR CONTRACT\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_angel_number — lookup for a specific number sequence by value.\nasterwise_get_angel_number_personal — personalised number from birth date Life Path."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_angel_number_today(
        ctx: Context,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Get today's angel number."""
        async with tool_guard("asterwise_get_angel_number_today"):
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/numerology/angel/today", api_key, timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Angel Number Today", d),
            )
    @mcp.tool(
        name="asterwise_get_angel_number",
        title="Angel Number",
        description=compact_description("asterwise_get_angel_number", "Lookup the meaning of a specific angel number by its sequence. Supported: 000, 111–999 (single repeating digit), 911, 1010, 1111, 1122, 1212, 1234, 2222–9999 (double repeating digit).\n\nSECTION: WHAT THIS TOOL COVERS\nReturns the theme, primary message, actionable guidance, and associated life areas for a specific angel number sequence. Each sequence carries distinct meaning in modern numerological tradition. 111 = manifestation portal. 444 = angelic protection. 999 = cycle completion. 1111 = awakening gateway. 555 = transformation in progress. Pass the number as a string exactly as it appears (e.g. '444' not 444).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nnumber: string — the angel number sequence to look up. Examples: '111', '444', '1111', '911'.\n\nSECTION: OUTPUT CONTRACT\ndata.number (string)\ndata.theme (string)\ndata.message (string)\ndata.guidance (string)\ndata.areas[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — structured JSON. response_format=markdown — human-readable. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Unsupported number → 404, surfaces as MCP INTERNAL_ERROR.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_angel_number_today — today's collective daily angel number.\nasterwise_get_angel_number_personal — personal angel number from birth date.\nasterwise_get_number_meaning — Pythagorean numerology meaning for 1–33; different tradition."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_angel_number(
        ctx: Context,
        number: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Look up a specific angel number."""
        async with tool_guard("asterwise_get_angel_number"):
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                f"/v1/numerology/angel/{safe_segment(number)}",
                api_key,
                timeout=10.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Angel Number {number}", d),
            )
    @mcp.tool(
        name="asterwise_get_angel_number_personal",
        title="Personal Angel Number",
        description=compact_description("asterwise_get_angel_number_personal", "Computes a personal angel number from a birth date using the Pythagorean Life Path as the base. Life Path 1-9 maps to the triple sequence (LP 4 → 444). Master numbers 11, 22, 33 map to 1111, 2222, 3333 respectively.\n\nSECTION: WHAT THIS TOOL COVERS\nThe personal angel number is the individual's primary energetic signature in angel number tradition. Derived using the digit-fusing Life Path method (same as asterwise_get_numerology_profile): all digits of the birth date are summed and reduced to a single digit or master number, then mapped to the corresponding triple or quadruple sequence. Returns the Life Path number, the angel sequence, and the full angel number interpretation.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_numerology_profile — confirm Life Path before calling.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\ndate: Birth date in YYYY-MM-DD format. Example: '1994-03-31'\nname (optional): Person's name for personalisation.\n\nSECTION: OUTPUT CONTRACT\ndata.birth_date (string)\ndata.life_path (int — 1-9 or master 11/22/33)\ndata.angel_number (string — e.g. '333' for LP 3)\ndata.number (string)\ndata.theme (string)\ndata.message (string)\ndata.guidance (string)\ndata.areas[] (string array)\ndata.name (string or null — if provided)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — structured JSON. response_format=markdown — human-readable. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP — pure digit math, no ephemeris.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Invalid date format → 422.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_angel_number_today — collective daily number from today's date, not birth date.\nasterwise_get_numerology_profile — full Pythagorean profile; this tool extracts only the Life Path → angel sequence mapping."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_angel_number_personal(
        ctx: Context,
        date: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        name: str | None = None,
    ) -> str:
        """Compute personal angel number from birth date."""
        async with tool_guard("asterwise_get_angel_number_personal"):
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = {"date": date}
            if name:
                body["name"] = name
            data = await get_client().post(
                "/v1/numerology/angel/personal", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Personal Angel Number", d),
            )
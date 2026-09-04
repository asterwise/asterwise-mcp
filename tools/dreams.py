"""Dream symbol database MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
import mcp.types as mcp_types

from client import get_client, safe_segment
from models import ResponseFormat
from runtime import (
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_dream_symbols",
        title="Dream Symbols",
        description="Returns dream symbols from the database with dual-tradition interpretation: Jungian/Western psychological analysis and traditional Vedic dream-symbol meaning. 500 symbols across 8 categories. Optionally filter by category.\n\nSECTION: WHAT THIS TOOL COVERS\nEach symbol includes: Jungian meaning and archetype (Shadow, Self, Anima, Animus, Great Mother, Wise Old Man, Hero, Trickster, Persona), Vedic dream meaning with Shubha/Ashubha (auspicious/inauspicious) classification, vedic_source tradition label per entry, traditions_agree field flagging where East and West conflict, emotional tone, 2-3 context variants, and related symbol slugs. The traditions_agree='conflict' entries are significant — e.g. Owl (West=wisdom; Vedic=inauspicious death omen), Wedding (West=union; Vedic=inauspicious, medical-astrological tradition warns illness), Gold (West=the Self; Vedic=financial loss warning in medical-astrological tradition). Valid categories: animals, nature, people, places, objects, actions, body, abstract.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_dream_symbol — get full detail for a specific symbol.\n\nSECTION: INPUT CONTRACT\ncategory (optional): One of animals, nature, people, places, objects, actions, body, abstract. Omit for all 500 symbols.\n\nSECTION: OUTPUT CONTRACT\ndata.total (int)\ndata.category_filter (string or null)\ndata.symbols[] — each:\n  slug (string)\n  name (string)\n  category (string)\n  jungian_meaning (string)\n  jungian_archetype (string)\n  vedic_meaning (string)\n  vedic_auspicious (bool or null — null = mixed/context-dependent)\n  vedic_source (string)\n  traditions_agree (string — 'agree'|'conflict'|'partial')\n  emotional_tone (string)\n  themes[] (string array — for AI synthesis)\n  context_variants[] — { context (string), meaning (string) }\n  related_symbols[] (string array of slugs)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — symbol array. response_format=markdown — formatted catalogue. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP — static database.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Invalid category → 422.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dream_symbol — single symbol detail by name.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_dream_symbols(
        ctx: Context,
        response_format: ResponseFormat,
        category: str | None = None,
    ) -> str:
        """Get dream symbol database."""
        async with tool_guard("asterwise_get_dream_symbols"):
            api_key = await require_api_key(ctx)
            params: dict[str, Any] | None = None
            if category:
                params = {"category": category}
            data = await get_client().get(
                "/v1/dreams/symbols", api_key, params, timeout=30.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dream Symbols", d),
            )
    @mcp.tool(
        name="asterwise_get_dream_symbol",
        title="Dream Symbol",
        description="Lookup a specific dream symbol by slug or name (case-insensitive). Returns full dual-tradition interpretation including Jungian archetype, Vedic dream meaning with auspiciousness, context variants, and related symbols.\n\nSECTION: WHAT THIS TOOL COVERS\nSingle symbol lookup with complete detail. Use for dream journaling apps, AI-powered dream interpretation (the themes[] field is designed for synthesis), and cross-tradition comparison. Notable tradition conflicts: Snake (Western=transformation; Vedic=partial — white snake=auspicious, black chasing=inauspicious). Elephant=auspicious both traditions (Ganesha). Crow=inauspicious both traditions (Yama's messenger). Wedding=conflict (West=union; Vedic=inauspicious).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nname: Symbol slug or display name. Examples: 'snake', 'eagle', 'childhood-home', 'lotus', 'black-dog'\n\nSECTION: OUTPUT CONTRACT\nSame shape as each symbol in asterwise_get_dream_symbols — full single symbol object.\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — single symbol object. response_format=markdown — formatted interpretation card. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Unknown symbol → 404, surfaces as MCP INTERNAL_ERROR.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dream_symbols — full database listing with optional category filter.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_dream_symbol(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Lookup a specific dream symbol."""
        async with tool_guard("asterwise_get_dream_symbol"):
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                f"/v1/dreams/symbol/{safe_segment(name)}",
                api_key,
                timeout=15.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Dream Symbol: {name}", d),
            )
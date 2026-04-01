"""Vimshottari and alternative Dasha systems (timing)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat
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


def _dasha_tree_md(data: dict[str, Any]) -> str:
    periods = data.get("periods") or data.get("dasha") or data.get("vimshottari")
    lines = ["## Vimshottari Dasha", ""]
    if isinstance(periods, list):
        for block in periods[:200]:
            if isinstance(block, dict):
                label = block.get("planet") or block.get("lord") or block.get("name", "—")
                start = block.get("start") or block.get("start_date") or ""
                end = block.get("end") or block.get("end_date") or ""
                bal = block.get("balance") or block.get("balance_at_birth") or ""
                lines.append(
                    f"- **{label}** — {start} → {end}"
                    + (f" (balance: {bal})" if bal else "")
                )
                children = block.get("antar") or block.get("children") or block.get("sub_periods")
                if isinstance(children, list):
                    for ch in children[:50]:
                        if isinstance(ch, dict):
                            lines.append(
                                f"  - {ch.get('planet', ch.get('lord', '—'))}: "
                                f"{ch.get('start', '')} → {ch.get('end', '')}"
                            )
        lines.append("")
    lines.append("### Raw structure\n\n")
    lines.append(structured_markdown("Dasha details", data))
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_dasha",
        description=(
            "Calculate Vimshottari Dasha periods — the primary timing system of Parashari "
            "Jyotish, based on the Moon's nakshatra at birth and a 120-year planetary "
            "cycle. Returns a hierarchical tree of Mahadasha (major period), Antardasha "
            "(sub-period), Pratyantar, Sookshma, and Prana levels. Source: BPHS Dasha "
            "chapters. "
            "Use this as the core timing tool for predicting when events unfold. "
            "levels=1 returns Mahadasha only (fast, lightweight); levels=2 adds "
            "Antardasha (recommended for most readings); levels=3 gives Pratyantar "
            "(detailed timing); levels=4–5 are highly granular and return large responses. "
            "Do not confuse with asterwise_get_char_dasha (Jaimini sign-based system), "
            "asterwise_get_yogini_dasha (36-year Yogini cycle), or "
            "asterwise_get_ashtottari_dasha (108-year alternative). "
            "Use Vimshottari (this tool) for all standard Parashari timing analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        levels: int = 3
    ) -> str:
        """Vimshottari Dasha up to five levels."""
        try:
            if levels < 1 or levels > 5:
                invalid_params("levels must be between 1 and 5 inclusive.")
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "levels": levels}
            data = await get_client().post("/v1/astro/dasha", api_key, body, timeout=20.0)
            return format_tool_result(data, response_format, _dasha_tree_md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dasha", exc)

    @mcp.tool(
        name="asterwise_get_dasha_transits",
        description=(
            "Get the correlation between the current running Dasha periods and active "
            "planetary transits — showing which transiting planets are supporting or "
            "challenging the Dasha lord and sub-lord at this moment. Source: classical "
            "Gochar overlaid on Dasha. "
            "Use this when you need to assess the quality of the current period — "
            "whether the Dasha promise is being activated or blocked by transits right now. "
            "Do not confuse with asterwise_get_gochar (which shows all transits vs "
            "the natal chart without Dasha context) or asterwise_get_transits (which "
            "shows transits across a custom date range). "
            "Use this tool when the user asks: 'Is this a good time for me?' or "
            "'Why is my Mars Dasha not delivering results?' "
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_dasha_transits(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dasha-period transits."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/dasha-transits", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dasha transits", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dasha_transits", exc)

    @mcp.tool(
        name="asterwise_get_char_dasha",
        description=(
            "Calculate Char Dasha — the Jaimini sign-based timing system in which "
            "zodiac signs (not planets) take turns as the major period lord, each sign "
            "ruling for a number of years determined by its lord's position. Gives "
            "a different timing perspective from Vimshottari, particularly for "
            "relationship and dharma events. Source: Jaimini Sutras. "
            "Use when the user follows Jaimini astrology, or when Vimshottari Dasha "
            "does not clearly explain events and a cross-system check is needed. "
            "Do not use as a replacement for Vimshottari — use both together for "
            "corroboration of timing."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_char_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Char Dasha."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/char-dasha", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Char Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_char_dasha", exc)

    @mcp.tool(
        name="asterwise_get_yogini_dasha",
        description=(
            "Calculate Yogini Dasha — an alternative timing system based on an "
            "8-Yogini cycle totalling 36 years: Mangala (1yr), Pingala (2yr), "
            "Dhanya (3yr), Bhramari (4yr), Bhadrika (5yr), Ulka (6yr), Siddha (7yr), "
            "Sankata (8yr), then repeating. Particularly valued for timing events "
            "in the near term. Source: Yogini Dasha tradition, referenced in "
            "Muhurta Chintamani and other texts. "
            "Use when the user wants a second timing perspective alongside Vimshottari, "
            "or when their life events match Yogini cycles better than Vimshottari. "
            "This is a secondary system — always check Vimshottari first."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_yogini_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Yogini Dasha."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/yogini", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Yogini Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_yogini_dasha", exc)

    @mcp.tool(
        name="asterwise_get_ashtottari_dasha",
        description=(
            "Calculate Ashtottari Dasha — a 108-year alternative timing cycle using "
            "eight planets (excluding Ketu) with different period lengths than "
            "Vimshottari. Applicable when Rahu is in a Kendra or Trikona from Lagna "
            "or Moon (the classical condition), though some astrologers apply it broadly. "
            "Source: classical Ashtottari rules. "
            "Use as a secondary timing system for cross-checking Vimshottari results, "
            "or specifically when the chart meets the Rahu-in-Kendra/Trikona condition. "
            "Do not replace Vimshottari with this — use them together."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_ashtottari_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        levels: int = 3,
    ) -> str:
        """Ashtottari Dasha."""
        try:
            if levels < 1 or levels > 5:
                invalid_params("levels must be between 1 and 5 inclusive.")
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "levels": levels}
            data = await get_client().post(
                "/v1/astro/ashtottari", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Ashtottari Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ashtottari_dasha", exc)

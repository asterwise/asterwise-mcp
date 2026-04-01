"""Vimshottari and alternative Dasha systems (timing)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat, birth_dict
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
            "Calculate Vimshottari Dasha periods up to 5 levels deep (Maha, Antar, Pratyantar, Sookshma, "
            "Prana). Specify levels=1 for Mahadasha only through levels=5 for the full tree. Source: BPHS "
            "Dasha chapters.\n"
            "Inputs: BirthData, levels (1–5, default 3), response_format.\n"
            "Returns: Hierarchical dasha tree or full periods JSON."
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
            body = {**birth_dict(birth), "levels": levels}
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
            "Get planetary transits during the current Dasha period — how transits interact with the "
            "running Dasha for timing. Source: classical Gochar with Dasha overlay.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Transit–Dasha combinations."
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
                "/v1/astro/dasha-transits", api_key, birth_dict(birth),
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
            "Calculate Char Dasha (Jaimini) — sign-based periods. Source: Jaimini Sutras.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Char Dasha periods."
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
            data = await get_client().post("/v1/astro/char-dasha", api_key, birth_dict(birth),
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
            "Calculate Yogini Dasha — 36-year cycle with eight Yoginis. Source: Yogini Dasha tradition.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Yogini periods."
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
            data = await get_client().post("/v1/astro/yogini", api_key, birth_dict(birth),
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
            "Calculate Ashtottari Dasha — 108-year alternative cycle. Source: classical Ashtottari rules.\n"
            "Inputs: BirthData, levels (1–5, default 3), response_format.\n"
            "Returns: Ashtottari periods."
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
            body = {**birth_dict(birth), "levels": levels}
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

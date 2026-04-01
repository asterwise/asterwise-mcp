"""PDF report generation (stateful URLs — not idempotent)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat, birth_dict
from runtime import (
    REPORT_ANNOTATIONS,
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
        name="asterwise_generate_kundli_report",
        description=(
            "Generate a comprehensive Kundli PDF — natal chart, vargas, Dasha, yogas, doshas. Source: "
            "compiled BPHS-style report.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Download URL and metadata (each call may create a new file)."
        ),
        annotations=REPORT_ANNOTATIONS,
    )
    async def asterwise_generate_kundli_report(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Kundli PDF."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/report/kundli", api_key, birth_dict(birth), timeout=45.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Kundli report", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_generate_kundli_report", exc)

    @mcp.tool(
        name="asterwise_generate_matchmaking_report",
        description=(
            "PDF matchmaking report — Ashtakoota, vetoes, dosha sync. Source: BPHS Ch.18 style summary.\n"
            "Inputs: person1, person2 BirthData, response_format.\n"
            "Returns: Report URL and metadata."
        ),
        annotations=REPORT_ANNOTATIONS,
    )
    async def asterwise_generate_matchmaking_report(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Matchmaking PDF."""
        try:
            api_key = await require_api_key(ctx)
            body = {"person1": birth_dict(person1), "person2": birth_dict(person2)}
            data = await get_client().post(
                "/v1/report/matchmaking", api_key, body, timeout=45.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Matchmaking report", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_generate_matchmaking_report", exc)

    @mcp.tool(
        name="asterwise_generate_dasha_report",
        description=(
            "PDF Vimshottari timeline — five levels mapped visually. Source: BPHS Dasha presentation.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Report URL and metadata."
        ),
        annotations=REPORT_ANNOTATIONS,
    )
    async def asterwise_generate_dasha_report(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dasha PDF."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/report/dasha", api_key, birth_dict(birth), timeout=45.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dasha report", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_generate_dasha_report", exc)

    @mcp.tool(
        name="asterwise_generate_varshaphal_report",
        description=(
            "Varshaphal (solar return) PDF for a given year. Calls chart computation then report generation. "
            "Source: Varshaphal tradition.\n"
            "Inputs: BirthData, year, response_format.\n"
            "Returns: Report URL and metadata."
        ),
        annotations=REPORT_ANNOTATIONS,
    )
    async def asterwise_generate_varshaphal_report(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat
    ) -> str:
        """Varshaphal PDF (two-step)."""
        try:
            api_key = await require_api_key(ctx)
            chart_payload: dict[str, Any] = {**birth_dict(birth), "target_year": year}
            chart = await get_client().post(
                "/v1/astro/varshaphal", api_key, chart_payload, timeout=45.0
            )
            report_body = {**birth_dict(birth), "year": year, "varshaphal": chart}
            data = await get_client().post(
                "/v1/report/varshaphal", api_key, report_body, timeout=45.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Varshaphal report ({year})", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_generate_varshaphal_report", exc)

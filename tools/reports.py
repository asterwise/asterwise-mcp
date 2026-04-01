"""PDF report generation (stateful URLs — not idempotent)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat
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
            "Generate a comprehensive Kundli PDF report for a person — includes the "
            "natal chart, divisional charts (Navamsa and others), Vimshottari Dasha "
            "timeline, yoga analysis, dosha summary, and remedial suggestions, "
            "compiled into a formatted document. Source: compiled BPHS-style report. "
            "Returns a download URL for the generated PDF. Each call generates a new file. "
            "Use when the user wants a complete shareable birth chart document. "
            "Do not use this for on-screen analysis — call the individual tools "
            "(asterwise_get_natal_chart, asterwise_get_dasha, asterwise_get_yogas) "
            "for interactive readings. This tool is for generating a PDF to download "
            "or share."
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
                "/v1/report/kundli", api_key, birth.to_api_dict(), timeout=45.0
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
            "Generate a matchmaking compatibility PDF report for two people — includes "
            "Ashtakoota Guna Milan, Rajju and Vedha veto assessment, Mangal Dosha "
            "check, and Papa Samyam balance, formatted as a shareable document. "
            "Source: BPHS Ch.18 style summary. Returns a download URL. "
            "Use when the user needs a formal matchmaking report to share with families. "
            "For interactive compatibility analysis without a PDF, use "
            "asterwise_get_compatibility instead."
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
            body = {"person1": person1.to_api_dict(), "person2": person2.to_api_dict()}
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
            "Generate a Vimshottari Dasha PDF timeline report — five levels of Dasha "
            "periods mapped visually across the person's lifetime, showing which "
            "planetary periods are active and when transitions occur. "
            "Source: BPHS Dasha presentation. Returns a download URL. "
            "Use when the user wants a visual timeline document to print or share. "
            "For on-screen Dasha data, use asterwise_get_dasha instead."
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
                "/v1/report/dasha", api_key, birth.to_api_dict(), timeout=45.0
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
            "Generate a Varshaphal (Solar Return) PDF report for a specific year — "
            "includes the annual chart, year lord, Muntha position, and year-ahead "
            "analysis. This tool makes two sequential API calls: first computing the "
            "Varshaphal chart, then generating the report. "
            "Source: Varshaphal tradition. Returns a download URL. "
            "Use when the user wants a formal annual forecast document. "
            "For on-screen Varshaphal data, use asterwise_get_varshaphal instead."
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
            chart_payload: dict[str, Any] = {**birth.to_api_dict(), "target_year": year}
            chart = await get_client().post(
                "/v1/astro/varshaphal", api_key, chart_payload, timeout=45.0
            )
            report_body = {**birth.to_api_dict(), "year": year, "varshaphal": chart}
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

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
            "Generate a comprehensive Kundli PDF — includes natal chart, all 16 "
            "divisional charts (D1 through D60), full Vimshottari Dasha tree, "
            "complete yoga analysis (80+ yogas including all Pancha Mahapurusha, "
            "Neecha Bhanga, Raja Yogas, Nabhasha, Chandra and Surya Yogas), "
            "full dosha summary with severity and cancellation conditions for all "
            "14 classical doshas, Avakahada table, Ashtakavarga, and remedial "
            "suggestions. Returns a download URL. "
            "Use when the user wants a complete shareable birth chart document "
            "to print, email, or present. "
            "For interactive on-screen analysis use the individual tools "
            "(asterwise_get_natal_chart, asterwise_get_dasha, asterwise_get_yogas). "
            "Source: compiled BPHS-style report — all calculations audited against "
            "BPHS and Phaladeepika."
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
            "Generate a PDF matchmaking report for two charts — includes Ashtakoota "
            "Guna Milan score (out of 36), Rajju veto analysis, Vedha veto analysis, "
            "Papa Samyam malefic balance, and Nadi Dosha check — compiled into a "
            "formatted shareable document. Returns a download URL. "
            "Use when families need a formal compatibility document. "
            "For interactive compatibility analysis without a PDF use "
            "asterwise_get_compatibility instead. "
            "Source: BPHS Chapter 18 compatibility framework."
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
            "Generate a PDF Vimshottari Dasha timeline — all five levels (Maha "
            "through Prana Dasha) mapped visually with period dates, planet "
            "significations, and lifecycle markers. Returns a download URL. "
            "Use when the user needs a printable Dasha reference document to "
            "consult over time, not for on-screen analysis. "
            "For on-screen Dasha data use asterwise_get_dasha instead. "
            "Source: BPHS Dasha presentation."
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
            "includes the annual chart, year lord (Varsha Pati) with election scores, "
            "Muntha sign and Muntha Lord, Tajika planet-pair aspect matrix with "
            "Ithsala detection, Pancha Adhikari analysis, and year-ahead predictions. "
            "Returns a download URL. "
            "Use when the user wants a formal annual forecast document. "
            "For on-screen Varshaphal data, use asterwise_get_varshaphal instead. "
            "Source: Varshaphal tradition — Tajika Neelakanthi."
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

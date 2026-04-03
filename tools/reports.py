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
        description='Generate a comprehensive Kundli PDF — includes natal chart, all 16\ndivisional charts, full Vimshottari Dasha tree, yoga analysis,\ndosha summary, Avakahada table, and remedial suggestions. Returns a\ndownload URL. Compute class: heavy (~3–8 seconds). Treat as async.\nSource: compiled BPHS-style report.\n\nOUTPUT CONTRACT (response_format=json):\ndata.url (string — full URL:\n  http://api.asterwise.com/v1/report/download/{token})\ndata.expires_at (ISO datetime string, UTC, 24 hours from generation)\n\nThe download URL requires a valid API key (Authorization: Bearer).\nURL is valid for 24 hours. In multi-worker Railway deployments,\nset REDIS_URL so PDF tokens are shared across instances — without it,\ndownload will fail if a different worker receives the GET request.\n\nIf PDF generation fails server-side → 500 with standard error envelope.\nNo retry token is issued — call again to generate a new one.\n\nFor interactive on-screen analysis use asterwise_get_natal_chart,\nasterwise_get_dasha, and asterwise_get_yogas.',
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
        description='Generate a PDF matchmaking report compiling Ashtakoota Guna Milan\nscore (out of 36), Rajju veto analysis, Vedha veto analysis, Papa\nSamyam malefic balance, and Nadi Dosha check. Returns a download URL\nvalid for 24 hours. Source: BPHS Chapter 18 compatibility framework.\n\nOUTPUT CONTRACT (response_format=json):\ndata.url (string — full URL to PDF download endpoint:\n  http://api.asterwise.com/v1/report/download/{token})\ndata.expires_at (ISO datetime string, UTC, 24h from generation)\n\nThe download URL requires a valid API key in the Authorization header.\nURL is valid for 24 hours from expires_at timestamp. In multi-worker\nRailway deployments, REDIS_URL must be set or download tokens will not\nbe shared across instances.\n\nERROR CONTRACT: If PDF generation fails server-side, returns 500\nwith standard error envelope. No retry token is issued on failure —\ncall again to generate a new token.\n\nFor interactive compatibility analysis without a PDF, use\nasterwise_get_compatibility instead.\n\nCompute class: heavy (~3–8 seconds). Treat as async.',
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
        description='Generate a PDF Vimshottari Dasha timeline — all five levels (Maha\nthrough Prana Dasha) with period dates, planet significations, and\nlifecycle markers. Returns a download URL. Compute class: heavy.\nSource: BPHS Dasha presentation.\n\nOUTPUT CONTRACT (response_format=json):\ndata.url (string — http://api.asterwise.com/v1/report/download/{token})\ndata.expires_at (ISO UTC, 24 hours from generation)\n\nSame URL/token/Redis behaviour as asterwise_generate_kundli_report.\nIf generation fails → 500. Call again for a new token.\n\nFor on-screen Dasha data use asterwise_get_dasha instead.',
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
        description="Generate a Varshaphal (Solar Return) PDF report for a specific year —\nincludes the annual chart, year lord, Muntha position, Pancha Adhikari,\nTajika aspects, and year-ahead analysis. Returns a download URL.\nCompute class: heavy. Source: Varshaphal tradition.\n\nCRITICAL PARAMETER: year = 4-digit calendar year (e.g. 2026),\nNOT the person's age. Passing age instead of year produces incorrect\nresults. Same warning as asterwise_get_varshaphal.\n\nOUTPUT CONTRACT (response_format=json):\ndata.url (string — http://api.asterwise.com/v1/report/download/{token})\ndata.expires_at (ISO UTC, 24 hours from generation)\n\nSame URL/token/Redis behaviour as asterwise_generate_kundli_report.\nIf generation fails → 500. Call again for a new token.\n\nFor on-screen Varshaphal data use asterwise_get_varshaphal instead.",
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

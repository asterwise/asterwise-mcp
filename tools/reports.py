"""PDF report generation (stateful URLs — not idempotent)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat
from runtime import (
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
        description="Requests a compiled Kundli PDF from birth data and returns a time-limited HTTPS URL plus expiry metadata for download.\n\nSECTION: WHAT THIS TOOL COVERS\nTriggers a synchronous upstream job that assembles a full BPHS-style PDF package (natal, vargas, dasha, yogas, doshas, avakhada, remedial sections as implemented server-side) and responds with a bearer-protected download link. It does not return structured chart JSON — use asterwise_get_natal_chart and related tools for programmatic slices. Multi-step PDF orchestration beyond this single POST is out of scope.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — preview chart logic before paying PDF latency.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract. The call blocks up to the client timeout (45s) while the upstream generates the file. No partial token is returned on failure — callers must invoke again.\n\nSECTION: OUTPUT CONTRACT\ndata.url (string — full URL to the PDF download endpoint)\ndata.expires_at (string — ISO UTC, 24 hours TTL from generation)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nHEAVY_ASYNC (~3–8 seconds, synchronous call with 45-second timeout — do not call inline in a synchronous pipeline)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — REDIS_URL must be set on multi-worker Railway hosts or download tokens may not be shared across instances.\n  — No retry token on failure; call the tool again.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — returns JSON chart rows, not a PDF URL.\nasterwise_generate_dasha_report — PDF focused on Vimshottari presentation only.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Builds a matchmaking PDF from two birth profiles and returns a bearer-protected download URL with a 24-hour expiry timestamp.\n\nSECTION: WHAT THIS TOOL COVERS\nRuns the upstream PDF pipeline for paired BirthData (Ashtakoota, vetoes, Papa Samyam, Nadi, and related sections as implemented) and returns only url + expires_at. It does not return the numeric breakdown JSON — use asterwise_get_compatibility or regional porutham tools for interactive scoring.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_compatibility — sanity-check scores before PDF latency.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nTwo full BirthData objects are required. Synchronous POST with 45s client timeout; failures produce no download token.\n\nSECTION: OUTPUT CONTRACT\ndata.url (string — full URL to PDF download endpoint)\ndata.expires_at (string — ISO UTC, 24h TTL)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nHEAVY_ASYNC (~3–8 seconds, synchronous call with 45-second timeout — do not call inline in a synchronous pipeline)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — REDIS_URL must be set on multi-worker Railway hosts or download tokens may not be shared across instances.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_compatibility — live JSON Guna Milan breakdown, not a PDF.\nasterwise_generate_kundli_report — single-native Kundli PDF, not paired matchmaking.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Generates a multi-level Vimshottari Dasha PDF from birth data and returns a download URL plus expiry time.\n\nSECTION: WHAT THIS TOOL COVERS\nProduces a PDF presentation of the full Vimshottari tree depth offered by the report service (Maha through Prana as implemented upstream). It does not return JSON period rows — use asterwise_get_dasha for programmatic dasha trees.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_dasha — validate period structure before PDF latency.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract. Synchronous 45s-timeout POST; on failure there is no URL.\n\nSECTION: OUTPUT CONTRACT\ndata.url (string — full URL to PDF download endpoint)\ndata.expires_at (string — ISO UTC, 24h TTL)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nHEAVY_ASYNC (~3–8 seconds, synchronous call with 45-second timeout — do not call inline in a synchronous pipeline)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — REDIS_URL must be set on multi-worker Railway hosts or download tokens may not be shared across instances.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — JSON dasha tree with levels parameter, not a PDF.\nasterwise_generate_kundli_report — full Kundli PDF bundle, not dasha-only.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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
        description="Runs Varshaphal chart computation then report generation and returns a PDF download URL with expiry — two upstream calls in one tool.\n\nSECTION: WHAT THIS TOOL COVERS\nSequentially calls solar-return computation and the Varshaphal PDF builder; either step failing aborts the tool with MCP INTERNAL_ERROR. The output is only url and expires_at like other report tools. It does not return the full Tajika JSON — use asterwise_get_varshaphal for structured annual chart data.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_varshaphal — confirm the annual chart JSON before PDF latency.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nyear must be a four-digit calendar year (e.g. 2026), not biological age; this is not enforced locally and wrong values yield wrong years. BirthData follows the global contract. Two POSTs each honor the 45s client timeout budget in aggregate risk.\n\nSECTION: OUTPUT CONTRACT\ndata.url (string — full URL to PDF download endpoint)\ndata.expires_at (string — ISO UTC, 24h TTL)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nHEAVY_ASYNC (~3–8 seconds, synchronous call with 45-second timeout — do not call inline in a synchronous pipeline)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout on either the chart or report call → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Failure in either upstream step fails the whole tool; no partial PDF token.\n  — REDIS_URL must be set on multi-worker Railway hosts or download tokens may not be shared across instances.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_varshaphal — returns JSON solar return and Tajika structures, not a PDF link.\nasterwise_generate_kundli_report — natal-focused PDF, not annual varshaphal.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
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

"""Matchmaking and compatibility (BPHS Ch.18 and South Indian systems)."""

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


def _ashtakoota_md(data: dict[str, Any]) -> str:
    lines = [
        "## Ashtakoota (Guna Milan)",
        "",
        "Per **BPHS Ch.18**: evaluate **Rajju** and **Vedha** as hard vetoes before trusting the total score.",
        "",
    ]
    kootas = data.get("kootas") or data.get("ashtakoota") or data.get("guna")
    if isinstance(kootas, list):
        lines.append("| Koota | Score | Max | Notes |")
        lines.append("|-------|-------|-----|-------|")
        for row in kootas:
            if isinstance(row, dict):
                lines.append(
                    f"| {row.get('name', '—')} | {row.get('score', '—')} | "
                    f"{row.get('max', '—')} | {row.get('notes', '')} |"
                )
        lines.append("")
    for veto in ("rajju", "vedha"):
        if veto in data:
            lines.append(f"- **{veto.title()} veto**: {data[veto]}")
    lines.append("")
    lines.append(structured_markdown("Full compatibility payload", data))
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    def _pair_body(p1: BirthData, p2: BirthData) -> dict[str, Any]:
        return {"person1": p1.to_api_dict(), "person2": p2.to_api_dict()}

    @mcp.tool(
        name="asterwise_get_compatibility",
        description=(
            "Calculate Ashtakoota Guna Milan — the standard North Indian matchmaking "
            "system that scores compatibility across eight kootas: Varna (1pt), "
            "Vashya (2pt), Tara (3pt), Yoni (4pt), Graha Maitri (5pt), Gana (6pt), "
            "Bhakoot (7pt), and Nadi (8pt), totalling 36 points. Also evaluates "
            "Rajju and Vedha as hard vetoes — a match failing either veto should not "
            "proceed regardless of the Guna total (Parashara's explicit instruction). "
            "Source: BPHS Chapter 18. "
            "Use for all standard North Indian marriage compatibility assessments. "
            "Use asterwise_get_dashakoot for South Indian 10-point system, "
            "asterwise_get_porutham for Tamil 10-point system, or "
            "asterwise_get_thirumana_porutham for Tamil 12-koota system instead."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_compatibility(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Ashtakoota with vetoes."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(data, response_format, _ashtakoota_md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_compatibility", exc)

    @mcp.tool(
        name="asterwise_get_dashakoot",
        description=(
            "Calculate Dashakoot compatibility — the South Indian 10-point system that "
            "extends Ashtakoota with additional factors. Includes Rajju and Vedha as "
            "vetoes. Source: South Indian marriage astrology texts. "
            "Use when the couple or their families follow South Indian matching "
            "traditions, particularly Kannada or Telugu communities. "
            "Use asterwise_get_compatibility for standard North Indian Ashtakoota, "
            "asterwise_get_porutham for Tamil tradition."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_dashakoot(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dashakoot."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/dashakoot",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dashakoot", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dashakoot", exc)

    @mcp.tool(
        name="asterwise_get_papasamyam",
        description=(
            "Calculate Papa Samyam — the assessment of malefic planet balance between "
            "two charts. Checks whether the malefic affliction level (Mangal Dosha and "
            "related factors) is comparable between the partners, since serious "
            "imbalance is considered inauspicious. Source: classical dosha-matching logic. "
            "Use alongside Ashtakoota when Mangal Dosha is present in one or both charts "
            "to determine whether the dosha is balanced or cancelled. "
            "This is a supplementary check — always run asterwise_get_compatibility first."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_papasamyam(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Papa Samyam."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/papasamyam",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Papa Samyam", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_papasamyam", exc)

    @mcp.tool(
        name="asterwise_get_porutham",
        description=(
            "Calculate Tamil Porutham — the 10-point marriage compatibility system "
            "used in Tamil Nadu. The ten Poruthams are: Dinam, Ganam, Mahendram, "
            "Stree Deergham, Yoni, Rasi, Rasiyathipaty, Rajju, Vetham, and Vasiyam. "
            "Rajju and Vedha are absolute vetoes. Source: Tamil marriage astrology tradition. "
            "Use for Tamil community marriage matching. "
            "Use asterwise_get_thirumana_porutham for the extended 12-koota Tamil system."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Tamil Porutham."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/porutham",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Porutham", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_porutham", exc)

    @mcp.tool(
        name="asterwise_get_thirumana_porutham",
        description=(
            "Calculate Thirumana Porutham — the extended Tamil marriage compatibility "
            "system with 12 kootas, offering more granular assessment than the standard "
            "10-point Porutham. Source: Tamil marriage classics. "
            "Use when a more detailed Tamil compatibility analysis is required beyond "
            "the standard 10-point Porutham."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_thirumana_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Thirumana Porutham."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/thirumana-porutham",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Thirumana Porutham", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_thirumana_porutham", exc)

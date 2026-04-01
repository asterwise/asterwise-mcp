"""Matchmaking and compatibility (BPHS Ch.18 and South Indian systems)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from client import get_client
from models import BirthData, ResponseFormat, birth_dict
from runtime import (
    STANDARD_ANNOTATIONS,
    format_tool_result,
    mcp_error_message,
    require_api_key,
    structured_markdown,
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
        return {"person1": birth_dict(p1), "person2": birth_dict(p2)}

    @mcp.tool(
        name="asterwise_get_compatibility",
        description=(
            "Calculate Ashtakoota Guna Milan — eight kootas, total /36, and **Rajju** / **Vedha** as hard "
            "vetoes (not soft scores). A match failing Rajju or Vedha should not proceed regardless of Guna "
            "score (Parashara). Source: BPHS Ch.18.\n"
            "Inputs: person1 BirthData, person2 BirthData, response_format.\n"
            "Returns: Koota table, veto status, assessment."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_compatibility(
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Ashtakoota with vetoes."""
        try:
            api_key = await require_api_key()
            data = await get_client().post(
                "/v1/astro/matchmaking", api_key, _pair_body(person1, person2)
            )
            return format_tool_result(data, response_format, _ashtakoota_md)
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_dashakoot",
        description=(
            "Dashakoot compatibility — 10-point South Indian system including Rajju, Vedha, and extended "
            "kootas. Source: regional marriage compatibility texts.\n"
            "Inputs: two BirthData, response_format.\n"
            "Returns: 10-point breakdown."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_dashakoot(
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Dashakoot."""
        try:
            api_key = await require_api_key()
            data = await get_client().post(
                "/v1/astro/matchmaking/dashakoot",
                api_key,
                _pair_body(person1, person2),
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dashakoot", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_papasamyam",
        description=(
            "Papa Samyam — malefic balance between charts (relevant for Mangal Dosha and related rules). "
            "Source: classical dosha-matching logic.\n"
            "Inputs: two BirthData, response_format.\n"
            "Returns: Papa Samyam analysis."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_papasamyam(
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Papa Samyam."""
        try:
            api_key = await require_api_key()
            data = await get_client().post(
                "/v1/astro/matchmaking/papasamyam",
                api_key,
                _pair_body(person1, person2),
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Papa Samyam", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_porutham",
        description=(
            "Tamil Porutham — 10-point compatibility with Rajju and Vedha as absolute vetoes. Source: Tamil "
            "marriage astrology.\n"
            "Inputs: two BirthData, response_format.\n"
            "Returns: 10 Porutham results."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_porutham(
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Tamil Porutham."""
        try:
            api_key = await require_api_key()
            data = await get_client().post(
                "/v1/astro/matchmaking/porutham",
                api_key,
                _pair_body(person1, person2),
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Porutham", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

    @mcp.tool(
        name="asterwise_get_thirumana_porutham",
        description=(
            "Thirumana Porutham — extended 12-koota Tamil compatibility. Source: Tamil marriage classics.\n"
            "Inputs: two BirthData, response_format.\n"
            "Returns: 12 koota results."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_thirumana_porutham(
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Thirumana Porutham."""
        try:
            api_key = await require_api_key()
            data = await get_client().post(
                "/v1/astro/matchmaking/thirumana-porutham",
                api_key,
                _pair_body(person1, person2),
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Thirumana Porutham", d),
            )
        except Exception as exc:
            return mcp_error_message(exc)

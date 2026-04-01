"""Yoga detection, dosha analysis, and remedies."""

from __future__ import annotations

from fastmcp import FastMCP
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
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_yogas",
        description=(
            "Detect classical yogas (Raj, Dhana, Mahapurusha, Neecha Bhanga, Parivartana, Gajakesari, "
            "etc.) with formation conditions. Source: BPHS / Phaladeepika / Saravali.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: List of yogas present in the chart."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_yogas(
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Chart yogas."""
        try:
            api_key = await require_api_key()
            data = await get_client().post("/v1/astro/yoga", api_key, birth_dict(birth))
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Yogas", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

    @mcp.tool(
        name="asterwise_get_doshas",
        description=(
            "Analyse classical doshas (Mangal, Kaal Sarpa, Guru Chandal, Kemdrum, etc.) with severity and "
            "remedial context. Source: BPHS and related dosha chapters.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Dosha checklist with severity."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_doshas(
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Dosha analysis."""
        try:
            api_key = await require_api_key()
            data = await get_client().post("/v1/astro/dosha", api_key, birth_dict(birth))
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Doshas", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

    @mcp.tool(
        name="asterwise_get_remedies",
        description=(
            "Classical Jyotish remedies — gemstones, mantras, charity, rituals. Source: remedial "
            "sections of BPHS / tradition.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Remedies keyed by planet or theme."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_remedies(
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Parashari-style remedies."""
        try:
            api_key = await require_api_key()
            data = await get_client().post("/v1/astro/remedies", api_key, birth_dict(birth))
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Remedies", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

    @mcp.tool(
        name="asterwise_get_gemstone_recommendations",
        description=(
            "Gemstone recommendations from the natal chart — primary/secondary stones and wearing method. "
            "Source: classical ratna shastra.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Stone recommendations with rationale."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_gemstone_recommendations(
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Gemstones."""
        try:
            api_key = await require_api_key()
            data = await get_client().post("/v1/astro/gemstones", api_key, birth_dict(birth))
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Gemstone recommendations", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

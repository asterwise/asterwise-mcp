"""Yoga detection, dosha analysis, and remedies."""

from __future__ import annotations

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


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_yogas",
        description=(
            "Detect classical yogas present in the natal chart with formation "
            "conditions and classical results. Currently detects: Gajakesari, "
            "Chandra-Mangal, Dhana yogas (house-based and planetary), "
            "Papa Kartari (malefic scissors on Lagna and Moon), Parivartana "
            "(mutual exchange), select Raja yogas (Kendra-Kona combinations), "
            "and Viparita Raja yoga. Pancha Mahapurusha and Neecha Bhanga "
            "detection coverage is expanding. "
            "Source: BPHS Chapters 36, 38, 41 — Phaladeepika Chapters 6, 7."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_yogas(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Chart yogas."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/yoga", api_key, birth.to_api_dict())
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Yogas", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_yogas", exc)

    @mcp.tool(
        name="asterwise_get_doshas",
        description=(
            "Analyse classical doshas — afflictions and imbalances present in the "
            "natal chart. Checks for: Mangal Dosha (Mars in 1st, 2nd, 4th, 7th, 8th, "
            "or 12th house — relevant for marriage), Kaal Sarp Dosha (all planets "
            "between Rahu-Ketu axis), Guru Chandal Dosha (Jupiter-Rahu conjunction), "
            "Kemdrum Dosha (Moon without flanking planets), and others. Returns "
            "severity, the specific formation, and whether cancellation conditions "
            "(bhanga) apply. Source: BPHS and classical dosha chapters. "
            "Use when assessing chart afflictions, delays, or when a user is facing "
            "persistent obstacles and wants to know if a dosha is present. "
            "Always check bhanga (cancellation) conditions before concluding a dosha "
            "is active — many doshas are cancelled by counter-combinations."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_doshas(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dosha analysis."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/dosha", api_key, birth.to_api_dict())
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Doshas", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_doshas", exc)

    @mcp.tool(
        name="asterwise_get_remedies",
        description=(
            "Get classical Jyotish remedies for a natal chart — mantras, gemstones, "
            "charity, fasting, and ritual recommendations based on the chart's "
            "planetary weaknesses and afflictions. Source: remedial sections of BPHS, "
            "Ratna Shastra, and classical tradition. "
            "Use when the user wants to know what they can do to strengthen weak "
            "planets or reduce dosha effects. "
            "Do not confuse with asterwise_get_lal_kitab_remedies — that provides "
            "Lal Kitab-specific practical remedies (feeding birds, flowing items in "
            "rivers); this provides BPHS/Parashari remedies (mantras, gemstones, rituals). "
            "Do not confuse with asterwise_get_gemstone_recommendations — that focuses "
            "exclusively on gemstone selection; this provides the full remedial picture."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_remedies(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Parashari-style remedies."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/remedies", api_key, birth.to_api_dict())
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Remedies", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_remedies", exc)

    @mcp.tool(
        name="asterwise_get_gemstone_recommendations",
        description=(
            "Get gemstone recommendations from the natal chart — the primary stone "
            "(for the Lagna lord or most important planet), secondary/supporting stones, "
            "and contraindicated stones to avoid. Includes metal, finger, and weight "
            "guidance per classical Ratna Shastra. Source: classical gem therapy texts. "
            "Use when the user specifically asks about which gemstone to wear. "
            "Do not confuse with asterwise_get_remedies — that provides the complete "
            "remedial picture including mantras, fasting, and charity alongside gems; "
            "this focuses exclusively on gemstone selection and wearing guidance."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_gemstone_recommendations(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Gemstones."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/gemstones", api_key, birth.to_api_dict())
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Gemstone recommendations", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_gemstone_recommendations", exc)

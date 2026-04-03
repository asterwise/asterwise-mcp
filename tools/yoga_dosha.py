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
            "conditions and classical results. Fully audited against BPHS and "
            "Phaladeepika. Detects 80+ yogas across all major categories: "
            "all five Pancha Mahapurusha (Ruchaka/Bhadra/Hamsa/Malavya/Sasa) "
            "from Lagna and Moon; Gajakesari from Lagna and Moon; Neecha Bhanga "
            "Raja Yoga with all six classical cancellation conditions; full Raj "
            "Yoga suite including Dharma-Karma Adhipati and Dharma-Mantra Adhipati; "
            "Yogakaraka and Yoganashaka per Ascendant; Viparita Raja Yoga "
            "(Harsha/Sarala/Vimala) with Full Viparita flag; Parivartana "
            "(Maha/Khala/Dainya classification); Dhana Yogas with BPHS Ch.43 "
            "specific combinations; Adhi Yoga with Chandradhi/Lagnadhi tiers "
            "(commander/minister/ruler); Lakshmi Yoga; Maharaja Yoga (6-condition "
            "BPHS Ch.41); Budhaditya with combustion exception; Chandra-Mangal; "
            "Papa Kartari and Shubha Kartari; Sunapha/Anapha/Durudhara; all 6 "
            "Surya Yogas (Subhavesi/Subhavasi/Subhobhayachari and malefic variants); "
            "complete Nabhasha system (3 Aashraya + 2 Dala + all 20 Aakriti + "
            "7 Sankhya = 32 Nabhasha Yogas); Graha Drishti aspect matrix. "
            "Each yoga returns formation conditions, cancellation status, classical "
            "results, and interpretation text. "
            "Source: BPHS Chapters 36–41, 77 — Phaladeepika Chapters 6, 7, 9."
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
            "natal chart. Fully audited against BPHS and Phaladeepika. Detects "
            "14 doshas: Mangal Dosha (Mars in houses 1/2/4/7/8/12 from Lagna, "
            "Moon, and Venus with D9 secondary check — severity tiers, all 5 "
            "cancellation conditions including Yogakaraka and house-sign exceptions); "
            "Kala Sarpa and Kala Amrita (sign-based nodal containment); Guru Chandal "
            "(Jupiter-Rahu conjunction with secondary 7th-aspect form and mitigation "
            "flag); Kemadruma (Moon isolation per Phaladeepika Adhyaya 6 Sloka 5 — "
            "Sun/Rahu/Ketu excluded from prevention, 3 cancellation conditions); "
            "Grahan (Sun/Moon conjunct Rahu or Ketu — 4 sub-types); Shrapit "
            "(Saturn-Rahu conjunction); Pitru Dosha (Sun or 9th lord in Dusthana "
            "or afflicted by Rahu/Saturn/Mars — either alone is sufficient); "
            "Gandmool with deep Gandanta pada flags for all 6 junction Nakshatras; "
            "Shani (natal Saturn affliction assessment + Sade Sati reference); "
            "Paap Kartari for all 12 houses with per-house flags; Gulika position "
            "with dosha-sensitive house flag. Returns severity, formation details, "
            "and bhanga (cancellation) conditions for each. "
            "Source: BPHS dosha chapters — Phaladeepika Adhyaya 6, 12."
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

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
        description="Detect classical yogas in the natal chart with formation conditions,\nclassical results, and modern interpretation. Call asterwise_get_natal_chart\nfirst — this tool requires the same birth data to compute the chart.\n\nCurrently detects: Gajakesari, Chandra-Mangal, Dhana yogas\n(house-based and planetary), Papa Kartari (malefic scissors on Lagna\nand Moon), Parivartana (mutual exchange), Raja yogas (Kendra-Kona\ncombinations), Viparita Raja yoga, Pancha Mahapurusha yogas,\nNeecha Bhanga Raja yoga, and others. Detection coverage is expanding —\nnew yogas are added without versioning. Source: BPHS Chapters 36, 38,\n41; Phaladeepika Chapters 6, 7.\n\nOUTPUT CONTRACT (response_format=json):\ndata.yogas[] — array of yoga objects, each:\n  yoga_name (string, descriptive label)\n  category (string: 'raja_yogas', 'dhana_yogas', 'pancha_mahapurusha',\n    or 'unknown' when interpretation data is pending)\n  formation (string, describes the planetary combination that formed it)\n  classical_results (string, traditional text results)\n  modern_summary (string, contemporary interpretation)\n  keywords[] (string array)\n  Note: when category='unknown', formation and classical_results may be\n  empty strings — interpretation data is being added iteratively.\ndata.birth_time_unknown (bool)\n\nGraha Drishti (aspect matrix) is returned separately in\nasterwise_get_natal_chart under data.graha_drishti — it is a\ndifferent data structure from yogas and is not included here.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not confuse with asterwise_get_chart_strength — that tool measures\nraw planetary power via Shadbala; this tool identifies specific\nclassical configurations regardless of strength.",
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
        description="Analyse all classical doshas — natal afflictions — present in the\nchart. Call asterwise_get_natal_chart first. Source: BPHS and\nclassical dosha chapters.\n\nChecks 12 doshas: mangal_dosha, shani_dosha, shrapit_dosha,\ngrahan_dosha, kala_sarpa (key: 'kala_sarpa'), guru_chandal\n(key: 'guru_chandal'), kemadruma_dosha (key: 'kemadruma_dosha'),\npaap_kartari, pitru_dosha, gandmool_dosha, nadi_dosha, gulika.\n\nOUTPUT CONTRACT (response_format=json):\ndata.doshas — fixed object with the 12 keys above. Each dosha:\n  present (bool)\n  types[] (string array, sub-types when applicable)\n  details{} (type-specific dict — varies per dosha; mangal_dosha\n    includes mars_house, from_moon, from_venus, d9_present,\n    severity, cancellations[]; gulika includes longitude, sign_index,\n    sign_name, house, dosha_sensitive)\n  interpretation_summary (string or null — null when pending)\n  keywords (array or null)\n  remedies[] (string array or null)\ndata.birth_time_unknown (bool)\n\nAlways check cancellation (bhanga) conditions in details.cancellations[]\nbefore concluding a dosha is active. Many doshas are cancelled by\ncounter-combinations.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not confuse with asterwise_get_chart_strength — doshas measure\nafflictions; Shadbala measures raw power.",
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
        description="Get classical Jyotish remedies for the natal chart — mantras,\ngemstones, charity, fasting, and ritual recommendations based on\nplanetary weaknesses and afflictions. Call asterwise_get_natal_chart\nfirst — remedies are computed from the chart's planetary dignities.\nSource: remedial sections of BPHS, Ratna Shastra.\n\nOUTPUT CONTRACT (response_format=json):\ndata.recommended_remedies[] — one object per weak/afflicted planet:\n  planet, dignity (string: 'debilitated', 'enemy', 'neutral', etc.),\n  rashi, house, is_dusthana_lord (bool), reason (string),\n  mantra (string), repetitions (int, typically 108), deity,\n  gemstone, colour, metal, fast_day, charity, action_daily,\n  action_weekly\ndata.planet_dignities[] — all 9 planets: planet, dignity, rashi, house\n\nIf the chart has no weak planets, data.recommended_remedies[] is an\nempty array — not an error.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not confuse with asterwise_get_lal_kitab_remedies — that provides\nLal Kitab practical remedies (household actions, feeding birds). This\nprovides BPHS/Parashari remedies (mantras, gemstones, rituals).\nDo not confuse with asterwise_get_gemstone_recommendations — that\nfocuses exclusively on gemstone selection.",
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
        description='Get gemstone recommendations from the natal chart — primary stone,\nsecondary stone, Yogakaraka gem, 5th lord gem, 9th lord gem,\nAtmakaraka gem, and contraindicated stones to avoid. Call\nasterwise_get_natal_chart first.\nSource: classical Ratna Shastra gem therapy texts.\n\nOUTPUT CONTRACT (response_format=json):\ndata.primary — { planet, reason, gemstone (may be empty string if\n  withheld due to dual lordship), substitute_gemstone, metal,\n  colour, note, caution }\ndata.yogakaraka_gem — { planet, gemstone }\ndata.fifth_lord_gem — { planet, gemstone }\ndata.ninth_lord_gem — { planet, gemstone }\ndata.atmakaraka_gem — { planet, gemstone }\ndata.secondary — { planet, gemstone }\ndata.contraindicated[] — { planet, gemstone, reason }\ndata.note (string, safety disclaimer)\n\nNote: a gemstone may appear in both secondary and contraindicated when\nit serves different roles — always read the reason field.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nFor the full remedial picture (mantras, fasting, charity) use\nasterwise_get_remedies. This focuses exclusively on gemstone selection.',
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

"""Yoga detection, dosha analysis, and remedies."""

from __future__ import annotations

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
        name="asterwise_get_yogas",
        title="Yogas",
        description="Evaluates the natal chart for named classical yogas and returns category, formation text, classical results, modern summaries, and keywords per hit.\n\nSECTION: WHAT THIS TOOL COVERS\nDetects an open-ended set of named yogas and emits the data.yogas[] list; categories include raja_yogas, dhana_yogas, pancha_mahapurusha, chandra_yogas, surya_yogas, kartari_yogas, or unknown while metadata is pending. It does not return the Graha Drishti matrix (see asterwise_get_natal_chart data.graha_drishti), Shadbala scores, or divisional charts. New yogas may appear without API versioning.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — same birth tuple should be understood before interpreting yoga names.\nAFTER: asterwise_get_doshas — complementary affliction scan on the same chart.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract. time='00:00' is accepted without flag; yoga house logic may be wrong if true birth time is unknown.\n\nSECTION: OUTPUT CONTRACT\ndata.yogas[] — each object:\n  yoga_name (string)\n  category (string — 'raja_yogas', 'dhana_yogas', 'pancha_mahapurusha', 'chandra_yogas', 'surya_yogas', 'kartari_yogas', or 'unknown' while metadata is pending)\n  formation (string — empty when yoga has no JSON entry yet)\n  modern_summary (string)\n  keywords[] (string array)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — Dates before 1800 or after 2100 → MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Graha Drishti lives only on asterwise_get_natal_chart, not in data.yogas[].\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — supplies graha_drishti and base chart rows, not the yoga catalogue.\nasterwise_get_panchanga — Panchanga yoga (Sun+Moon sum) is unrelated to these natal yogas.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Doshas",
        description="Scores twelve fixed dosha buckets from birth data and returns presence flags, typed detail objects, optional summaries, and remedy lines per dosha.\n\nSECTION: WHAT THIS TOOL COVERS\nMaps mangal_dosha, shani_dosha, shrapit_dosha, grahan_dosha, kala_sarpa, guru_chandal, kemadruma_dosha, paap_kartari, pitru_dosha, gandmool_dosha, nadi_dosha, and gulika — each with present, types[], details{}, interpretation_summary, keywords, remedies[]. It does not replace compatibility Nadi scoring (asterwise_get_compatibility) or Shadbala (asterwise_get_chart_strength). Cancellation arrays inside details (e.g. mangal_dosha) must be read before treating a dosha as final.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — chart familiarity before dosha interpretation.\nAFTER: asterwise_get_remedies — classical remedial suggestions after dosha review.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract. Unknown birth time at midnight is accepted silently.\n\nSECTION: OUTPUT CONTRACT\ndata.doshas — object with exactly twelve keys:\n  mangal_dosha, shani_dosha, shrapit_dosha, grahan_dosha, kala_sarpa, guru_chandal, kemadruma_dosha, paap_kartari, pitru_dosha, gandmool_dosha, nadi_dosha, gulika\nEach value:\n  present (bool)\n  types[] (string array)\n  details{} (object — mangal_dosha includes mars_house, from_moon, from_venus, d9_present, severity, cancellations[]; gulika includes longitude, sign_index, sign_name, house, dosha_sensitive; other keys vary)\n  interpretation_summary (string or null)\n  keywords (array or null)\n  remedies[] (string array or null)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — Dates before 1800 or after 2100 → MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Many doshas include cancellation lists inside details — read before concluding severity.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_chart_strength — Shadbala/Vimshopaka power metrics, not dosha booleans.\nasterwise_get_compatibility — pair scoring including nadi_dosha flags, not the twelve natal dosha buckets.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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
        title="Remedies",
        description="Derives classical remedial prescriptions from planetary weakness and dusthana lordship and returns mantra, lifestyle, charity, and dignity tables.\n\nSECTION: WHAT THIS TOOL COVERS\nBuilds data.recommended_remedies[] for grahas judged weak or afflicted plus data.planet_dignities[] for all nine planets. It is not Lal Kitab totka advice (asterwise_get_lal_kitab_remedies) nor a curated gem safety brief (asterwise_get_gemstone_recommendations). Empty recommended_remedies[] means no weak planets were flagged — not an error.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — chart context before choosing remedies.\nAFTER: asterwise_get_gemstone_recommendations — optional focused gem briefing.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.recommended_remedies[] — each object:\n  planet (string)\n  dignity (string — e.g. 'debilitated', 'enemy', 'neutral')\n  rashi (string)\n  house (int)\n  is_dusthana_lord (bool)\n  reason (string)\n  mantra (string)\n  repetitions (int — typically 108)\n  deity (string)\n  gemstone (string)\n  colour (string)\n  metal (string)\n  fast_day (string)\n  charity (string)\n  action_daily (string)\n  action_weekly (string)\ndata.planet_dignities[] — nine objects: planet, dignity, rashi, house (int)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — Dates before 1800 or after 2100 → MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Empty data.recommended_remedies[] when no weak grahas — valid success.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_lal_kitab_remedies — household Lal Kitab totkas, not mantra/gem classical rows.\nasterwise_get_gemstone_recommendations — gemstone roles and contraindications only, not full lifestyle remedies.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_remedies(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Classical-style remedies."""
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
        title="Gemstone Recommendations",
        description="Computes Ratna-style gemstone picks and cautions from the natal chart and returns primary, role-based stones, secondary options, contraindications, and a safety note.\n\nSECTION: WHAT THIS TOOL COVERS\nSurfaces data.primary, yogakaraka/fifth/ninth/atmakaraka gems, secondary, contraindicated[], and note. Gemstone may be an empty string in primary when dual lordship withholds a recommendation. It does not emit mantra or fasting guidance (asterwise_get_remedies) or Lal Kitab totkas (asterwise_get_lal_kitab_remedies). The same mineral may appear in secondary and contraindicated with different reasons — read reason fields.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — confirm chart before wearing advice.\nAFTER: asterwise_get_remedies — broader remedial programme if needed.\n\nSECTION: INPUT CONTRACT\nBirthData follows the global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.primary:\n  planet (string)\n  reason (string)\n  gemstone (string — may be empty when withheld for dual lordship)\n  substitute_gemstone (string)\n  metal (string)\n  colour (string)\n  note (string)\n  caution (string)\ndata.yogakaraka_gem — { planet (string), gemstone (string) }\ndata.fifth_lord_gem — { planet (string), gemstone (string) }\ndata.ninth_lord_gem — { planet (string), gemstone (string) }\ndata.atmakaraka_gem — { planet (string), gemstone (string) }\ndata.secondary — { planet (string), gemstone (string) }\ndata.contraindicated[] — { planet (string), gemstone (string), reason (string) }\ndata.note (string — safety disclaimer)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — Dates before 1800 or after 2100 → MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Gemstone duplication across secondary and contraindicated is intentional when roles conflict.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_remedies — mantras, fasting, charity rows, not a gem matrix.\nasterwise_get_lal_kitab_remedies — Lal Kitab actions, not classical Ratna picks.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
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

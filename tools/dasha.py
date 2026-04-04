"""Vimshottari and alternative Dasha systems (timing)."""

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


def _dasha_tree_md(data: dict[str, Any]) -> str:
    periods = data.get("periods") or data.get("dasha") or data.get("vimshottari")
    lines = ["## Vimshottari Dasha", ""]
    if isinstance(periods, list):
        for block in periods[:200]:
            if isinstance(block, dict):
                label = block.get("planet") or block.get("lord") or block.get("name", "—")
                start = block.get("start") or block.get("start_date") or ""
                end = block.get("end") or block.get("end_date") or ""
                bal = block.get("balance") or block.get("balance_at_birth") or ""
                lines.append(
                    f"- **{label}** — {start} → {end}"
                    + (f" (balance: {bal})" if bal else "")
                )
                children = block.get("antar") or block.get("children") or block.get("sub_periods")
                if isinstance(children, list):
                    for ch in children[:50]:
                        if isinstance(ch, dict):
                            lines.append(
                                f"  - {ch.get('planet', ch.get('lord', '—'))}: "
                                f"{ch.get('start', '')} → {ch.get('end', '')}"
                            )
        lines.append("")
    lines.append("### Raw structure\n\n")
    lines.append(structured_markdown("Dasha details", data))
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_dasha",
        description="Computes Vimshottari Dasha from birth data and returns hierarchical period trees plus current Maha/Antar interpretation blocks.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes the classical Parashari Vimshottari timeline from the Moon's birth nakshatra: Mahadasha and nested sub-periods up to the depth set by levels, with Julian and calendar boundaries and optional modern summaries. It returns data.periods[] and data.interpretation for the active periods. It does not compute Jaimini Char Dasha, Yogini Dasha, Ashtottari, or transit correlations; use the dedicated tools for those systems.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — establishes chart and Moon context before interpreting Dasha lords.\nAFTER: asterwise_get_dasha_transits — correlates active Dasha lords with transits for the same birth data.\n\nSECTION: INPUT CONTRACT\nlevels (int, default 3, max 5): tree depth — 1 = Mahadasha only; 2 adds Antardasha; 3 Pratyantar; 4 Sookshma; 5 Prana (much larger payload). Response dates in periods[] use DD/MM/YYYY, not ISO. BirthData fields follow global contract (date YYYY-MM-DD, time HH:MM; time='00:00' is accepted without flag — lagna-sensitive timing may be wrong if birth time is unknown).\n\nSECTION: OUTPUT CONTRACT\ndata.periods[] — array of Mahadasha objects:\n  planet (string)\n  start_jd (float)\n  end_jd (float)\n  start_date (string — DD/MM/YYYY, not ISO)\n  end_date (string — DD/MM/YYYY)\n  modern_summary (string or null)\n  sub[] — array of Antardasha objects with the same shape; sub=null at deepest level\ndata.interpretation.current_mahadasha:\n  planet (string)\n  start_date (string)\n  end_date (string)\n  duration_years (float)\n  modern_summary (string or null)\n  favorable_conditions[] (string array)\n  favorable_results[] (string array)\n  unfavorable_conditions[] (string array)\n  unfavorable_results[] (string array)\n  timing_note (string)\ndata.interpretation.current_antardasha — same fields as current_mahadasha plus mahadasha_planet (string)\ndata.birth_time_unknown (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (~100ms at levels=1, ~1500ms at levels=5)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — levels < 1 or levels > 5 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — BirthData validation is upstream beyond Pydantic field constraints.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Period start_date/end_date strings are DD/MM/YYYY; do not parse as ISO.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_char_dasha — Jaimini sign-based periods with ISO dates on periods[], not planet-based Vimshottari.\nasterwise_get_yogini_dasha — 36-year eight-Yogini cycle with data.periods.root[], not Vimshottari.\nasterwise_get_ashtottari_dasha — 108-year alternative tree with data.periods.root[] and same levels semantics as this tool.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        levels: int = 3
    ) -> str:
        """Vimshottari Dasha up to five levels."""
        try:
            if levels < 1 or levels > 5:
                invalid_params("levels must be between 1 and 5 inclusive.")
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "levels": levels}
            data = await get_client().post("/v1/astro/dasha", api_key, body, timeout=20.0)
            return format_tool_result(data, response_format, _dasha_tree_md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dasha", exc)

    @mcp.tool(
        name="asterwise_get_dasha_transits",
        description="Combines active Vimshottari lords with today's transits and returns scored correlations plus transit longitudes and houses from Moon and Lagna.\n\nSECTION: WHAT THIS TOOL COVERS\nBuilds a snapshot for the current calendar day (no date parameter): active Mahadasha, Antardasha, and Pratyantar; transiting planet positions; pairwise dasha–transit correlations with scores; and a filtered list of stronger correlations. It does not return full Dasha trees (use asterwise_get_dasha), ingress calendars (asterwise_get_transits), or standalone Gochar without Dasha context (asterwise_get_gochar).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — same birth data should be understood before interpreting houses and lords.\nAFTER: asterwise_get_gochar — optional broader transit snapshot without dasha scoring.\n\nSECTION: INPUT CONTRACT\nNo date field — \"today\" is fixed by the API. All parameters are otherwise defined in the tool schema. BirthData follows the global contract (unknown birth time: time='00:00' accepted without detection).\n\nSECTION: OUTPUT CONTRACT\ndata.target_date (string — YYYY-MM-DD, today)\ndata.active_dasha:\n  start_date (string)\n  end_date (string)\n  maha — { planet (string), start_date (string), end_date (string) }\n  antar — { planet (string), start_date (string), end_date (string) }\n  pratyantar — { planet (string), start_date (string), end_date (string) }\ndata.transit_positions{} — keyed by planet name:\n  rashi_index (int)\n  rashi (string)\n  is_retrograde (bool)\n  house_from_moon (int)\n  house_from_lagna (int)\ndata.correlations[] — each object:\n  dasha_level (string)\n  dasha_lord (string)\n  transit_planet (string)\n  aspect_type (string)\n  score (int — 1=mild, 2=moderate, 3=high)\n  natal_rashi (string)\n  transit_rashi (string)\n  is_retrograde (bool)\n  significance (string)\ndata.periods_of_significance[] — same shape as correlations[] filtered to score ≥ 2\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Target date is always \"today\"; past/future analysis is not supported by this tool.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — full nine-planet Gochar with AVK and vedha fields, without dasha–transit correlation scores.\nasterwise_get_transits — ingress and station lists over a chosen range, not today's dasha snapshot.\nasterwise_get_dasha — full Vimshottari tree without transit overlay.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_dasha_transits(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dasha-period transits."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/dasha-transits", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dasha transits", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dasha_transits", exc)

    @mcp.tool(
        name="asterwise_get_char_dasha",
        description="Computes Jaimini Char Dasha from birth data and returns sign lords as period rulers with ISO-dated Maha and Antar sequences plus karaka mappings.\n\nSECTION: WHAT THIS TOOL COVERS\nUses the Jaimini system where rashis (not grahas) rule time periods, including Atmakaraka, eight karakas, current Maha/Antar labels in Sanskrit signs, and a period array with nested antardashas. It does not return Vimshottari (asterwise_get_dasha), Yogini, or Ashtottari timelines.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — contextualises the chart before interpreting sign-based lords.\nAFTER: asterwise_get_dasha — optional Vimshottari cross-check for the same native.\n\nSECTION: INPUT CONTRACT\nPeriod start_date and end_date in data.periods[] are YYYY-MM-DD (ISO), unlike asterwise_get_dasha which uses DD/MM/YYYY in its tree. All other parameters follow the BirthData global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.atmakaraka (string — planet name)\ndata.start_rashi (string — Sanskrit rashi name)\ndata.start_rashi_index (int)\ndata.karakas{} — object mapping Jaimini karaka keys to planet names\ndata.current_mahadasha (string — Sanskrit rashi name, e.g. 'Mithuna')\ndata.current_antardasha (string — Sanskrit rashi name)\ndata.periods[] — Mahadasha objects:\n  rashi (string)\n  rashi_index (int)\n  years (int)\n  start_date (string — YYYY-MM-DD ISO)\n  end_date (string — YYYY-MM-DD ISO)\n  antardashas[] — same shape as one level (no further nesting)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Two planets at the same degree: classical tie-break rules apply upstream; no separate error.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — Vimshottari planet lords with DD/MM/YYYY in periods[], not sign-based Jaimini Char Dasha.\nasterwise_get_yogini_dasha — eight Yoginis and data.periods.root[], not Jaimini signs.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_char_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Char Dasha."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/char-dasha", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Char Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_char_dasha", exc)

    @mcp.tool(
        name="asterwise_get_yogini_dasha",
        description="Computes the eight-Yogini, 36-year Yogini Dasha cycle with two-level period trees and DD/MM/YYYY boundaries from birth data.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns Mahadasha rows under data.periods.root[] (not data.periods[]), each with Yogini name, ruling planet, Julian and calendar dates, and sub-periods for Antar only (two levels total). The eight Yoginis map to year-lengths 1–8 summing to 36 years per cycle. It does not validate or refuse charts outside classical Yogini applicability; it does not output Vimshottari or Char Dasha.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — establishes birth context for interpreting Yogini lords.\nAFTER: asterwise_get_dasha — optional Vimshottari comparison for the same native.\n\nSECTION: INPUT CONTRACT\nTree lives at data.periods.root[] — agents must not expect a top-level data.periods array. Calendar strings in periods use DD/MM/YYYY. BirthData follows the global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.periods.root[] — array of Mahadasha objects:\n  yogini (string — e.g. 'Pingala')\n  planet (string — ruling planet)\n  start_jd (float)\n  end_jd (float)\n  start_date (string — DD/MM/YYYY)\n  end_date (string — DD/MM/YYYY)\n  sub[] — Antardasha objects with the same fields (max two levels total)\ndata.birth_time_unknown (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Root key is data.periods.root, not data.periods.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — Vimshottari planet periods with data.periods[] and optional levels 1–5, not Yogini names.\nasterwise_get_ashtottari_dasha — 108-year system with data.periods.root[] but planet-based rows, not Yoginis.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_yogini_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Yogini Dasha."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/yogini", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Yogini Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_yogini_dasha", exc)

    @mcp.tool(
        name="asterwise_get_ashtottari_dasha",
        description="Computes the 108-year Ashtottari Dasha tree with configurable depth (levels 1–5) and returns periods under data.periods.root with DD/MM/YYYY dates.\n\nSECTION: WHAT THIS TOOL COVERS\nProvides the Ashtottari planetary sequence (eight grahas, Ketu excluded) with the same levels semantics as Vimshottari: deeper levels nest sub-periods in sub[]. Classical texts restrict use when Rahu is in Kendra/Trikona from Lagna lord (not in Lagna); this tool always returns a full timeline with no niyama_met flag — apply rules externally. It is not Vimshottari, Yogini, or Char Dasha.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — chart context before choosing between Ashtottari and Vimshottari.\nAFTER: asterwise_get_dasha — optional Vimshottari comparison.\n\nSECTION: INPUT CONTRACT\nlevels: same as asterwise_get_dasha (1–5), enforced locally before the API call. Periods use data.periods.root[], not data.periods[]. Dates in periods are DD/MM/YYYY.\n\nSECTION: OUTPUT CONTRACT\ndata.periods.root[] — Mahadasha objects:\n  planet (string)\n  start_jd (float)\n  end_jd (float)\n  start_date (string — DD/MM/YYYY)\n  end_date (string — DD/MM/YYYY)\n  sub[] — Antardasha objects, same shape, nested per levels\ndata.birth_time_unknown (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (timing scales with levels similarly to asterwise_get_dasha)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — levels < 1 or levels > 5 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  None — remaining validation is upstream.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — No classical applicability check in the response; full timeline is always returned.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — standard 120-year Vimshottari with data.periods[], not Ashtottari or data.periods.root[].\nasterwise_get_yogini_dasha — 36-year Yogini cycle with yogini names on each row.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_ashtottari_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        levels: int = 3,
    ) -> str:
        """Ashtottari Dasha."""
        try:
            if levels < 1 or levels > 5:
                invalid_params("levels must be between 1 and 5 inclusive.")
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "levels": levels}
            data = await get_client().post(
                "/v1/astro/ashtottari", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Ashtottari Dasha", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ashtottari_dasha", exc)

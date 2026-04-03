"""Vimshottari and alternative Dasha systems (timing)."""

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
        description="Calculate Vimshottari Dasha — the primary timing system of Parashari\nJyotish, a 120-year planetary cycle based on the Moon's nakshatra at\nbirth. Returns a hierarchical period tree.\n\nlevels parameter: 1 = Mahadasha only (fast, ~100ms); 2 = adds\nAntardasha (recommended, ~200ms); 3 = Pratyantar (~400ms); 4 = Sookshma\n(~800ms); 5 = Prana (very large response, ~1500ms). Maximum: 5.\nRequests with levels=6 or above are rejected with 422.\n\nOUTPUT CONTRACT (response_format=json):\ndata.periods[] — array of Mahadasha objects:\n  planet, start_jd, end_jd, start_date (DD/MM/YYYY), end_date\n  (DD/MM/YYYY), modern_summary (string or null), sub[] (array of\n  Antardasha objects with same shape, sub=null at lowest level)\ndata.interpretation.current_mahadasha — { planet, start_date,\n  end_date, duration_years, modern_summary, favorable_conditions[],\n  favorable_results[], unfavorable_conditions[], unfavorable_results[],\n  timing_note }\ndata.interpretation.current_antardasha — same shape plus\n  mahadasha_planet\ndata.birth_time_unknown (bool)\n\nDate format in periods is DD/MM/YYYY — not ISO. Parse accordingly.\n\nERROR CONTRACT: levels > 5 → 422 with message 'levels must be\nbetween 1 and 5 inclusive'. Other errors follow standard shape.\n\nDo not confuse with asterwise_get_char_dasha (Jaimini sign-based),\nasterwise_get_yogini_dasha (36-year Yogini cycle), or\nasterwise_get_ashtottari_dasha (108-year alternative).",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Dasha-transit correlation for today — returns the active Mahadasha,\nAntardasha, and Pratyantar lords alongside scores showing how current\ntransiting planets interact with each Dasha lord. Always computed for\ntoday's date — not configurable for past or future.\n\nOUTPUT CONTRACT (response_format=json):\ndata.target_date (YYYY-MM-DD, today)\ndata.active_dasha — { start_date, end_date, maha{ planet, start_date,\n  end_date }, antar{ planet, start_date, end_date }, pratyantar{\n  planet, start_date, end_date } }\ndata.transit_positions{} — keyed by planet: { rashi_index, rashi,\n  is_retrograde, house_from_moon, house_from_lagna }\ndata.correlations[] — scored transit-dasha interactions: dasha_level,\n  dasha_lord, transit_planet, aspect_type, score (int 1–3: 1=mild,\n  2=moderate, 3=high), natal_rashi, transit_rashi, is_retrograde,\n  significance\ndata.periods_of_significance[] — same shape as correlations[],\n  filtered to score ≥ 2\n\nTransit tool selection: use THIS for timing quality of the running\nDasha period. Use asterwise_get_gochar for raw transit house positions\nwithout Dasha context. Use asterwise_get_transits for ingress events\nover a date range. Use asterwise_check_sade_sati for Saturn-Moon\ntransit specifically.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Calculate Char Dasha — the Jaimini sign-based timing system where\nzodiac signs (not planets) serve as period lords. Each sign rules for\nyears determined by its lord's position. Particularly useful for\ndharma, relationship, and major life-event timing.\nSource: Jaimini Sutras.\n\nOUTPUT CONTRACT (response_format=json):\ndata.atmakaraka (planet name)\ndata.start_rashi, data.start_rashi_index\ndata.karakas{} — 8 Jaimini karakas mapped to planets\ndata.current_mahadasha (Sanskrit rashi name, e.g. 'Mithuna')\ndata.current_antardasha (Sanskrit rashi name)\ndata.periods[] — array of Mahadasha objects:\n  rashi, rashi_index, years (int), start_date (YYYY-MM-DD),\n  end_date (YYYY-MM-DD), antardashas[] (same shape minus antardashas)\n\nDate format is YYYY-MM-DD (ISO) — unlike Vimshottari which uses\nDD/MM/YYYY.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not use as a replacement for Vimshottari — use both together\nfor corroboration.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Calculate Yogini Dasha — an 8-Yogini, 36-year repeating cycle:\nMangala (Moon, 1yr), Pingala (Sun, 2yr), Dhanya (Jupiter, 3yr),\nBhramari (Mars, 4yr), Bhadrika (Mercury, 5yr), Ulka (Saturn, 6yr),\nSiddha (Venus, 7yr), Sankata (Rahu, 8yr). Particularly valued for\nnear-term timing. Source: Yogini Dasha tradition.\n\nOUTPUT CONTRACT (response_format=json):\ndata.periods.root[] — array of Mahadasha objects:\n  yogini (Yogini name, e.g. 'Pingala'), planet (ruling planet),\n  start_jd, end_jd, start_date (DD/MM/YYYY), end_date (DD/MM/YYYY),\n  sub[] — array of Antardasha objects with same fields (no further\n  sub nesting beyond two levels)\ndata.birth_time_unknown (bool)\n\nNote: the response root key is data.periods.root (not data.periods[]).\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nAlways check Vimshottari first. This is a secondary timing system.",
        annotations=STANDARD_ANNOTATIONS,
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
        description='Calculate Ashtottari Dasha — a 108-year alternative timing cycle\nusing 8 planets (Sun, Moon, Mars, Mercury, Saturn, Jupiter, Rahu,\nVenus — Ketu excluded) with different period lengths than Vimshottari.\nSource: BPHS Ashtottari chapters.\n\nClassical applicability: BPHS prescribes this system when Rahu is in\na Kendra or Trikona from the Lagna lord, but not in the Ascendant\nitself. This tool always returns a full timeline regardless of whether\nthe classical condition is met — there is no niyama_met flag and no\nrefusal. Apply classical applicability judgement externally.\n\nlevels parameter: works the same as in asterwise_get_dasha (1–5).\nRequests with levels > 5 are rejected with 422.\n\nOUTPUT CONTRACT (response_format=json):\ndata.periods.root[] — array of Mahadasha objects:\n  planet, start_jd, end_jd, start_date (DD/MM/YYYY),\n  end_date (DD/MM/YYYY), sub[] (Antardasha objects, same shape)\ndata.birth_time_unknown (bool)\n\nNote: response root key is data.periods.root (not data.periods[]).\n\nERROR CONTRACT: Same as asterwise_get_dasha.\n\nDo not replace Vimshottari with this — use together for\ncorroboration when the classical condition applies.',
        annotations=STANDARD_ANNOTATIONS,
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

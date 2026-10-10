"""Vimshottari and alternative Dasha systems (timing)."""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import Context, FastMCP
from pydantic import Field


import mcp.types as mcp_types

from client import get_client
from models import BirthData, ResponseFormat, TimedBirthData
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
)


def _slim_dasha(payload: dict[str, Any], *, keep_levels: int = 0) -> dict[str, Any]:
    """
    Drop per-period bulk from the tree: the generic per-planet essay
    (modern_summary, identical for every period of the same planet) and the
    Julian-day pair, which duplicates the calendar dates. The current-period
    interpretation block keeps its essays, so nothing interpretive is lost
    and markdown output never points at text it does not show. Cuts a
    three-level tree from ~1.3 MB to about 100 KB.
    """
    def walk(periods: Any, depth: int) -> Any:
        if not isinstance(periods, list):
            return periods
        out = []
        for p in periods:
            if not isinstance(p, dict):
                out.append(p); continue
            q = {k: v for k, v in p.items() if k not in ("start_jd", "end_jd")}
            if depth > keep_levels:
                q.pop("modern_summary", None)
            if "sub" in q:
                q["sub"] = walk(q["sub"], depth + 1)
            out.append(q)
        return out
    data = payload.get("data") if isinstance(payload.get("data"), dict) else None
    if data is None or not isinstance(data.get("periods"), list):
        return payload
    slim = dict(payload); slim["data"] = dict(data)
    slim["data"]["periods"] = walk(data["periods"], 1)
    return slim


def _dasha_tree_md(data: dict[str, Any]) -> str:
    # Upstream wraps the result in {success, message, data}; render the inner object.
    if isinstance(data.get("data"), dict) and "periods" in data["data"]:
        data = data["data"]
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
                children = block.get("antar") or block.get("children") or block.get("sub_periods") or block.get("sub")
                if isinstance(children, list):
                    for ch in children[:50]:
                        if isinstance(ch, dict):
                            lines.append(
                                f"  - {ch.get('planet', ch.get('lord', '—'))}: "
                                f"{ch.get('start', ch.get('start_date', ''))} → {ch.get('end', ch.get('end_date', ''))}"
                            )
        lines.append("")
    # Current-period interpretation is the part worth reading in full; the
    # per-period essays are generic per planet and are not repeated here.
    interp = data.get("interpretation")
    if isinstance(interp, dict) and interp:
        lines.append("### Current periods")
        lines.append("")
        lines.append(structured_markdown("Interpretation", interp))
        lines.append("")
    extras = {k: v for k, v in data.items() if k not in ("periods", "dasha", "vimshottari", "interpretation")}
    if extras:
        lines.append(structured_markdown("Details", extras))
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_dasha",
        title="Vimshottari Dasha",
        description=compact_description("asterwise_get_dasha", "Computes Vimshottari Dasha from birth data and returns hierarchical period trees plus current Maha/Antar interpretation blocks.\n\nSECTION: WHAT THIS TOOL COVERS\nComputes the classical Vimshottari timeline from the Moon's birth nakshatra: Mahadasha and nested sub-periods up to the depth set by levels, with Julian and calendar boundaries and optional modern summaries. It returns data.periods[] and data.interpretation for the active periods. It does not compute Char Dasha, Yogini Dasha, Ashtottari, or transit correlations; use the dedicated tools for those systems. The first Mahadasha row starts at birth and lasts the balance; its sub-periods are the remaining tail of the full Mahadasha, which began before birth, so the period running at birth is usually not the Mahadasha lord's own. That row also carries dasha_start_date (DD/MM/YYYY) and balance_years.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — establishes chart and Moon context before interpreting Dasha lords.\nAFTER: asterwise_get_dasha_transits — correlates active Dasha lords with transits for the same birth data.\n\nSECTION: INPUT CONTRACT\nlevels (int, default 2, max 5): tree depth — 1 = Mahadasha only; 2 adds Antardasha; 3 Pratyantar; 4 Sookshma; 5 Prana (much larger payload). Response dates in periods[] use DD/MM/YYYY, not ISO. BirthData fields follow the global contract (date YYYY-MM-DD, time HH:MM). Unknown birth time: omit time (a sunrise chart is cast and birth_time_provided=false); never pass time='00:00' for unknown, which is read as midnight.\n\nSECTION: OUTPUT CONTRACT\ndata.periods[] — array of Mahadasha objects:\n  planet (string)\n  start_date (string — DD/MM/YYYY, not ISO)\n  end_date (string — DD/MM/YYYY)\n  dasha_start_date (string — DD/MM/YYYY, first row only: when the full Mahadasha began, before birth)\n  balance_years (float — first row only: years of that Mahadasha left at birth)\n  sub[] — array of Antardasha objects with the same shape; sub=null at deepest level\n  (The per-period planet essays and Julian-day pairs from the REST API are omitted here to keep the tree small; the current-period essays are in data.interpretation.)\ndata.interpretation.current_mahadasha:\n  planet (string)\n  start_date (string)\n  end_date (string)\n  duration_years (float)\n  modern_summary (string or null)\n  favorable_conditions[] (string array)\n  favorable_results[] (string array)\n  unfavorable_conditions[] (string array)\n  unfavorable_results[] (string array)\n  timing_note (string)\ndata.interpretation.current_antardasha — same fields as current_mahadasha plus mahadasha_planet (string)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (~100ms at levels=1, ~1500ms at levels=5)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — levels < 1 or levels > 5 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — BirthData validation is upstream beyond Pydantic field constraints.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Period start_date/end_date strings are DD/MM/YYYY; do not parse as ISO.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_char_dasha — classical sign-based periods with ISO dates on periods[], not planet-based Vimshottari.\nasterwise_get_yogini_dasha — 36-year eight-Yogini cycle with data.periods.root[], not Vimshottari.\nasterwise_get_ashtottari_dasha — 108-year alternative tree with data.periods.root[] and same levels semantics as this tool."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        levels: int = 2
    ) -> str:
        """Vimshottari Dasha up to five levels (default 2: Mahadasha + Antardasha)."""
        async with tool_guard("asterwise_get_dasha"):
            if levels < 1 or levels > 5:
                invalid_params("levels must be between 1 and 5 inclusive.")
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "levels": levels}
            data = await get_client().post("/v1/astro/dasha", api_key, body, timeout=25.0)
            return format_tool_result(_slim_dasha(data), response_format, _dasha_tree_md)
    @mcp.tool(
        name="asterwise_get_dasha_transits",
        title="Dasha Transits",
        description=compact_description("asterwise_get_dasha_transits", "Combines active Vimshottari lords with transits on one date and returns scored correlations plus transit longitudes and houses from Moon and Lagna.\n\nSECTION: WHAT THIS TOOL COVERS\nBuilds a snapshot for one date (today unless target_date is given): active Mahadasha, Antardasha, and Pratyantar; transiting planet positions; pairwise dasha–transit correlations with scores; and a filtered list of stronger correlations. Aspects are cast by the transiting planet (BPHS Ch.26). It does not return full Dasha trees (use asterwise_get_dasha), ingress calendars (asterwise_get_transits), or standalone Gochar without Dasha context (asterwise_get_gochar).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — same birth data should be understood before interpreting houses and lords.\nAFTER: asterwise_get_gochar — optional broader transit snapshot without dasha scoring.\n\nSECTION: INPUT CONTRACT\ntarget_date (string, optional — YYYY-MM-DD): date to analyse; defaults to today. target_time (string, optional — HH:MM, default 12:00) and target_timezone (IANA, optional — default Asia/Kolkata) set the instant on that date. All parameters are otherwise defined in the tool schema. BirthData follows the global contract. Birth time is required: this tool has no sunrise fallback. If the user doesn't know it, say so rather than guessing; never pass time='00:00' for unknown.\n\nSECTION: OUTPUT CONTRACT\ndata.target_date (string — YYYY-MM-DD, the date analysed)\ndata.active_dasha:\n  start_date (string)\n  end_date (string)\n  maha — { planet (string), start_date (string), end_date (string) }\n  antar — { planet (string), start_date (string), end_date (string) }\n  pratyantar — { planet (string), start_date (string), end_date (string) }\ndata.transit_positions{} — keyed by planet name:\n  rashi_index (int)\n  rashi (string)\n  is_retrograde (bool)\n  house_from_moon (int)\n  house_from_lagna (int)\ndata.correlations[] — each object:\n  dasha_level (string)\n  dasha_lord (string)\n  transit_planet (string)\n  aspect_type (string — conjunction | opposition | trine | square | special)\n  aspect_house (int — natal lord's sign counted from the transiting planet)\n  drishti (string or null — e.g. '3rd'; null for conjunction)\n  score (int — 1=mild, 2=moderate, 3=high)\n  natal_rashi (string)\n  transit_rashi (string)\n  is_retrograde (bool)\n  significance (string)\ndata.periods_of_significance[] — same shape as correlations[] filtered to score ≥ 2\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — target_date not YYYY-MM-DD or target_time not HH:MM (schema pattern) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — Invalid target_date/target_time combination → upstream validation error, surfaces as MCP INTERNAL_ERROR.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Without target_date the snapshot is for today; pass target_date for past or future days (e.g. tomorrow, a week view).\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — full nine-planet Gochar with AVK and vedha fields, without dasha–transit correlation scores.\nasterwise_get_transits — ingress and station lists over a chosen range, not today's dasha snapshot.\nasterwise_get_dasha — full Vimshottari tree without transit overlay."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_dasha_transits(
        ctx: Context,
        birth: TimedBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        target_time: Optional[str] = Field(
            default=None,
            pattern=r"^\d{2}:\d{2}$",
            description="HH:MM on target_date. Defaults to 12:00.",
        ),
        target_timezone: Optional[str] = Field(
            default=None,
            description="IANA zone for target_date and target_time. Defaults to Asia/Kolkata.",
        ),
    ) -> str:
        """Dasha-period transits."""
        async with tool_guard("asterwise_get_dasha_transits"):
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            # Each is optional upstream: no date means today.
            for key, value in (
                ("target_date", target_date),
                ("target_time", target_time),
                ("target_timezone", target_timezone),
            ):
                if value is not None:
                    body[key] = value
            data = await get_client().post(
                "/v1/astro/dasha-transits", api_key, body,
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dasha transits", d),
            )
    @mcp.tool(
        name="asterwise_get_char_dasha",
        title="Char Dasha",
        description=compact_description("asterwise_get_char_dasha", "Computes Char Dasha from birth data and returns sign lords as period rulers with ISO-dated Maha and Antar sequences plus karaka mappings.\n\nSECTION: WHAT THIS TOOL COVERS\nUses the classical system where rashis (not grahas) rule time periods, including Atmakaraka, eight karakas, current Maha/Antar labels in Sanskrit signs, and a period array with nested antardashas. Method: K.N. Rao, as in his own dated case notes: sequence from the Lagna, forward if the 9th sign is savya, else backward; years = signs to the lord minus one, 12 when the lord is in the sign, with no year added or taken off for an exalted or debilitated lord (JHora's K.N. Rao option adds/subtracts one). Scorpio and Aquarius count to the co-lord outside the sign, or with both outside to the one with more planets, then the one further advanced in its sign. It does not return Vimshottari (asterwise_get_dasha), Yogini, or Ashtottari timelines.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — contextualises the chart before interpreting sign-based lords.\nAFTER: asterwise_get_dasha — optional Vimshottari cross-check for the same native.\n\nSECTION: INPUT CONTRACT\ncycles (optional int 1–3, default 1): every further cycle repeats the first cycle's signs, order and years (K.N. Rao). Period start_date and end_date in data.periods[] are YYYY-MM-DD (ISO), unlike asterwise_get_dasha which uses DD/MM/YYYY in its tree. All other parameters follow the BirthData global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.atmakaraka (string — planet name)\ndata.start_rashi (string — Sanskrit rashi name)\ndata.start_rashi_index (int)\ndata.karakas{} — object mapping classical karaka keys to planet names\ndata.current_mahadasha (string — Sanskrit rashi name, e.g. 'Mithuna')\ndata.current_antardasha (string — Sanskrit rashi name)\ndata.periods[] — Mahadasha objects:\n  rashi (string)\n  rashi_index (int)\n  years (int — K.N. Rao: signs to the lord minus one, 12 when the lord is in the sign, no exaltation/debilitation adjustment; 1–12; every cycle repeats the first cycle's years)\n  start_date (string — YYYY-MM-DD ISO)\n  end_date (string — YYYY-MM-DD ISO)\n  antardashas[] — same shape as one level (no further nesting); K.N. Rao order: forward or backward by the 9th sign from the mahadasha sign, starting with the next sign, the mahadasha sign's own antardasha last; each lasts as many months as the mahadasha has years\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — cycles outside 1..3 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Period years are 1–12; JHora's K.N. Rao option (±1 for exalted/debilitated lords) can differ by a year.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — Vimshottari planet lords with DD/MM/YYYY in periods[], not sign-based Char Dasha.\nasterwise_get_yogini_dasha — eight Yoginis and data.periods.root[], not classical signs."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_char_dasha(
        ctx: Context,
        birth: TimedBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        cycles: int | None = None,
    ) -> str:
        """Char Dasha."""
        async with tool_guard("asterwise_get_char_dasha"):
            if cycles is not None and not 1 <= cycles <= 3:
                invalid_params("cycles must be 1, 2 or 3, or omitted for one cycle.")
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            if cycles is not None:
                body["cycles"] = cycles
            data = await get_client().post("/v1/astro/char-dasha", api_key, body,
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Char Dasha", d),
            )
    @mcp.tool(
        name="asterwise_get_yogini_dasha",
        title="Yogini Dasha",
        description=compact_description("asterwise_get_yogini_dasha", "Computes the eight-Yogini, 36-year Yogini Dasha cycle with two-level period trees and DD/MM/YYYY boundaries from birth data.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns Mahadasha rows under data.periods.root[] (not data.periods[]), each with Yogini name, ruling planet, Julian and calendar dates, and sub-periods for Antar only (two levels total). The eight Yoginis map to year-lengths 1–8 summing to 36 years per cycle; the timeline runs from birth through three full cycles (past age 108). Antardashas are proportional (MD years × AD years / 36). The first row carries dasha_start_date and balance_years. It does not validate or refuse charts outside classical Yogini applicability; it does not output Vimshottari or Char Dasha.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — establishes birth context for interpreting Yogini lords.\nAFTER: asterwise_get_dasha — optional Vimshottari comparison for the same native.\n\nSECTION: INPUT CONTRACT\nTree lives at data.periods.root[] — agents must not expect a top-level data.periods array. Calendar strings in periods use DD/MM/YYYY. BirthData follows the global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.periods.root[] — array of Mahadasha objects:\n  yogini (string — e.g. 'Pingala')\n  planet (string — ruling planet)\n  start_jd (float)\n  end_jd (float)\n  start_date (string — DD/MM/YYYY)\n  end_date (string — DD/MM/YYYY)\n  dasha_start_date (string — DD/MM/YYYY, first row only: when that Mahadasha began, before birth)\n  balance_years (float — first row only: years of that Mahadasha left at birth)\n  sub[] — Antardasha objects with the same fields (max two levels total)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Root key is data.periods.root, not data.periods.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — Vimshottari planet periods with data.periods[] and optional levels 1–5, not Yogini names.\nasterwise_get_ashtottari_dasha — 108-year system with data.periods.root[] but planet-based rows, not Yoginis."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_yogini_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Yogini Dasha."""
        async with tool_guard("asterwise_get_yogini_dasha"):
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/yogini", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Yogini Dasha", d),
            )
    @mcp.tool(
        name="asterwise_get_ashtottari_dasha",
        title="Ashtottari Dasha",
        description=compact_description("asterwise_get_ashtottari_dasha", "Computes the Ashtottari Dasha tree (108-year cycle) with configurable depth, levels 1–5. The timeline continues into the next cycle until it reaches at least age 120 (usually 9–11 mahadashas); periods are under data.periods.root with DD/MM/YYYY dates.\n\nSECTION: WHAT THIS TOOL COVERS\nProvides the Ashtottari planetary sequence (eight grahas, Ketu excluded) with the same levels semantics as Vimshottari: deeper levels nest sub-periods in sub[]. Applies only when Rahu is in a Kendra/Trikona from the Lagna lord's sign and not in the Lagna (BPHS); otherwise the response is {applicable: false, reason} with no periods. Starting lord and balance use the BPHS nakshatra groups from Ardra with the balance spread over the whole group (JHora). It is not Vimshottari, Yogini, or Char Dasha.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — chart context before choosing between Ashtottari and Vimshottari.\nAFTER: asterwise_get_dasha — optional Vimshottari comparison.\n\nSECTION: INPUT CONTRACT\nlevels: same as asterwise_get_dasha (1–5, default 2), enforced locally before the API call. Periods use data.periods.root[], not data.periods[]. Dates in periods are DD/MM/YYYY.\n\nSECTION: OUTPUT CONTRACT\ndata.periods.root[] — Mahadasha objects:\n  planet (string)\n  start_jd (float)\n  end_jd (float)\n  start_date (string — DD/MM/YYYY)\n  end_date (string — DD/MM/YYYY)\n  dasha_start_date (string — DD/MM/YYYY, first row only: when that Mahadasha began, before birth)\n  balance_years (float — first row only: years of that Mahadasha left at birth)\n  sub[] — Antardasha objects, same shape, nested per levels\ndata.birth_time_provided (bool)\nWhen Ashtottari does not apply, data is instead { applicable (bool — false), reason (string), birth_time_provided (bool) } with no periods.\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (timing scales with levels similarly to asterwise_get_dasha)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — levels < 1 or levels > 5 → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  None — remaining validation is upstream.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Non-applicable charts return applicable=false and a reason instead of periods.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — standard 120-year Vimshottari with data.periods[], not Ashtottari or data.periods.root[].\nasterwise_get_yogini_dasha — 36-year Yogini cycle with yogini names on each row."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_ashtottari_dasha(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        levels: int = 2,
    ) -> str:
        """Ashtottari Dasha."""
        async with tool_guard("asterwise_get_ashtottari_dasha"):
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
"""Natal chart and extended chart tools (Vedic chart foundations)."""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import Context, FastMCP
from pydantic import Field


import mcp.types as mcp_types

from client import get_client, safe_segment
from models import (
    BirthData,
    DivisionalChartType,
    PrashnaInput,
    ResponseFormat,
    TimedBirthData,
    prashna_dict,
)
from tools import panchanga_texts as texts
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
)


def _lk_reject_tropical(birth: BirthData) -> None:
    if birth.ayanamsa.value == "tropical":
        invalid_params(
            "Lal Kitab needs a sidereal chart; tropical is not supported. Use lahiri, raman or kp."
        )


def _lk_payload(data: dict[str, Any]) -> dict[str, Any]:
    inner = data.get("data")
    return inner if isinstance(inner, dict) else data


def _lk_time_note(d: dict[str, Any]) -> list[str]:
    if d.get("birth_time_provided") is False:
        return ["> No birth time given: a sunrise chart was used, so the lagna and every house are approximate.", ""]
    return []


def _lk_chart_md(data: dict[str, Any]) -> str:
    d = _lk_payload(data)
    asc = d.get("ascendant") or {}
    lines = ["## Lal Kitab chart", ""]
    lines += _lk_time_note(d)
    lines.append(f"Lagna: {asc.get('rashi', '—')} ({asc.get('longitude', '—')}°), read as house 1. Ayanamsa: {d.get('ayanamsa', 'lahiri')}.")
    lines += ["", "| Planet | House | Sign | Pakka ghar | Uchcha | Neecha | Effect | Malefic because |",
              "|---|---|---|---|---|---|---|---|"]
    for name, p in (d.get("planets") or {}).items():
        why = "; ".join(p.get("malefic_reasons") or []) or "—"
        lines.append(
            f"| {name} | {p.get('lk_house')} | {p.get('rashi')} | {'yes' if p.get('pucca_ghar') else 'no'} "
            f"| {'yes' if p.get('uchcha') else 'no'} | {'yes' if p.get('neecha') else 'no'} | {p.get('effect')} | {why} |"
        )
    rin = d.get("rin_analysis") or {}
    lines += ["", "### Debts (rin)", ""]
    found = rin.get("rin_remedies") or []
    if not found:
        lines.append("None indicated.")
    for r in found:
        where = ", ".join(f"{f['planet']} in {f['house']}" for f in r.get("found") or [])
        lines.append(f"- **{r.get('name')}** ({where}): {r.get('remedy')} — {r.get('source')}")
    if rin.get("not_evaluated"):
        lines += ["", f"_{rin['not_evaluated']}_"]
    return "\n".join(lines)


def _lk_remedies_md(data: dict[str, Any]) -> str:
    d = _lk_payload(data)
    lines = ["## Lal Kitab remedies", ""]
    lines += _lk_time_note(d)
    entries = d.get("remedies") or []
    if not entries:
        lines.append("No planet needs a remedy.")
    for e in entries:
        why = "; ".join(e.get("malefic_reasons") or [])
        lines += ["", f"### {e.get('planet')} in house {e.get('lk_house')}", f"Why: {why}", ""]
        items = e.get("remedies") or []
        if not items:
            lines.append("- The book gives no remedy for this placement.")
        for it in items:
            cond = f" (when: {it['condition']})" if it.get("condition") else ""
            note = f" [{it['note']}]" if it.get("note") else ""
            lines.append(f"- {it.get('type')}: {it.get('action')}{cond} — p.{it.get('page')}{note}")
    nr = d.get("not_remediable") or []
    if nr:
        lines += ["", "### Malefic but fixed (Lal Kitab says remedies cannot change these)", ""]
        for e in nr:
            lines.append(f"- {e.get('planet')} in house {e.get('lk_house')}: {'; '.join(e.get('reasons') or [])}")
    rins = d.get("rin_remedies") or []
    if rins:
        lines += ["", "### Debt (rin) remedies", ""]
        for r in rins:
            lines.append(f"- **{r.get('name')}**: {r.get('remedy')} — {r.get('source')}")
    if d.get("sources"):
        lines += ["", "Sources: " + "; ".join(d["sources"])]
    return "\n".join(lines)


def _natal_table_md(data: dict[str, Any]) -> str:
    planets = data.get("planets") or data.get("positions")
    if planets is None and isinstance(data.get("chart"), dict):
        planets = data["chart"].get("planets")
    if isinstance(planets, list) and planets and isinstance(planets[0], dict):
        rows = []
        for p in planets:
            name = p.get("planet") or p.get("name") or p.get("graha") or "—"
            sign = p.get("sign") or p.get("rashi") or "—"
            house = p.get("house") or p.get("bhava") or "—"
            nak = p.get("nakshatra") or p.get("nakshatra_name") or "—"
            flags = []
            for k in (
                "combust",
                "retrograde",
                "vargottama",
                "debilitated",
                "exalted",
            ):
                if p.get(k):
                    flags.append(k.replace("_", " "))
            flag_s = ", ".join(flags) if flags else "—"
            rows.append(f"| {name} | {sign} | {house} | {nak} | {flag_s} |")
        if rows:
            return (
                "## Natal chart — planet table\n\n"
                "| Planet | Sign | House | Nakshatra | Flags |\n"
                "|--------|------|-------|-----------|-------|\n"
                + "\n".join(rows)
                + "\n\n### Full response\n\n"
                + structured_markdown("Details", data)
            )
    return structured_markdown("Natal chart", data)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_natal_chart",
        title="Natal Chart",
        description=compact_description("asterwise_get_natal_chart", "Computes the full sidereal natal chart from BirthData and returns planet rows, houses, aspects, arudhas, upapada, bhava cusps, and avakhada metadata.\n\nSECTION: WHAT THIS TOOL COVERS\nVedic natal endpoint: nine grahas with signs, degrees, nakshatras, combustion, retrograde, Bhava Chalit and rashi houses, twelve house cusps, graha and rashi drishti, arudha padas A1–A12, upapada lagna block, bhava madhya/sandhi arrays, ayanamsa metadata, and avakhada attributes. When include_interpretation=true, ascendant_sign_interpretation, moon_sign_interpretation, moon_nakshatra_interpretation, and interpretation are populated from interpretation JSON; otherwise they are null. It does not return PDFs, yogas list (asterwise_get_yogas), or dasha trees (asterwise_get_dasha).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: RECOMMENDED — asterwise_get_yogas — layer classical combinations after the base chart exists.\n\nSECTION: INPUT CONTRACT\nBirthData enforces date YYYY-MM-DD, time HH:MM, lat -90..90, lon -180..180, ayanamsa enum locally (Pydantic). Unknown birth time: omit time (a sunrise chart is cast and birth_time_provided=false); never pass time='00:00' for unknown, which is read as midnight. Lagna-sensitive results (houses, lagna, arudhas) are then approximate.\n\nSECTION: OUTPUT CONTRACT\ndata.planets[] — nine objects:\n  planet (string)\n  sign (string)\n  sign_num (int — 0–11)\n  degree (float)\n  nakshatra (string)\n  nakshatra_pada (int — 1–4)\n  is_retrograde (bool)\n  is_combust (bool)\n  is_deep_combust (bool)\n  house (int — Bhava Chalit)\n  rasi_house (int)\n  bhava_chalit_house (int)\ndata.houses[] — twelve objects:\n  house (int)\n  sign (string)\n  sign_num (int)\n  degree (float)\ndata.ascendant (float)\ndata.ascendant_sign (string — Sanskrit name)\ndata.moon_sign (string)\ndata.moon_nakshatra (string)\ndata.ayanamsa_value (float)\ndata.ayanamsa_used (string)\ndata.avakahada:\n  nakshatra, nakshatra_lord, charan (int), rashi, rashi_lord, varna, vashya, yoni, gana, nadi, paya, ascendant, ascendant_lord, sun_sign, sun_sign_lord (strings/ints per upstream)\ndata.graha_drishti — object keyed by planet name; each value object keyed by house strings '1'–'12' with aspect strength int (25, 50, 75, or 100)\ndata.rashi_drishti[] — active sign-to-sign aspect pairs:\n  { from_sign (string), from_sign_num (int 0-11), to_sign (string), to_sign_num (int 0-11) }\ndata.arudha_padas — keys A1–A12 each { sign_index (int), sign_name (string) }\ndata.upapada_lagna:\n  sign_index (int)\n  sign_name (string)\n  upapada_lord (string)\n  second_from_upapada_sign_index (int)\n  second_from_upapada_sign_name (string)\n  planets_in_second_from_upapada[] (string array of planet names)\n  has_benefic_in_second_from_upapada (bool)\n  has_malefic_in_second_from_upapada (bool)\ndata.bhava_madhya[] — twelve objects:\n  { house (int 1-12), sign (string), sign_num (int 0-11), degree (float) }\ndata.bhava_sandhi[] — twelve objects:\n  { house (int 1-12), sign (string), sign_num (int 0-11), degree (float) }\ndata.birth_time_provided (bool — always false; no detection)\ndata.fallback_method (null)\nascendant_sign_interpretation (dict or null — sign interpretation from signs/ascendant.json when include_interpretation=true)\n  moon_sign_interpretation (dict or null — Moon sign interpretation from signs/moon_sign.json when include_interpretation=true)\n  moon_nakshatra_interpretation (dict or null — nakshatra interpretation from nakshatras/ files when include_interpretation=true)\n  interpretation (list or null — planet-in-house interpretation list when include_interpretation=true)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — BirthData Pydantic violations (date/time/lat/lon/ayanamsa) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — calendar years outside supported upstream window surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Unknown birth time: omit time (birth_time_provided=false); '00:00' is read as midnight, not as unknown.\n  — Interpretation fields are null unless include_interpretation=true on the request.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_divisional_chart — sixteen vargas only, not the primary radix bundle returned here."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_natal_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        include_interpretation: bool = False,
    ) -> str:
        """Compute full natal chart from classical calculations."""
        async with tool_guard("asterwise_get_natal_chart"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "include_interpretation": include_interpretation}
            data = await get_client().post(
                "/v1/astro/natal", api_key, body,
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                _natal_table_md,
            )
    @mcp.tool(
        name="asterwise_get_divisional_chart",
        title="Divisional Chart",
        description=compact_description("asterwise_get_divisional_chart", texts.DIVISIONAL_CHART),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_divisional_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        chart_type: Optional[DivisionalChartType] = None,
    ) -> str:
        """Compute divisional (varga) chart."""
        async with tool_guard("asterwise_get_divisional_chart"):
            api_key = await require_api_key(ctx)
            body = {
                **birth.to_api_dict(),
                **({"chart_type": chart_type.value} if chart_type else {}),
            }
            data = await get_client().post("/v1/astro/divisional", api_key, body, timeout=20.0)
            title = (
                f"Divisional chart {chart_type.value}"
                if chart_type
                else "Divisional charts (all vargas)"
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(title, d),
            )
    @mcp.tool(
        name="asterwise_get_chart_strength",
        title="Chart Strength",
        description=compact_description("asterwise_get_chart_strength", "Aggregates Shadbala, Bhavbala, Vimshopaka (with per-varga contributions), embedded sixteen vargas, Ashtakavarga, karaka maps, and graha yuddha pairs from BirthData.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns chart strength computations: seven-planet (Sun–Saturn) Shadbala breakdowns with sthana/kala detail objects, twelve-house Bhavbala totals, Vimshopaka scores with threshold bands (BPHS scoring: own sign 20, otherwise 18/15/10/7/5 by relationship with the sign lord) and per-D1..D60 fractions, full divisional chart mirror of asterwise_get_divisional_chart, Ashtakavarga mirror of asterwise_get_ashtakavarga, karaka_to_planet / planet_to_karaka, and graha_yuddha.war_pairs. It does not label named yogas (asterwise_get_yogas) or doshas (asterwise_get_doshas).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — contextualises houses before reading bala tables.\nAFTER: asterwise_get_yogas — optional configuration pass after strength review.\n\nSECTION: INPUT CONTRACT\nBirthData only; no extra toggles.\n\nSECTION: OUTPUT CONTRACT\ndata.shadbala — keyed by Sun..Saturn (excludes Rahu/Ketu):\n  planet (string)\n  sthana_bala, dig_bala, dig_bala_virupas, dig_bala_rupas, kala_bala, cheshta_bala, naisargika_bala, drik_bala, yuddhabala_adjustment, total (float), ratio (float), required_minimum (float), is_purna_bala (bool)\n  sthana_bala_details — { uchcha, saptavargaja, ojhayugma, kendradi, drekkana, total }\n  kala_bala_details — { nathonnatha, paksha, tribhaga, abda, masa, vara, hora, ayana, total }. Sun and Moon cheshta_bala is 0: their BPHS Cheshta is counted in Kala Bala (Sun's ayana and Moon's paksha doubled, 0–120), as in B.V. Raman and JHora. ayana uses the kranti of the ecliptic longitude (0–60). Paksha uses the chart's natures: a waning Moon is malefic (strongest near Amavasya) and Mercury follows his companions, as in JHora.\ndata.bhavbala — keys '1'..'12':\n  bhavadhipati_bala, bhava_dig_bala, bhava_drik_bala, total (float)\ndata.vimshopaka_bala — keyed by planet including Rahu/Ketu:\n  vimshopaka_score (float, max 20)\n  threshold (string — 'zero_capacity', 'moderate', 'good', or 'extremely_auspicious')\n  per_varga — keyed by D1..D60: { contribution (float), fraction (float) }\ndata.divisional_charts — same nested schema as asterwise_get_divisional_chart\ndata.ashtakavarga — same schema as asterwise_get_ashtakavarga\ndata.karakas — { karaka_to_planet{}, planet_to_karaka{} }\ndata.graha_yuddha — { war_pairs[] }\nThreshold guide: 15+ extremely_auspicious, 10–15 good, 5–10 moderate (BPHS minimum is 5.0, so zero_capacity — below 5 — is kept for compatibility but never occurs).\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (~800ms)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData only; Pydantic handles field bounds.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Large payload due to embedded vargas and Ashtakavarga duplicates.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_yogas — boolean yoga catalogue, not numeric bala.\nasterwise_get_ashtakavarga — standalone AVK when strength bundle is not needed."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_chart_strength(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Shadbala and Bhavbala."""
        async with tool_guard("asterwise_get_chart_strength"):
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/strength", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Chart strength (Shadbala / Bhavbala)", d),
            )
    @mcp.tool(
        name="asterwise_get_special_ascendants",
        title="Special Ascendants",
        description=compact_description("asterwise_get_special_ascendants", "Calls atmakaraka and ishta-devata endpoints sequentially and merges their payloads into top-level atmakaraka and ishta_devata objects for one BirthData.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns the karaka layer: eight-karaka mapping, soul significator graha, navamsa-based ishta devata inference, twelfth-house occupants, and D9 positions map. It is not general prediction, medical timing, or matchmaking scoring. Two planets tied by degree use classical highest-longitude resolution without raising an error.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — understand chart basics before devotional pointers.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nWrapper returns { atmakaraka: <upstream dict>, ishta_devata: <upstream dict> } — not a flat data.* root; consumers must read nested .data fields inside each branch per upstream shape.\n\nSECTION: OUTPUT CONTRACT\nTop-level merge:\n  atmakaraka — upstream POST /v1/astro/atmakaraka body; use atmakaraka.data:\n    karaka_to_planet{} (eight karakas to planet names)\n    planet_to_karaka{}\n    atmakaraka (string)\n    atmakaraka_sign (string)\n    atmakaraka_nakshatra (string)\n    details{} — per karaka: planet, rashi, nakshatra, longitude\n  ishta_devata — upstream POST /v1/astro/ishta-devta body; use ishta_devata.data:\n    atmakaraka (string)\n    karakamsha_lagna (string)\n    karakamsha_lagna_index (int)\n    jivanmuktamsa_planet (string)\n    navamsa_lagna (string)\n    navamsa_lagna_index (int)\n    twelfth_house_sign (string)\n    twelfth_house_index (int)\n    planets_in_12th[] (string array)\n    ishta_devta_planet (string)\n    deity (string)\n    description (string)\n    method (string)\n    d9_positions{} — per planet: { sign (string), sign_num (int) }\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData validated via Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout on either sequential call → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Identical-degree planets: classical tie-break applies; no error.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — general chart; does not compute ishta devata workflow.\nasterwise_get_char_dasha — timing system using karakas, not deity discovery."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_special_ascendants(
        ctx: Context,
        birth: TimedBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Atmakaraka and Ishta Devata (two API calls)."""
        async with tool_guard("asterwise_get_special_ascendants"):
            api_key = await require_api_key(ctx)
            bd = birth.to_api_dict()
            atm = await get_client().post("/v1/astro/atmakaraka", api_key, bd, timeout=20.0)
            ishta = await get_client().post("/v1/astro/ishta-devta", api_key, bd, timeout=20.0)
            merged = {"atmakaraka": atm, "ishta_devata": ishta}

            def _md(d: dict[str, Any]) -> str:
                # Render from ``d`` (the scrubbed payload), not the raw upstream
                # responses, so markdown output drops internal fields like the
                # JSON path does.
                parts = [
                    "## Atmakaraka",
                    structured_markdown("Atmakaraka", d.get("atmakaraka", {})),
                    "",
                    "## Ishta Devata",
                    structured_markdown("Ishta Devata", d.get("ishta_devata", {})),
                ]
                return "\n".join(parts)

            return format_tool_result(merged, response_format, _md)
    @mcp.tool(
        name="asterwise_get_nakshatra_details",
        title="Nakshatra Details",
        description=compact_description("asterwise_get_nakshatra_details", "Looks up static metadata for one of twenty-seven nakshatras by exact name and returns interpretive, professional, activity, and body-map reference data.\n\nSECTION: WHAT THIS TOOL COVERS\nVedanga/classical reference only — no chart computation. Covers deity, ruler, symbol, gana, nature, classical vs modern prose, profession vectors, life themes, keywords, strengths/challenges, favourable vs unfavourable activities, and body_map. Names are case-sensitive exact matches (Ashwini … Revati list). It does not compute birth nakshatra from BirthData (use asterwise_get_natal_chart).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nnakshatra_name is forwarded raw — no local fuzzy matching or normalisation.\n\nSECTION: OUTPUT CONTRACT\ndata.name (string)\ndata.index (int — 0–26)\ndata.interpretation:\n  source (string)\n  nakshatra_number (int)\n  name (string)\n  sanskrit (string)\n  span (string)\n  symbol (string)\n  deity (string)\n  ruling_planet (string)\n  sign (string)\n  sign_lord (string)\n  gana (string)\n  nature (string)\n  body_part (string)\n  classical_qualities[] (string array)\n  appearance — { classical (string), modern (string) }\n  nature_description — { classical (string), modern (string) }\n  profession — { primary[] (string array), secondary[] (string array), note (string), modern (string) }\n  life_themes — { core, karmic_path, challenge, gift, modern (strings) }\n  keywords[] (string array)\n  strengths[] (string array)\n  challenges[] (string array)\n  padas[] — { pada (int), span (string), navamsa_sign (string), navamsa_lord (string), vargottama (bool), special_note (string — names Gandanta, Vargottama and Pushkara Navamsa; 24 Pushkara padas per the standard rule) }\ndata.activities:\n  favorable_activities[] (string array)\n  unfavorable_activities[] (string array)\ndata.body_map:\n  parts[] (string array)\n  sensitivity (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — name passes straight through.\n\nINVALID_PARAMS (upstream):\n  — None — unknown names surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Exact spelling required — no fuzzy recovery.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — computes birth nakshatra from time/place, not encyclopaedic copy.\nasterwise_get_dasha — uses Moon nakshatra for timing, not this lookup table."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_nakshatra_details(
        ctx: Context,
        nakshatra_name: str,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Nakshatra reference details."""
        async with tool_guard("asterwise_get_nakshatra_details"):
            api_key = await require_api_key(ctx)
            path = f"/v1/astro/nakshatra/{safe_segment(nakshatra_name)}"
            data = await get_client().get(path, api_key, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Nakshatra: {nakshatra_name}", d),
            )
    @mcp.tool(
        name="asterwise_check_sade_sati",
        title="Sade Sati",
        description=compact_description("asterwise_check_sade_sati", "Evaluates Saturn's seven-and-a-half-year Moon-sign cycle phases against natal data for the current day and returns intensity, upcoming cycles, and historical rows.\n\nSECTION: WHAT THIS TOOL COVERS\nSade Sati mechanics: natal Moon sign in English, three reference signs (rising/peak/setting), active flag, current phase label, intensity score/label, next occurrence metadata, all_periods[] timeline with nested phase objects, mitigation booleans. \"Today\" is implicit — no date parameter. active and phase come from Saturn's sign on the check date; next_sade_sati may be a re-entry after a retrograde gap (phase can be setting). Signs are English, not Sanskrit. It is not general Gochar (asterwise_get_gochar) or dasha overlay (asterwise_get_dasha_transits).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — confirm Moon sign context.\nAFTER: asterwise_get_gochar — broader transit canvas if needed.\n\nSECTION: INPUT CONTRACT\nNo explicit query date — API pins to current day. BirthData global contract applies.\n\nSECTION: OUTPUT CONTRACT\ndata.natal_moon_sign (string — English, e.g. 'Libra')\ndata.natal_moon_sign_index (int — 0–11)\ndata.sade_sati_signs:\n  rising (string)\n  peak (string)\n  setting (string)\ndata.is_currently_active (bool)\ndata.current_phase (string — 'rising', 'peak', 'setting', or null)\ndata.current_phase_description (string or null)\ndata.intensity_score (int — 0–100 scale: rising 40–80, peak 70–90, setting 80–40; 0 when inactive)\ndata.intensity_label (string — 'low', 'moderate', or 'high')\ndata.next_sade_sati:\n  starts (string — YYYY-MM-DD)\n  phase (string)\n  years_away (float)\ndata.all_periods[] — each:\n  sade_sati_number (int)\n  overall_start (string — YYYY-MM-DD)\n  overall_end (string — YYYY-MM-DD)\n  duration_years (float)\n  is_interrupted (bool — Saturn stepped out of the three signs for a while; Sade Sati is not active during that gap)\n  phases:\n    rising — { name, description, start, end, saturn_sign, intensity, segments[] { start, end } (every stay of Saturn in the sign), is_interrupted (bool) }\n    peak — same shape\n    setting — same shape\ndata.small_panoti[] — Saturn in the 4th or 8th sign from the Moon: { panoti_number, sign_index, sign, position_from_moon, start, end, is_currently_active, duration_years, segments[], is_interrupted }\ndata.is_small_panoti_active (bool)\ndata.current_small_panoti_position (int — 4 or 8 when active)\ndata.mitigated_by_own_sign (bool)\ndata.mitigated_by_exaltation (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — English sign names throughout — do not expect Sanskrit.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — nine-planet daily scan including sade_sati_active flag but less Sade Sati detail than this tool.\nasterwise_get_transits — ingress/station feed, not Moon-focused Saturn phase model."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_check_sade_sati(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Sade Sati check."""
        async with tool_guard("asterwise_check_sade_sati"):
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/sade-sati", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Sade Sati", d),
            )
    @mcp.tool(
        name="asterwise_get_prashna_chart",
        title="Prashna Chart",
        description=compact_description("asterwise_get_prashna_chart", "Casts a Prashna chart for the query instant using supplied date, time, place, and a single-topic keyword, then returns houses, Moon diagnostics, verdict, and cusps.\n\nSECTION: WHAT THIS TOOL COVERS\nHorary workflow: maps one of the approved keywords to a primary house (the house and its lord are whole sign from the Prashna lagna; data.house_cusps lists the quadrant cusps and the lords of their signs, which can differ), evaluates Moon (phase, VOC, affliction), applies Tajika Ithasala/Musaripha between the Lagna lord and the quesited house lord (sign aspects 1/3/4/5/7/9/10/11, faster planet by mean motion, mean-Deeptamsa orb; both false when one planet rules both houses, e.g. 'self'), aggregates graha dignities/houses from Prashna Lagna, and emits verdict/confidence/score. Not natal life analysis (asterwise_get_natal_chart) and not KP cusps from birth (asterwise_get_kp_chart).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone for horary.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nquestion must be exactly one of: self, wealth, siblings, property, children, health, marriage, death, travel, career, gains, loss. Full sentences are not validated locally and are rejected upstream → MCP INTERNAL_ERROR at the tool layer. PrashnaInput enforces date/time/lat/lon/ayanamsa patterns locally.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string)\ndata.question (string — keyword echoed)\ndata.primary_house (int)\ndata.ithsala_applying (bool — Tajika Ithasala; false when one planet rules both houses)\ndata.ithsala_separating (bool — Tajika Musaripha)\ndata.query_utc (string — ISO UTC)\ndata.lagna:\n  rashi_index (int)\n  rashi (string)\n  longitude (float)\n  lord (string)\ndata.house_analysis:\n  house (int)\n  rashi_index (int)\n  rashi (string)\n  lord (string)\n  lord_dignity (string)\n  lord_house (int)\n  lord_longitude (float)\n  occupants[] (string array)\ndata.moon:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  nakshatra (string)\n  phase (string — 'waxing' or 'waning')\n  dignity (string)\n  void_of_course (bool)\n  afflicted_moon (bool)\n  applying_to_benefic (bool)\ndata.verdict:\n  verdict (string — 'favorable', 'mixed', or 'unfavorable')\n  confidence (string — 'high', 'medium', or 'low')\n  score (int — negative unfavorable, positive favorable)\ndata.planets{} — per planet: longitude (float), rashi_index (int), rashi (string), house (int), is_retrograde (bool), dignity (string)\ndata.house_cusps{} — keys '1'..'12': rashi_index (int), rashi (string), lord (string), longitude (float)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — PrashnaInput Pydantic violations (date, time, lat, lon, ayanamsa) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — bad question tokens surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Moon void-of-course flagged classically negative for outcomes.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — requires birth data, not query-moment prashna.\nasterwise_get_kp_chart — natal KP from birth time, not horary keyword mapping."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_prashna_chart(
        ctx: Context,
        prashna: PrashnaInput
    ) -> str:
        """Prashna horary chart."""
        async with tool_guard("asterwise_get_prashna_chart"):
            api_key = await require_api_key(ctx)
            rf = prashna.response_format
            data = await get_client().post(
                "/v1/astro/prashna", api_key, prashna_dict(prashna),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                rf,
                lambda d: structured_markdown("Prashna chart", d),
            )
    @mcp.tool(
        name="asterwise_get_lal_kitab_chart",
        title="Lal Kitab Chart",
        description=compact_description("asterwise_get_lal_kitab_chart", "Produces a Lal Kitab chart from BirthData following the 1952 Lal Kitab: houses counted from the Vedic lagna, the lagna house read as house 1 (Aries). Returns planets with pakka ghar, uchcha/neecha, fixed or doubtful effect and malefic reasons, the twelve houses, and the nine Lal Kitab debts (rin).\n\nSECTION: WHAT THIS TOOL COVERS\nReturns data.ascendant, planets{} with lk_house and Lal Kitab flags, houses{} with the Lal Kitab sign (house N = sign N), the actual birth sign, occupants and the 1952 house title, and rin_analysis with nine debt booleans, active_rins[] and rin_remedies[]. Every table cites the 1952 text (Goswami & Vashisth translation page numbers). Do not merge these houses with asterwise_get_natal_chart Bhava Chalit without explicit user intent.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone for Lal Kitab queries.\nAFTER: asterwise_get_lal_kitab_remedies — remedies for the planets that need them.\n\nSECTION: INPUT CONTRACT\nBirthData global contract. ayanamsa: lahiri (default), raman or kp is used as sent; tropical is refused (INVALID_PARAMS) because Lal Kitab starts from the sidereal Indian chart. Unknown birth time: omit time (a sunrise chart is cast and birth_time_provided=false); houses are then approximate.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'lal_kitab')\ndata.ayanamsa (string — the sidereal ayanamsa used)\ndata.birth_time_provided (bool)\ndata.ascendant — { longitude (float), rashi_index (int 0-11), rashi (string) } — the sign that becomes house 1\ndata.planets{} — Sun..Ketu:\n  longitude (float), rashi_index (int), rashi (string)\n  lk_house (int — 1–12, counted from the lagna)\n  house_lord (string — lord of the sign Lal Kitab reads in that house)\n  is_retrograde (bool)\n  pucca_ghar (bool), pucca_houses[] (int array)\n  uchcha (bool), neecha (bool), uchcha_houses[], neecha_houses[] (int arrays)\n  effect (string — 'fixed' or 'doubtful'; only doubtful effects can be remedied)\n  companion_planets[] (string array)\n  malefic_reasons[] (string array — empty when not malefic)\ndata.houses{} — keys '1'..'12':\n  house (int), rashi_index (int — house-1), rashi (string), lord (string)\n  birth_rashi_index (int), birth_rashi (string) — the actual sign in that house\n  pucca_ghar_of[] (string array), occupants[] (string array), signification (string — 1952 house title)\ndata.rin_analysis:\n  pitru_rin, swayam_rin, matru_rin, stri_rin, rishtedar_rin, behan_rin, zalimana_rin, ajanma_rin, dev_rin (bool)\n  active_rins[] (string array)\n  rin_remedies[] — { rin, name, planet, houses[], found[] { planet, house }, remedy, source }\n  rule, not_evaluated, remedy_rules (strings)\ndata.sources[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json returns the complete response as indented JSON. response_format=markdown renders a planet table and the debts with their remedies; use json for the full data.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — BirthData violations (date that is badly formatted or does not exist, time, lat/lon) → MCP INVALID_PARAMS\n  — ayanamsa='tropical' → MCP INVALID_PARAMS (Lal Kitab needs a sidereal chart)\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Lal Kitab houses are whole-sign houses from the lagna, not cusps.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — classical radix, not Lal Kitab rules.\nasterwise_get_lal_kitab_remedies — remedies only, for the planets that need them."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_lal_kitab_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Lal Kitab chart."""
        async with tool_guard("asterwise_get_lal_kitab_chart"):
            _lk_reject_tropical(birth)
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/chart", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                _lk_chart_md,
            )
    @mcp.tool(
        name="asterwise_get_lal_kitab_remedies",
        title="Lal Kitab Remedies",
        description=compact_description("asterwise_get_lal_kitab_remedies", "Lists Lal Kitab remedies (from the 1952 Lal Kitab) for the planets that need them, each with its book page, plus remedies for any indicated debts (rin).\n\nSECTION: WHAT THIS TOOL COVERS\nA planet is listed only when its effect is doubtful (it is not in its own house, pakka ghar, or exaltation or debilitation house, or it is a companion planet) and its placement is generally malefic (debilitated or in an enemy's house). Malefic planets with a fixed effect are in not_remediable[]: Lal Kitab says remedies cannot change them. Exalted planets and planets in their own house are never listed. Distinct from classical mantra/gem rows (asterwise_get_remedies).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_lal_kitab_chart — see the chart and malefic reasons first.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nBirthData only. ayanamsa: lahiri (default), raman or kp is used as sent; tropical is refused (INVALID_PARAMS) because Lal Kitab starts from the sidereal Indian chart. Unknown birth time: omit time (a sunrise chart is cast and birth_time_provided=false); houses, and so the remedies, are then approximate.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'lal_kitab')\ndata.ayanamsa (string — the sidereal ayanamsa used)\ndata.birth_time_provided (bool)\ndata.ascendant — { longitude, rashi_index, rashi }\ndata.remedies[] — in planet order Sun..Ketu, each:\n  planet (string), lk_house (int), rashi (string)\n  pucca_ghar (bool), uchcha (bool — always false here), neecha (bool)\n  effect (string — always 'doubtful')\n  malefic_reasons[] (string array)\n  remedies[] — { type ('donation', 'keep', 'avoid' or 'remedy'), action (string), page (int — Goswami & Vashisth, Lal Kitab, based on the 1952 edition), condition (string or null — extra condition the book attaches), note (string, optional — set when the book says 'same as' another placement) }; empty when the book gives none\ndata.not_remediable[] — { planet, lk_house, reasons[] }\ndata.rin_remedies[] — { rin, name, planet, houses[], found[] { planet, house }, remedy, source }\ndata.rule (string)\ndata.sources[] (string array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json returns the complete response as indented JSON. response_format=markdown renders each planet's remedies with page numbers and conditions; use json for the full data.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — BirthData violations (date that is badly formatted or does not exist, time, lat/lon) → MCP INVALID_PARAMS\n  — ayanamsa='tropical' → MCP INVALID_PARAMS (Lal Kitab needs a sidereal chart)\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Empty remedies[] is normal when no planet is both remediable and malefic.\n  — Some remedies carry a condition (another planet's placement, age, family situation); show the condition with the remedy.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_remedies — mantra/gem prescriptions, not Lal Kitab remedies.\nasterwise_get_gemstone_recommendations — classical Ratna focus, not household remedies."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_lal_kitab_remedies(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Lal Kitab remedies."""
        async with tool_guard("asterwise_get_lal_kitab_remedies"):
            _lk_reject_tropical(birth)
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/remedies", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                _lk_remedies_md,
            )
    @mcp.tool(
        name="asterwise_get_kp_chart",
        title="KP Chart",
        description=compact_description("asterwise_get_kp_chart", "Builds a KP natal chart with sub-lords on grahas and twelve cusps from BirthData using the KP ayanamsa in the response.\n\nSECTION: WHAT THIS TOOL COVERS\nKrishnamurti Paddhati charting: lagna row, planet rows with nakshatra_index and sub_lord, house_cusps with matching lords. BirthData.ayanamsa is ignored: the server always uses the KP (Krishnamurti) ayanamsa. house is the KP cusp-to-cusp house (sidereal Placidus cusps; a planet exactly on a cusp starts that house); rasi_house is the whole-sign house. Charts inside the polar circles (no Placidus cusps) are refused with a validation error. Accurate birth time matters; midnight placeholder yields unreliable sub-lords for event timing. Not radix (asterwise_get_natal_chart) nor prashna (asterwise_get_prashna_chart).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — cross-check birth record before trusting sub-lords.\nAFTER: asterwise_get_kp_significators — house-level significator chains.\n\nSECTION: INPUT CONTRACT\nayanamsa is accepted but ignored (always KP). Birth time is required: this tool has no sunrise fallback. If the user doesn't know it, say so rather than guessing; never pass time='00:00' for unknown.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.house_basis (string — 'placidus_cusp_to_cusp')\ndata.lagna:\n  rashi (string)\n  rashi_index (int)\n  longitude (float)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.planets{} — Sun..Ketu:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  degree (float)\n  is_retrograde (bool)\n  house (int — KP cusp-to-cusp house)\n  rasi_house (int — whole-sign house from the lagna sign)\n  nakshatra_index (int — 0–26)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.house_cusps{} — keys '1'..'12':\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  nakshatra_lord (string)\n  sub_lord (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — Birth inside the polar circles, where Placidus cusps do not exist → 422 validation_error, surfaces as MCP INTERNAL_ERROR with the API message.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Sub-lord chains degrade when true birth time unknown.\n  — Inside the polar circles (beyond ~66.5°) Placidus cusps do not exist and the API returns 422 validation_error with details[].issue = no_quadrant_houses_at_this_latitude and input_format_ok = true. This is not an input error: tell the user KP cannot be cast for that place and time; do not ask them to correct their details.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — classical bundle without KP sub-lords.\nasterwise_get_kp_ruling_planets — rulers at the moment of judgment (now or a given time), not natal cusps."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_kp_chart(
        ctx: Context,
        birth: TimedBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """KP chart."""
        async with tool_guard("asterwise_get_kp_chart"):
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/kp/chart", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP chart", d),
            )
    @mcp.tool(
        name="asterwise_get_kp_significators",
        title="KP Significators",
        description=compact_description("asterwise_get_kp_significators", "Computes KP significator chains for all houses or one optional house from BirthData and returns house tables plus planet-tier reverse indexes.\n\nSECTION: WHAT THIS TOOL COVERS\nFor each house string key '1'..'12', lists sign_lord, occupants, nakshatra lord chains, and unions; planet_significators{} exposes tiered house lists per graha. Optional house_number keeps that one house in significators{} (the server returns all twelve; the tool filters). Values outside 1..12 are refused locally as MCP INVALID_PARAMS. Requires same birth tuple as asterwise_get_kp_chart for coherent analysis.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_kp_chart — establish cusps before significators.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nhouse_number optional int 1..12; omit for all twelve.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.significators{} — keys '1'..'12':\n  house (int)\n  sign_lord (string)\n  occupants[] (string array — planets in the house, cusp to cusp)\n  nak_of_occupants[] (string array)\n  nak_of_lord[] (string array)\n  all_significators[] (string array — union; not a ranking)\n  strength_order[] (string array — strongest first: star of occupants, occupants, star of sign lord, sign lord)\ndata.planet_significators{} — per planet:\n  tier1_houses[] (int array)\n  tier2_houses[] (int array)\n  tier3_houses[] (int array)\n  tier4_houses[] (int array)\n  all_significators[] (int array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — house_number outside 1..12.\n\nINVALID_PARAMS (upstream):\n  — Birth inside the polar circles, where Placidus cusps do not exist → 422 validation_error, surfaces as MCP INTERNAL_ERROR with the API message.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Filtering to one house still returns planet_significators{} for context.\n  — Inside the polar circles (beyond ~66.5°) Placidus cusps do not exist and the API returns 422 validation_error with details[].issue = no_quadrant_houses_at_this_latitude and input_format_ok = true. This is not an input error: tell the user KP cannot be cast for that place and time; do not ask them to correct their details.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_kp_chart — cusps and sub-lords, not tiered significator unions.\nasterwise_get_natal_chart — classical drishti matrices differ from KP significator tiers."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_kp_significators(
        ctx: Context,
        birth: TimedBirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        house_number: int | None = None
    ) -> str:
        """KP significators."""
        async with tool_guard("asterwise_get_kp_significators"):
            api_key = await require_api_key(ctx)
            if house_number is not None and not 1 <= house_number <= 12:
                invalid_params("house_number must be between 1 and 12, or omitted for all houses.")
            data = await get_client().post(
                "/v1/astro/kp/significators", api_key, birth.to_api_dict(), timeout=20.0
            )
            if house_number is not None:
                # The API returns all twelve houses (it has no house filter);
                # keep the requested one, and planet_significators for context.
                payload = data.get("data") if isinstance(data, dict) else None
                houses = payload.get("significators") if isinstance(payload, dict) else None
                if isinstance(houses, dict):
                    payload["significators"] = {
                        k: v for k, v in houses.items() if str(k) == str(house_number)
                    }
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP significators", d),
            )
    @mcp.tool(
        name="asterwise_get_kp_ruling_planets",
        title="KP Ruling Planets",
        description=compact_description("asterwise_get_kp_ruling_planets", "Computes KP ruling planets at lat/lon for the current instant or a given local date and time, with no birth data, and returns day lord, Moon/Ascendant lord chains, and a deduplicated ruling_planets list.\n\nSECTION: WHAT THIS TOOL COVERS\nKP snapshot at the moment of judgment (now unless a date or time is given): target_utc, target_timezone, day_lord, Moon and Ascendant tuples with sign/nakshatra/sub lords, ruling_planets[] unique names. Not natal positions (asterwise_get_kp_chart) and not house significators (asterwise_get_kp_significators). Coordinate sanity is upstream — not locally validated floats beyond whatever FastMCP passes.\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_kp_chart — if natal confirmation is needed afterwards.\n\nSECTION: INPUT CONTRACT\nlat and lon required. Optional target_date (YYYY-MM-DD), target_time (HH:MM), target_timezone (IANA; defaults to the zone at lat/lon). With neither date nor time the server uses the current instant (KP judges ruling planets at the moment of judgment); time only = that time today; date only = 12:00 local. data.target_utc and data.target_timezone show what was used. target_date must be within 1800-01-01 to 2099-12-31. A time skipped by a daylight-saving change is read with the offset before the change (moved forward by the gap); a time that occurred twice is read as the first occurrence; data.local_time_status is 'nonexistent' / 'ambiguous' / 'ok'.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.target_utc (string — ISO UTC, the instant used)\ndata.target_timezone (string — zone used to read target_date/target_time and for the sunrise-based day lord)\ndata.local_time_status (string — 'ok', 'nonexistent' (daylight-saving gap) or 'ambiguous' (time occurred twice))\ndata.day_lord (string — planet name)\ndata.moon:\n  longitude (float)\n  rashi (string)\n  sign_lord (string)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.ascendant — same fields as data.moon\ndata.ruling_planets[] (string array — unique names, deduplicated)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — target_date not YYYY-MM-DD or target_time not HH:MM (schema pattern) → MCP INVALID_PARAMS. lat/lon are not range-checked locally.\n\nINVALID_PARAMS (upstream):\n  — Unknown target_timezone, a target_date that is not in the calendar (e.g. 2026-02-30 → 'does not exist'), or a target_date outside 1800-01-01 to 2099-12-31 (the message names the range) → 422 validation_error, surfaces as MCP INTERNAL_ERROR with the API message.\n  — Polar day or night: the sunrise-based day lord fails with 422 sun_calculation_failed.\n  — Coordinate errors surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Represents the sky at one instant (now, or the given local date/time) — differs from natal stored charts.\n  — Works at any latitude (only the ascendant is used, no house cusps); only the day lord needs a sunrise.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_kp_chart — needs BirthData and returns full natal KP cusps.\nasterwise_get_prashna_chart — horary keyword workflow, not ruling-planet snapshot."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_kp_ruling_planets(
        ctx: Context,
        lat: float,
        lon: float,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
        target_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        target_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$"),
        target_timezone: Optional[str] = None,
    ) -> str:
        """KP ruling planets (time/location)."""
        async with tool_guard("asterwise_get_kp_ruling_planets"):
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = {"lat": lat, "lon": lon}
            # Each is optional upstream: neither date nor time means "now";
            # the zone defaults to the one at lat/lon.
            for key, value in (
                ("target_date", target_date),
                ("target_time", target_time),
                ("target_timezone", target_timezone),
            ):
                if value is not None:
                    body[key] = value
            data = await get_client().post(
                "/v1/astro/kp/ruling-planets",
                api_key,
                body,
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP ruling planets", d),
            )
    @mcp.tool(
        name="asterwise_get_ashtakavarga",
        title="Ashtakavarga",
        description=compact_description("asterwise_get_ashtakavarga", "Computes full Ashtakavarga bindu matrices, trikona and ekadhipatya reductions, and sarva totals from BirthData for transit support analysis.\n\nSECTION: WHAT THIS TOOL COVERS\nAshtakavarga: bhinna tables per contributing body (including Lagna), reduced variants, sarva and sarva_reduced arrays, after_trikona/after_ekadhipatya aggregates, birth_time_provided flag. Threshold lore: twenty-eight or more sarva bindus supports transits; below twenty-five implies friction. Not Shadbala totals (asterwise_get_chart_strength) though that bundle duplicates this data when needed.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — confirm chart before AVK study.\nAFTER: asterwise_get_gochar — uses AVK scores in transit rows.\n\nSECTION: INPUT CONTRACT\nBirthData only.\n\nSECTION: OUTPUT CONTRACT\ndata.bhinna — keys Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Lagna → each twelve-element int array (rashi index 0=Mesha .. 11=Meena), bindu 0..8\ndata.bhinna_after_trikona — seven planets (no Lagna), same array shape\ndata.bhinna_after_ekadhipatya — same after Ekadhipatya Shodhana (BPHS Ch.70; occupancy by the seven grahas only)\ndata.sarva[] — twelve ints\ndata.sarva_reduced[] — twelve ints\ndata.after_trikona[] — twelve ints (legacy, not classical; use sarva_reduced)\ndata.after_ekadhipatya[] — twelve ints (legacy, not classical; use sarva_reduced)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Rahu/Ketu are not classical bhinna contributors per tradition.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_chart_strength — primary payload is Shadbala/Vimshopaka, though it embeds AVK too.\nasterwise_get_gochar — applies AVK scores to transits rather than exposing raw matrices."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_ashtakavarga(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN
    ) -> str:
        """Ashtakavarga."""
        async with tool_guard("asterwise_get_ashtakavarga"):
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/ashtakavarga", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Ashtakavarga", d),
            )
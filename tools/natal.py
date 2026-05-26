"""Natal chart and extended chart tools (Vedic chart foundations)."""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import (
    BirthData,
    DivisionalChartType,
    PrashnaInput,
    ResponseFormat,
    prashna_dict,
)
from runtime import (
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


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
        description="Computes the full sidereal natal chart from BirthData and returns planet rows, houses, aspects, arudhas, upapada, bhava cusps, and avakhada metadata.\n\nSECTION: WHAT THIS TOOL COVERS\nVedic natal endpoint: nine grahas with signs, degrees, nakshatras, combustion, retrograde, Bhava Chalit and rashi houses, twelve house cusps, graha and rashi drishti, arudha padas A1–A12, upapada lagna block, bhava madhya/sandhi arrays, ayanamsa metadata, and avakhada attributes. When include_interpretation=true, ascendant_sign_interpretation, moon_sign_interpretation, moon_nakshatra_interpretation, and interpretation are populated from interpretation JSON; otherwise they are null. It does not return PDFs, yogas list (asterwise_get_yogas), or dasha trees (asterwise_get_dasha).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: RECOMMENDED — asterwise_get_yogas — layer classical combinations after the base chart exists.\n\nSECTION: INPUT CONTRACT\nBirthData enforces date YYYY-MM-DD, time HH:MM, lat -90..90, lon -180..180, ayanamsa enum locally (Pydantic). Unknown birth time may be entered as time='00:00' without error; lagna-sensitive results are then unreliable and callers must handle that — the API does not flag it.\n\nSECTION: OUTPUT CONTRACT\ndata.planets[] — nine objects:\n  planet (string)\n  sign (string)\n  sign_num (int — 0–11)\n  degree (float)\n  nakshatra (string)\n  nakshatra_pada (int — 1–4)\n  is_retrograde (bool)\n  is_combust (bool)\n  is_deep_combust (bool)\n  house (int — Bhava Chalit)\n  rasi_house (int)\n  bhava_chalit_house (int)\ndata.houses[] — twelve objects:\n  house (int)\n  sign (string)\n  sign_num (int)\n  degree (float)\ndata.ascendant (float)\ndata.ascendant_sign (string — Sanskrit name)\ndata.moon_sign (string)\ndata.moon_nakshatra (string)\ndata.ayanamsa_value (float)\ndata.ayanamsa_used (string)\ndata.avakahada:\n  nakshatra, nakshatra_lord, charan (int), rashi, rashi_lord, varna, vashya, yoni, gana, nadi, paya, ascendant, ascendant_lord, sun_sign, sun_sign_lord (strings/ints per upstream)\ndata.graha_drishti — object keyed by planet name; each value object keyed by house strings '1'–'12' with aspect strength int (25, 50, 75, or 100)\ndata.rashi_drishti[] — active sign-to-sign aspect pairs:\n  { from_sign (string), from_sign_num (int 0-11), to_sign (string), to_sign_num (int 0-11) }\ndata.arudha_padas — keys A1–A12 each { sign_index (int), sign_name (string) }\ndata.upapada_lagna:\n  sign_index (int)\n  sign_name (string)\n  upapada_lord (string)\n  second_from_upapada_sign_index (int)\n  second_from_upapada_sign_name (string)\n  planets_in_second_from_upapada[] (string array of planet names)\n  has_benefic_in_second_from_upapada (bool)\n  has_malefic_in_second_from_upapada (bool)\ndata.bhava_madhya[] — twelve objects:\n  { house (int 1-12), sign (string), sign_num (int 0-11), degree (float) }\ndata.bhava_sandhi[] — twelve objects:\n  { house (int 1-12), sign (string), sign_num (int 0-11), degree (float) }\ndata.birth_time_provided (bool — always false; no detection)\ndata.fallback_method (null)\nascendant_sign_interpretation (dict or null — sign interpretation from signs/ascendant.json when include_interpretation=true)\n  moon_sign_interpretation (dict or null — Moon sign interpretation from signs/moon_sign.json when include_interpretation=true)\n  moon_nakshatra_interpretation (dict or null — nakshatra interpretation from nakshatras/ files when include_interpretation=true)\n  interpretation (list or null — planet-in-house interpretation list when include_interpretation=true)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — BirthData Pydantic violations (date/time/lat/lon/ayanamsa) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — calendar years outside supported upstream window surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — time='00:00' accepted; lagna may be wrong if true birth time unknown — not auto-detected.\n  — Interpretation fields are null unless include_interpretation=true on the request.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_divisional_chart — sixteen vargas only, not the primary radix bundle returned here.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_natal_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        include_interpretation: bool = False,
    ) -> str:
        """Compute full natal chart from classical calculations."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_natal_chart", exc)

    @mcp.tool(
        name="asterwise_get_divisional_chart",
        description="Computes divisional (varga) chart positions from BirthData; pass chart_type for one varga, or omit chart_type for all sixteen.\n\nSECTION: WHAT THIS TOOL COVERS\nWhen chart_type is provided, returns only that one divisional chart.\nWhen chart_type is omitted, returns all sixteen standard classical divisional charts\n(D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60).\nD30 omits Sun and Moon per convention. Does not return Shadbala\n(asterwise_get_chart_strength) or radix-only graha drishti (asterwise_get_natal_chart).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — anchor D1 before reading higher vargas.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nchart_type enum is enforced locally (Pydantic). BirthData follows the global contract.\n\nSECTION: OUTPUT CONTRACT\nWhen chart_type is provided:\n  data — object with a single key (the requested chart, e.g. 'D9'):\n    planet_name (Sun..Ketu) → { sign (string), sign_num (int), degree (float) }\nWhen chart_type is omitted:\n  data — object with keys D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27,\n    D30, D40, D45, D60 — each: planet_name → { sign, sign_num, degree }\n  (D30 excludes Sun and Moon entries.)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid chart_type enum → MCP INVALID_PARAMS (via Pydantic)\n\nINVALID_PARAMS (upstream):\n  — None — unknown ayanamsa for a varga surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — radix chart with houses and drishti, not the full varga dictionary.\nasterwise_get_chart_strength — embeds vargas inside strength metrics, different primary payload.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_divisional_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        chart_type: Optional[DivisionalChartType] = None,
    ) -> str:
        """Compute divisional (varga) chart."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_divisional_chart", exc)

    @mcp.tool(
        name="asterwise_get_chart_strength",
        description="Aggregates Shadbala, Bhavbala, Vimshopaka (with per-varga contributions), embedded sixteen vargas, Ashtakavarga, karaka maps, and graha yuddha pairs from BirthData.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns chart strength computations: six-planet Shadbala breakdowns with sthana/kala detail objects, twelve-house Bhavbala totals, Vimshopaka scores with threshold bands and per-D1..D60 fractions, full divisional chart mirror of asterwise_get_divisional_chart, Ashtakavarga mirror of asterwise_get_ashtakavarga, karaka_to_planet / planet_to_karaka, and graha_yuddha.war_pairs. It does not label named yogas (asterwise_get_yogas) or doshas (asterwise_get_doshas).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — contextualises houses before reading bala tables.\nAFTER: asterwise_get_yogas — optional configuration pass after strength review.\n\nSECTION: INPUT CONTRACT\nBirthData only; no extra toggles.\n\nSECTION: OUTPUT CONTRACT\ndata.shadbala — keyed by Sun..Saturn (excludes Rahu/Ketu):\n  planet (string)\n  sthana_bala, dig_bala, dig_bala_virupas, dig_bala_rupas, kala_bala, cheshta_bala, naisargika_bala, drik_bala, yuddhabala_adjustment, total (float), ratio (float), required_minimum (float), is_purna_bala (bool)\n  sthana_bala_details — { uchcha, saptavargaja, ojhayugma, kendradi, drekkana, total }\n  kala_bala_details — { nathonnatha, paksha, tribhaga, vara, hora, ayana, total }\ndata.bhavbala — keys '1'..'12':\n  bhavadhipati_bala, bhava_dig_bala, bhava_drik_bala, total (float)\ndata.vimshopaka_bala — keyed by planet including Rahu/Ketu:\n  vimshopaka_score (float, max 20)\n  threshold (string — 'zero_capacity', 'moderate', 'good', or 'extremely_auspicious')\n  per_varga — keyed by D1..D60: { contribution (float), fraction (float) }\ndata.divisional_charts — same nested schema as asterwise_get_divisional_chart\ndata.ashtakavarga — same schema as asterwise_get_ashtakavarga\ndata.karakas — { karaka_to_planet{}, planet_to_karaka{} }\ndata.graha_yuddha — { war_pairs[] }\nThreshold guide: 15+ extremely_auspicious, 10–15 good, 5–10 moderate, below 5 zero_capacity.\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE (~800ms)\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData only; Pydantic handles field bounds.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Large payload due to embedded vargas and Ashtakavarga duplicates.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_yogas — boolean yoga catalogue, not numeric bala.\nasterwise_get_ashtakavarga — standalone AVK when strength bundle is not needed.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_chart_strength(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Shadbala and Bhavbala."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/strength", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Chart strength (Shadbala / Bhavbala)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_chart_strength", exc)

    @mcp.tool(
        name="asterwise_get_special_ascendants",
        description="Calls atmakaraka and ishta-devata endpoints sequentially and merges their payloads into top-level atmakaraka and ishta_devata objects for one BirthData.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns the karaka layer: eight-karaka mapping, soul significator graha, navamsa-based ishta devata inference, twelfth-house occupants, and D9 positions map. It is not general prediction, medical timing, or matchmaking scoring. Two planets tied by degree use classical highest-longitude resolution without raising an error.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — understand chart basics before devotional pointers.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nWrapper returns { atmakaraka: <upstream dict>, ishta_devata: <upstream dict> } — not a flat data.* root; consumers must read nested .data fields inside each branch per upstream shape.\n\nSECTION: OUTPUT CONTRACT\nTop-level merge:\n  atmakaraka — upstream POST /v1/astro/atmakaraka body; use atmakaraka.data:\n    karaka_to_planet{} (eight karakas to planet names)\n    planet_to_karaka{}\n    atmakaraka (string)\n    atmakaraka_sign (string)\n    atmakaraka_nakshatra (string)\n    details{} — per karaka: planet, rashi, nakshatra, longitude\n  ishta_devata — upstream POST /v1/astro/ishta-devta body; use ishta_devata.data:\n    atmakaraka (string)\n    karakamsha_lagna (string)\n    karakamsha_lagna_index (int)\n    jivanmuktamsa_planet (string)\n    navamsa_lagna (string)\n    navamsa_lagna_index (int)\n    twelfth_house_sign (string)\n    twelfth_house_index (int)\n    planets_in_12th[] (string array)\n    ishta_devta_planet (string)\n    deity (string)\n    description (string)\n    method (string)\n    d9_positions{} — per planet: { sign (string), sign_num (int) }\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData validated via Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout on either sequential call → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Identical-degree planets: classical tie-break applies; no error.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — general chart; does not compute ishta devata workflow.\nasterwise_get_char_dasha — timing system using karakas, not deity discovery.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_special_ascendants(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Atmakaraka and Ishta Devata (two API calls)."""
        try:
            api_key = await require_api_key(ctx)
            bd = birth.to_api_dict()
            atm = await get_client().post("/v1/astro/atmakaraka", api_key, bd, timeout=20.0)
            ishta = await get_client().post("/v1/astro/ishta-devta", api_key, bd, timeout=20.0)
            merged = {"atmakaraka": atm, "ishta_devata": ishta}

            def _md(d: dict[str, Any]) -> str:
                parts = [
                    "## Atmakaraka",
                    structured_markdown("Atmakaraka", atm),
                    "",
                    "## Ishta Devata",
                    structured_markdown("Ishta Devata", ishta),
                ]
                return "\n".join(parts)

            return format_tool_result(merged, response_format, _md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_special_ascendants", exc)

    @mcp.tool(
        name="asterwise_get_nakshatra_details",
        description="Looks up static metadata for one of twenty-seven nakshatras by exact name and returns interpretive, professional, activity, and body-map reference data.\n\nSECTION: WHAT THIS TOOL COVERS\nVedanga/classical reference only — no chart computation. Covers deity, ruler, symbol, gana, nature, classical vs modern prose, profession vectors, life themes, keywords, strengths/challenges, favourable vs unfavourable activities, and body_map. Names are case-sensitive exact matches (Ashwini … Revati list). It does not compute birth nakshatra from BirthData (use asterwise_get_natal_chart).\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nnakshatra_name is forwarded raw — no local fuzzy matching or normalisation.\n\nSECTION: OUTPUT CONTRACT\ndata.name (string)\ndata.index (int — 0–26)\ndata.interpretation:\n  source (string)\n  nakshatra_number (int)\n  name (string)\n  sanskrit (string)\n  span (string)\n  symbol (string)\n  deity (string)\n  ruling_planet (string)\n  sign (string)\n  sign_lord (string)\n  gana (string)\n  nature (string)\n  body_part (string)\n  classical_qualities[] (string array)\n  appearance — { classical (string), modern (string) }\n  nature_description — { classical (string), modern (string) }\n  profession — { primary[] (string array), secondary[] (string array), note (string), modern (string) }\n  life_themes — { core, karmic_path, challenge, gift, modern (strings) }\n  keywords[] (string array)\n  strengths[] (string array)\n  challenges[] (string array)\ndata.activities:\n  favorable_activities[] (string array)\n  unfavorable_activities[] (string array)\ndata.body_map:\n  parts[] (string array)\n  sensitivity (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — name passes straight through.\n\nINVALID_PARAMS (upstream):\n  — None — unknown names surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Exact spelling required — no fuzzy recovery.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — computes birth nakshatra from time/place, not encyclopaedic copy.\nasterwise_get_dasha — uses Moon nakshatra for timing, not this lookup table.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_nakshatra_details(
        ctx: Context,
        nakshatra_name: str,
        response_format: ResponseFormat
    ) -> str:
        """Nakshatra reference details."""
        try:
            api_key = await require_api_key(ctx)
            path = f"/v1/astro/nakshatra/{safe_segment(nakshatra_name)}"
            data = await get_client().get(path, api_key, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Nakshatra: {nakshatra_name}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_nakshatra_details", exc)

    @mcp.tool(
        name="asterwise_check_sade_sati",
        description="Evaluates Saturn's seven-and-a-half-year Moon-sign cycle phases against natal data for the current day and returns intensity, upcoming cycles, and historical rows.\n\nSECTION: WHAT THIS TOOL COVERS\nSade Sati mechanics: natal Moon sign in English, three reference signs (rising/peak/setting), active flag, current phase label, intensity score/label, next occurrence metadata, all_periods[] timeline with nested phase objects, mitigation booleans. \"Today\" is implicit — no date parameter. Signs are English, not Sanskrit. It is not general Gochar (asterwise_get_gochar) or dasha overlay (asterwise_get_dasha_transits).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — confirm Moon sign context.\nAFTER: asterwise_get_gochar — broader transit canvas if needed.\n\nSECTION: INPUT CONTRACT\nNo explicit query date — API pins to current day. BirthData global contract applies.\n\nSECTION: OUTPUT CONTRACT\ndata.natal_moon_sign (string — English, e.g. 'Libra')\ndata.natal_moon_sign_index (int — 0–11)\ndata.sade_sati_signs:\n  rising (string)\n  peak (string)\n  setting (string)\ndata.is_currently_active (bool)\ndata.current_phase (string — 'rising', 'peak', 'setting', or null)\ndata.current_phase_description (string or null)\ndata.intensity_score (int — 0–10)\ndata.intensity_label (string — 'low', 'moderate', or 'high')\ndata.next_sade_sati:\n  starts (string — YYYY-MM-DD)\n  phase (string)\n  years_away (float)\ndata.all_periods[] — each:\n  sade_sati_number (int)\n  overall_start (string — YYYY-MM-DD)\n  overall_end (string — YYYY-MM-DD)\n  duration_years (float)\n  phases:\n    rising — { name, description, start, end, saturn_sign, intensity }\n    peak — same shape\n    setting — same shape\ndata.mitigated_by_own_sign (bool)\ndata.mitigated_by_exaltation (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — English sign names throughout — do not expect Sanskrit.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — nine-planet daily scan including sade_sati_active flag but less Sade Sati detail than this tool.\nasterwise_get_transits — ingress/station feed, not Moon-focused Saturn phase model.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_check_sade_sati(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Sade Sati check."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/sade-sati", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Sade Sati", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_check_sade_sati", exc)

    @mcp.tool(
        name="asterwise_get_prashna_chart",
        description="Casts a Prashna chart for the query instant using supplied date, time, place, and a single-topic keyword, then returns houses, Moon diagnostics, verdict, and cusps.\n\nSECTION: WHAT THIS TOOL COVERS\nHorary workflow: maps one of the approved keywords to a primary house, evaluates Moon (phase, VOC, affliction), applies ithsala flags, aggregates graha dignities/houses from Prashna Lagna, and emits verdict/confidence/score. Not natal life analysis (asterwise_get_natal_chart) and not KP cusps from birth (asterwise_get_kp_chart).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone for horary.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nquestion must be exactly one of: self, wealth, siblings, property, children, health, marriage, death, travel, career, gains, loss. Full sentences are not validated locally and are rejected upstream → MCP INTERNAL_ERROR at the tool layer. PrashnaInput enforces date/time/lat/lon/ayanamsa patterns locally.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string)\ndata.question (string — keyword echoed)\ndata.primary_house (int)\ndata.ithsala_applying (bool)\ndata.ithsala_separating (bool)\ndata.query_utc (string — ISO UTC)\ndata.lagna:\n  rashi_index (int)\n  rashi (string)\n  longitude (float)\n  lord (string)\ndata.house_analysis:\n  house (int)\n  rashi_index (int)\n  rashi (string)\n  lord (string)\n  lord_dignity (string)\n  lord_house (int)\n  lord_longitude (float)\n  occupants[] (string array)\ndata.moon:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  nakshatra (string)\n  phase (string — 'waxing' or 'waning')\n  dignity (string)\n  void_of_course (bool)\n  afflicted_moon (bool)\n  applying_to_benefic (bool)\ndata.verdict:\n  verdict (string — 'favorable', 'mixed', or 'unfavorable')\n  confidence (string — 'high', 'medium', or 'low')\n  score (int — negative unfavorable, positive favorable)\ndata.planets{} — per planet: longitude (float), rashi_index (int), rashi (string), house (int), is_retrograde (bool), dignity (string)\ndata.house_cusps{} — keys '1'..'12': rashi_index (int), rashi (string), lord (string), longitude (float)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — PrashnaInput Pydantic violations (date, time, lat, lon, ayanamsa) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — bad question tokens surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Moon void-of-course flagged classically negative for outcomes.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — requires birth data, not query-moment prashna.\nasterwise_get_kp_chart — natal KP from birth time, not horary keyword mapping.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_prashna_chart(
        ctx: Context,
        prashna: PrashnaInput
    ) -> str:
        """Prashna horary chart."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_prashna_chart", exc)

    @mcp.tool(
        name="asterwise_get_lal_kitab_chart",
        description="Produces the Lal Kitab house and planet schema plus Rin (debt) flags from BirthData using Lal Kitab placement rules. Lal Kitab uses a distinct astrological system from standard Vedic computation, with its own house-based remedies.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns data.system 'lal_kitab', ayanamsa, planets{} with lk_house and pucca/kachcha flags, twelve houses{} with occupants and significations, and rin_analysis with boolean debts, active_rins[], and rin_remedies[] rows. Do not merge these houses with asterwise_get_natal_chart Bhava Chalit without explicit user intent — frameworks differ.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone for Lal Kitab queries.\nAFTER: asterwise_get_lal_kitab_remedies — practical totkas aligned to this chart.\n\nSECTION: INPUT CONTRACT\nBirthData global contract; mixing interpretive systems in prose is a caller concern, not validated here.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'lal_kitab')\ndata.ayanamsa (string)\ndata.planets{} — Sun..Ketu:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  lk_house (int — 1–12)\n  house_lord (string)\n  is_retrograde (bool)\n  pucca_ghar (bool)\n  kachcha_ghar (bool)\n  uchcha (bool)\n  neecha (bool)\n  pucca_house (int)\n  kachcha_house (int)\ndata.houses{} — keys '1'..'12':\n  house (int)\n  rashi_index (int)\n  rashi (string)\n  lord (string)\n  occupants[] (string array)\n  signification (string)\n  has_benefic (bool)\n  has_malefic (bool)\ndata.rin_analysis:\n  pitru_rin, matru_rin, bhai_rin, stri_rin, dev_rin (bool)\n  active_rins[] (string array)\n  rin_remedies[] — { rin (string), planet (string), totka (string) }\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Lal Kitab houses are not interchangeable with cusps.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — classical radix, not Lal Kitab lk_house logic.\nasterwise_get_lal_kitab_remedies — remedy list without full chart geometry.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_lal_kitab_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Lal Kitab chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/chart", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lal Kitab chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lal_kitab_chart", exc)

    @mcp.tool(
        name="asterwise_get_lal_kitab_remedies",
        description="Lists Lal Kitab style totkas per stressed planet from BirthData with priority tiers and typed action rows (remedy, donation, keep, avoid).\n\nSECTION: WHAT THIS TOOL COVERS\nOutputs data.system, ayanamsa, and remedies[] entries tying planets to lk context and nested remedies[] instructions. Distinct from classical mantra/gem rows (asterwise_get_remedies). Best interpreted alongside asterwise_get_lal_kitab_chart for house context.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_lal_kitab_chart — see chart before applying totkas.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nBirthData only.\n\nSECTION: OUTPUT CONTRACT\ndata.system (string — 'lal_kitab')\ndata.ayanamsa (string)\ndata.remedies[] — each:\n  planet (string)\n  lk_house (int)\n  rashi (string)\n  pucca_ghar (bool)\n  kachcha_ghar (bool)\n  uchcha (bool)\n  neecha (bool)\n  priority (string — 'high', 'medium', or 'low')\n  remedies[] — { type (string — 'remedy', 'donation', 'keep', or 'avoid'), action (string) }\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Empty remedies[] possible when no graha needs attention — still success if upstream returns so.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_remedies — mantra/gem prescriptions, not Lal Kitab totkas.\nasterwise_get_gemstone_recommendations — classical Ratna focus, not household remedies.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_lal_kitab_remedies(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Lal Kitab remedies."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/lal-kitab/remedies", api_key, birth.to_api_dict(),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Lal Kitab remedies", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_lal_kitab_remedies", exc)

    @mcp.tool(
        name="asterwise_get_kp_chart",
        description="Builds a KP natal chart with sub-lords on grahas and twelve cusps from BirthData using the KP ayanamsa in the response.\n\nSECTION: WHAT THIS TOOL COVERS\nKrishnamurti Paddhati charting: lagna row, planet rows with nakshatra_index and sub_lord, house_cusps with matching lords. Recommend BirthData.ayanamsa='kp' for coherent physics — any enum value is accepted locally and forwarded. Accurate birth time matters; midnight placeholder yields unreliable sub-lords for event timing. Not radix (asterwise_get_natal_chart) nor prashna (asterwise_get_prashna_chart).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — cross-check birth record before trusting sub-lords.\nAFTER: asterwise_get_kp_significators — house-level significator chains.\n\nSECTION: INPUT CONTRACT\nayanamsa choice is not forced locally — mismatched settings still post to upstream. time='00:00' is accepted without warning.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.lagna:\n  rashi (string)\n  rashi_index (int)\n  longitude (float)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.planets{} — Sun..Ketu:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  degree (float)\n  is_retrograde (bool)\n  house (int)\n  nakshatra_index (int — 0–26)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.house_cusps{} — keys '1'..'12':\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  nakshatra_lord (string)\n  sub_lord (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Sub-lord chains degrade when true birth time unknown.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — classical bundle without KP sub-lords.\nasterwise_get_kp_ruling_planets — live moment rulers, not natal cusps.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_kp_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """KP chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/kp/chart", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP chart", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_chart", exc)

    @mcp.tool(
        name="asterwise_get_kp_significators",
        description="Computes KP significator chains for all houses or one optional house from BirthData and returns house tables plus planet-tier reverse indexes.\n\nSECTION: WHAT THIS TOOL COVERS\nFor each house string key '1'..'12', lists sign_lord, occupants, nakshatra lord chains, and unions; planet_significators{} exposes tiered house lists per graha. Optional house_number filters upstream when provided. Out-of-range house integers are not validated locally — upstream handles errors as MCP INTERNAL_ERROR. Requires same birth tuple as asterwise_get_kp_chart for coherent analysis.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_kp_chart — establish cusps before significators.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nhouse_number optional int; omit for all twelve. Values outside 1..12 are validated upstream only.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.significators{} — keys '1'..'12':\n  house (int)\n  sign_lord (string)\n  occupants[] (string array)\n  nak_of_occupants[] (string array)\n  nak_of_lord[] (string array)\n  all_significators[] (string array)\ndata.planet_significators{} — per planet:\n  tier1_houses[] (int array)\n  tier2_houses[] (int array)\n  tier3_houses[] (int array)\n  tier4_houses[] (int array)\n  all_significators[] (int array)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — house_number not bounds-checked here.\n\nINVALID_PARAMS (upstream):\n  — None — invalid house indices surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Filtering to one house still returns planet_significators{} for context.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_kp_chart — cusps and sub-lords, not tiered significator unions.\nasterwise_get_natal_chart — classical drishti matrices differ from KP significator tiers.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_kp_significators(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        house_number: int | None = None
    ) -> str:
        """KP significators."""
        try:
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = birth.to_api_dict()
            if house_number is not None:
                body["house_number"] = house_number
            data = await get_client().post("/v1/astro/kp/significators", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP significators", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_significators", exc)

    @mcp.tool(
        name="asterwise_get_kp_ruling_planets",
        description="Computes KP ruling planets for the instantaneous chart at lat/lon with no birth data and returns day lord, Moon/Ascendant lord chains, and a deduplicated ruling_planets list.\n\nSECTION: WHAT THIS TOOL COVERS\nCurrent-moment KP snapshot: target_utc, day_lord, Moon and Ascendant tuples with sign/nakshatra/sub lords, ruling_planets[] unique names. Not natal positions (asterwise_get_kp_chart) and not house significators (asterwise_get_kp_significators). Coordinate sanity is upstream — not locally validated floats beyond whatever FastMCP passes.\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_kp_chart — if natal confirmation is needed afterwards.\n\nSECTION: INPUT CONTRACT\nlat and lon only; no date parameter — \"now\" is implicit on the server clock.\n\nSECTION: OUTPUT CONTRACT\ndata.ayanamsa (string — 'kp')\ndata.target_utc (string — ISO UTC)\ndata.day_lord (string — planet name)\ndata.moon:\n  longitude (float)\n  rashi (string)\n  sign_lord (string)\n  nakshatra_lord (string)\n  sub_lord (string)\ndata.ascendant — same fields as data.moon\ndata.ruling_planets[] (string array — unique names, deduplicated)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — lat/lon not range-checked locally.\n\nINVALID_PARAMS (upstream):\n  — None — coordinate errors surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Represents instantaneous sky — differs from natal stored charts.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_kp_chart — needs BirthData and returns full natal KP cusps.\nasterwise_get_prashna_chart — horary keyword workflow, not ruling-planet snapshot.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_kp_ruling_planets(
        ctx: Context,
        lat: float,
        lon: float,
        response_format: ResponseFormat
    ) -> str:
        """KP ruling planets (time/location)."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/kp/ruling-planets",
                api_key,
                {"lat": lat, "lon": lon},
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("KP ruling planets", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_kp_ruling_planets", exc)

    @mcp.tool(
        name="asterwise_get_ashtakavarga",
        description="Computes full Ashtakavarga bindu matrices, trikona and ekadhipatya reductions, and sarva totals from BirthData for transit support analysis.\n\nSECTION: WHAT THIS TOOL COVERS\nAshtakavarga: bhinna tables per contributing body (including Lagna), reduced variants, sarva and sarva_reduced arrays, after_trikona/after_ekadhipatya aggregates, birth_time_provided flag. Threshold lore: twenty-eight or more sarva bindus supports transits; below twenty-five implies friction. Not Shadbala totals (asterwise_get_chart_strength) though that bundle duplicates this data when needed.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — confirm chart before AVK study.\nAFTER: asterwise_get_gochar — uses AVK scores in transit rows.\n\nSECTION: INPUT CONTRACT\nBirthData only.\n\nSECTION: OUTPUT CONTRACT\ndata.bhinna — keys Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Lagna → each twelve-element int array (rashi index 0=Mesha .. 11=Meena), bindu 0..8\ndata.bhinna_after_trikona — seven planets (no Lagna), same array shape\ndata.bhinna_after_ekadhipatya — same after further reduction\ndata.sarva[] — twelve ints\ndata.sarva_reduced[] — twelve ints\ndata.after_trikona[] — twelve ints\ndata.after_ekadhipatya[] — twelve ints\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — BirthData Pydantic only.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Rahu/Ketu are not classical bhinna contributors per tradition.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_chart_strength — primary payload is Shadbala/Vimshopaka, though it embeds AVK too.\nasterwise_get_gochar — applies AVK scores to transits rather than exposing raw matrices.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_ashtakavarga(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Ashtakavarga."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post("/v1/astro/ashtakavarga", api_key, birth.to_api_dict(),
                timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Ashtakavarga", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_ashtakavarga", exc)

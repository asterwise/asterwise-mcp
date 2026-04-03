"""Natal chart and extended chart tools (BPHS / Parashari foundations)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

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
    STANDARD_ANNOTATIONS,
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
        description="Compute the complete Vedic birth chart (Janam Kundali) for a person.\n\nMANDATORY FIRST CALL: Use this as the entry point for any personalised\nJyotish analysis. Every natal tool (get_yogas, get_doshas,\nget_chart_strength, get_ashtakavarga, get_divisional_chart,\nget_special_ascendants, get_remedies, get_gemstone_recommendations,\nget_dasha, get_gochar) depends on the birth data this call processes.\n\nOUTPUT CONTRACT (response_format=json):\ndata.planets[] — array of 9 planet objects, each:\n  planet, sign, sign_num (0=Mesha…11=Meena), degree (absolute\n  longitude), nakshatra, nakshatra_pada, is_retrograde (bool),\n  is_combust (bool), is_deep_combust (bool), house (Bhava Chalit),\n  rasi_house (Rashi-based), bhava_chalit_house\ndata.houses[] — 12 house objects: house, sign, sign_num, degree\ndata.ascendant (float, absolute longitude)\ndata.ascendant_sign (Sanskrit name, e.g. 'Tula')\ndata.moon_sign, data.moon_nakshatra\ndata.ayanamsa_value, data.ayanamsa_used\ndata.avakahada — object with: nakshatra, nakshatra_lord, charan,\n  rashi, rashi_lord, varna, vashya, yoni, gana, nadi, paya,\n  ascendant, ascendant_lord, sun_sign, sun_sign_lord\ndata.graha_drishti — object keyed by planet, each value is object\n  keyed by house number with aspect strength (int: 25/50/75/100)\ndata.rashi_drishti — 12×12 int array (0 or 1)\ndata.arudha_padas — A1–A12, each: { sign_index, sign_name }\ndata.upapada_lagna — { sign_index, sign_name, upapada_lord,\n  second_from_upapada_sign, planets_in_second_from_upapada[],\n  has_benefic_in_second_from_upapada, has_malefic_in_second_from_upapada }\ndata.bhava_madhya[] — 12-element float array\ndata.bhava_sandhi[] — 12-element float array\ndata.birth_time_unknown (bool — always false; the API has no\n  unknown-birth-time detection. Passing time='00:00' computes Lagna\n  from midnight — result is astronomically incorrect if actual time\n  is unknown. Lagna-sensitive tools will be unreliable.)\ndata.fallback_method (always null)\n\nInterpretation fields (ascendant_sign_interpretation,\nmoon_sign_interpretation, moon_nakshatra_interpretation,\ninterpretation) are currently null — they are populated in\nresponse_format=markdown.\n\nERROR CONTRACT:\nInvalid time format → 422 validation error with details[].\nLatitude/longitude out of range → 422.\nInvalid ayanamsa → 422.\nDates before 1800 or after 2100 → 422 DATE_OUT_OF_SUPPORTED_RANGE.\nError shape: { error, message, details[], doc_url, retry_after* }\n\nCompute class: fast (~200ms). Suitable for synchronous inline calls.\n\nDo not confuse with asterwise_generate_kundli_report — that produces\na downloadable PDF document; this returns structured JSON for\nprogrammatic use.",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_natal_chart(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Compute full natal chart from BPHS-style calculations."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/natal", api_key, birth.to_api_dict(),
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
        description="Compute a specific divisional (Varga) chart for a person.\nCall asterwise_get_natal_chart first for reference chart comparison.\n\nSupported chart_type values: D1, D2, D3, D4, D7, D9, D10, D12, D16,\nD20, D24, D27, D30, D40, D45, D60. Each reveals a distinct life domain:\nD2 wealth, D3 siblings/courage, D4 property, D7 children, D9 spouse\nand dharma (most important varga after D1), D10 career, D12 parents,\nD16 vehicles/comforts, D20 spiritual practice, D24 education, D27\nstrengths, D30 misfortunes/health, D40 auspiciousness, D45 character,\nD60 past karma. Source: BPHS varga chapters.\n\nOUTPUT CONTRACT (response_format=json):\ndata — object containing all 16 D-charts. Even when chart_type\nspecifies a single chart (e.g. 'D9'), all charts are returned.\nEach chart is keyed by label ('D1', 'D9', etc.). Within each chart,\nkeys are planet names (Sun, Moon, Mars, Mercury, Jupiter, Venus,\nSaturn, Rahu, Ketu). Each planet: { sign, sign_num, degree }.\nNote: D30 omits Sun and Moon by classical convention.\n\nERROR CONTRACT: Invalid chart_type → 422 with details[].\nUnknown ayanamsa for a varga → 422.",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_divisional_chart(
        ctx: Context,
        birth: BirthData,
        chart_type: DivisionalChartType,
        response_format: ResponseFormat
    ) -> str:
        """Compute divisional (varga) chart."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "chart_type": chart_type.value}
            data = await get_client().post("/v1/astro/divisional", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Divisional chart {chart_type.value}", d),
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
        description="Calculate Shadbala (six-fold planetary strength), Bhavbala (house\nstrength), and Vimshopaka Bala (divisional dignity score) for the\nnatal chart. Call asterwise_get_natal_chart first.\nSource: BPHS strength chapters.\n\nOUTPUT CONTRACT (response_format=json):\ndata.shadbala — object keyed by planet (Sun, Moon, Mars, Mercury,\n  Jupiter, Venus, Saturn — Rahu/Ketu excluded from Shadbala).\n  Each planet: planet, sthana_bala, dig_bala, dig_bala_virupas,\n  dig_bala_rupas, kala_bala, cheshta_bala, naisargika_bala,\n  drik_bala, yuddhabala_adjustment, total, ratio,\n  required_minimum, is_purna_bala (bool), sthana_bala_details\n  (uchcha, saptavargaja, ojhayugma, kendradi, drekkana, total),\n  kala_bala_details (nathonnatha, paksha, tribhaga, vara, hora,\n  ayana, total)\ndata.bhavbala — object keyed by house number '1'–'12'. Each:\n  bhavadhipati_bala, bhava_dig_bala, bhava_drik_bala, total\ndata.vimshopaka_bala — object keyed by planet including Rahu/Ketu.\n  Each: vimshopaka_score (float, max 20), threshold (string:\n  'zero_capacity' <5, 'moderate' 5–10, 'good' 10–15,\n  'extremely_auspicious' 15+), per_varga (object keyed by\n  D1–D60, each: { contribution, fraction })\ndata.divisional_charts — all 16 D-charts embedded (same schema\n  as asterwise_get_divisional_chart). Each chart keyed by planet,\n  each planet: { sign, sign_num, degree }\ndata.ashtakavarga — full Ashtakavarga data (same as\n  asterwise_get_ashtakavarga response)\ndata.karakas — { karaka_to_planet{}, planet_to_karaka{} }\ndata.graha_yuddha — { war_pairs[] }\n\nVimshopaka threshold guide: 15+ extremely auspicious, 10–15 good,\n5–10 moderate, below 5 zero capacity.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\nCompute class: heavy (~800ms). Consider async handling.\n\nDo not confuse with asterwise_get_yogas — yogas identify\nconfigurations; strength measures raw planetary power.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Get two key spiritual significators from the natal chart in one call:\n(1) Atmakaraka — the planet with the highest sidereal degree, the\nsoul's primary desire in this life (Jaimini system); (2) Ishta Devata\n— the personal deity revealed via the 12th from the Karakamsha Lagna\nin D9 (BPHS/Jaimini). Call asterwise_get_natal_chart first.\n\nOUTPUT CONTRACT (response_format=json):\nResponse is a combined object with two keys:\natmakaraka.data — { karaka_to_planet{} (8 karakas mapped to planets),\n  planet_to_karaka{}, atmakaraka (planet name), atmakaraka_sign,\n  atmakaraka_nakshatra, details{} (each karaka: planet, rashi,\n  nakshatra, longitude) }\nishta_devata.data — { atmakaraka, karakamsha_lagna,\n  karakamsha_lagna_index, jivanmuktamsa_planet, navamsa_lagna,\n  navamsa_lagna_index, twelfth_house_sign, twelfth_house_index,\n  planets_in_12th[], ishta_devta_planet, deity, description, method,\n  d9_positions{} (each planet: sign, sign_num) }\n\nEdge case: if two planets share the exact same degree, tie-breaking\nfollows classical highest-degree-wins rule from raw ecliptic longitude.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nThis is a spiritual tool, not a predictive one. Do not call for\ntiming, health, career, or matchmaking analysis.",
        annotations=STANDARD_ANNOTATIONS,
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
        description='Reference lookup for any of the 27 nakshatras by name — returns\nruling planet, deity, symbol, Gana, Varna, Yoni, Nadi, pada meanings,\nclassical qualities, profession guidance, life themes, favorable and\nunfavorable activities, and body map. No birth data required.\nSource: Vedanga Jyotisha and classical nakshatra texts.\n\nAccepted nakshatra names: Ashwini, Bharani, Krittika, Rohini,\nMrigashira, Ardra, Punarvasu, Pushya, Ashlesha, Magha, Purva Phalguni,\nUttara Phalguni, Hasta, Chitra, Swati, Vishakha, Anuradha, Jyeshtha,\nMula, Purva Ashadha, Uttara Ashadha, Shravana, Dhanishtha, Shatabhisha,\nPurva Bhadrapada, Uttara Bhadrapada, Revati. Total: 27.\n\nOUTPUT CONTRACT (response_format=json):\ndata.name, data.index (int 0–26)\ndata.interpretation — { source, nakshatra_number, name, sanskrit,\n  span, symbol, deity, ruling_planet, sign, sign_lord, gana, nature,\n  body_part, classical_qualities[], appearance{ classical, modern },\n  nature_description{ classical, modern }, profession{ primary[],\n  secondary[], classical_note, modern }, life_themes{ core,\n  karmic_path, challenge, gift, modern }, keywords[], strengths[],\n  challenges[] }\ndata.activities — { favorable_activities[], unfavorable_activities[] }\ndata.body_map — { parts[], sensitivity }\n\nERROR CONTRACT: Unknown or misspelled nakshatra name → HTTP 404.\nNo fuzzy matching. Exact name match required.',
        annotations=STANDARD_ANNOTATIONS,
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
        description="Check Sade Sati status — Saturn's 7.5-year transit through the sign\nbefore, the sign of, and the sign after the natal Moon. Always computed\nfor today's date — not configurable for past or future.\n\nOUTPUT CONTRACT (response_format=json):\ndata.natal_moon_sign (English name, e.g. 'Libra')\ndata.natal_moon_sign_index (int 0–11)\ndata.sade_sati_signs — { rising (English), peak (English),\n  setting (English) }\ndata.is_currently_active (bool)\ndata.current_phase (string: 'rising', 'peak', 'setting', or null)\ndata.current_phase_description (string or null)\ndata.intensity_score (int 0–10)\ndata.intensity_label (string: 'low', 'moderate', 'high')\ndata.next_sade_sati — { starts (YYYY-MM-DD), phase, years_away (float) }\ndata.all_periods[] — historical and future periods, each:\n  sade_sati_number, overall_start (YYYY-MM-DD), overall_end,\n  duration_years, phases: { rising, peak, setting } — each:\n  name, description, start, end, saturn_sign, intensity\ndata.mitigated_by_own_sign (bool)\ndata.mitigated_by_exaltation (bool)\ndata.classical_note (string)\n\nSign names in this response are English ('Libra'), not Sanskrit.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not use asterwise_get_gochar for this — Gochar shows all transits;\nthis focuses exclusively on Saturn's Moon transit with full phase and\nintensity detail.",
        annotations=STANDARD_ANNOTATIONS,
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
        description='Generate a Prashna (horary) chart for a question asked at this moment.\nPlanetary positions at the time and place the question is asked are\nused to answer the question — no birth data required.\nSource: Prashna Marga and classical horary texts.\n\nValid question categories: self, wealth, siblings, property, children,\nhealth, marriage, death, travel, career, gains, loss.\n\nOUTPUT CONTRACT: Schema not yet confirmed from live response —\nendpoint was recently fixed. Expected response contains the horary\nchart data (planetary positions for the question moment) plus a\nquestion interpretation or verdict.\n\nERROR CONTRACT: Empty question → 422. Invalid date/time format → 422.\nCoordinates out of range → 422.\n\nDo not use for ongoing life analysis — use asterwise_get_natal_chart\nfor personal natal analysis.',
        annotations=STANDARD_ANNOTATIONS,
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
        name="asterwise_get_varshaphal",
        description="Calculate the Varshaphal (Solar Return) chart — cast for the exact\nmoment the Sun returns to its natal sidereal longitude each year.\n\nCRITICAL PARAMETER: year = the 4-digit calendar year (e.g. 2026),\nNOT the person's age. Passing age (e.g. 40) instead of year will\nproduce a chart for the wrong year and return incorrect results.\nSame warning applies to asterwise_generate_varshaphal_report.\n\nOUTPUT CONTRACT (response_format=json):\ndata.target_year, data.ayanamsa, data.solar_return_utc (ISO),\ndata.solar_return_jd, data.natal_sun_longitude, data.natal_lagna,\ndata.natal_lagna_index, data.year_lord\ndata.muntha — { rashi_index, rashi, age_years, muntha_lord }\ndata.planets{} — object keyed by planet (Sun through Ketu):\n  longitude, rashi_index, rashi, degree, is_retrograde, speed\ndata.varshaphal_ascendant_longitude\ndata.varsha_pati — { planet, role, pancha_vargeeya_bala, kshetra_bala,\n  uchcha_bala, election_used_strongest_without_aspect }\ndata.pancha_adhikaris[] — 5 objects: role, planet,\n  pancha_vargeeya_bala, kshetra_bala, uchcha_bala, hadda_bala,\n  dreshkana_bala, navamsa_bala, pending_components_note,\n  aspects_ascendant, tajika_aspect_angles_matched[], separation_from_asc_deg\ndata.pancha_vargeeya_bala{} — keyed by role\ndata.tajika_aspects[] — per Pancha Adhikari\ndata.tajika_planet_pairs[] — all planet pairs: planet_a, planet_b,\n  house_a, house_b, diff_ab, diff_ba, aspect_ab, aspect_ba,\n  is_ithsala, is_musaripha, faster_planet, orb_degrees\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not confuse with asterwise_get_dasha (lifetime cycles) or\nasterwise_get_transits (transit events over a date range).",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_varshaphal(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat
    ) -> str:
        """Varshaphal solar return."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "target_year": year}
            data = await get_client().post("/v1/astro/varshaphal", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Varshaphal ({year})", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_varshaphal", exc)

    @mcp.tool(
        name="asterwise_get_lal_kitab_chart",
        description="Get the Lal Kitab chart — a North Indian astrological tradition with\nits own distinct house placement rules, planet interpretation, and\ndebt (Rin) analysis. Structurally different from BPHS.\nSource: Lal Kitab (1952 edition).\n\nOUTPUT CONTRACT (response_format=json):\ndata.system ('lal_kitab'), data.ayanamsa\ndata.planets{} — keyed by planet (Sun through Ketu):\n  longitude, rashi_index, rashi, lk_house (int 1–12),\n  house_lord, is_retrograde, pucca_ghar (bool — strong/permanent\n  placement), kachcha_ghar (bool — weak placement), uchcha (bool),\n  neecha (bool), pucca_house (int), kachcha_house (int)\ndata.houses{} — keyed by '1'–'12':\n  house (int), rashi_index, rashi, lord, occupants[] (planet names),\n  signification (string), has_benefic (bool), has_malefic (bool)\ndata.rin_analysis — { pitru_rin, matru_rin, bhai_rin, stri_rin,\n  dev_rin (all bool), active_rins[] (string array), rin_remedies[]\n  (each: rin, planet, totka) }\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nCRITICAL: Do not mix Lal Kitab placements with BPHS interpretations\n— they use different logic and combining them produces incorrect\nanalysis. Use only when the user explicitly asks for Lal Kitab.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Get Lal Kitab remedies — practical household-level prescriptions\n(Totkas) including Rin clearance rituals, specific charity actions,\nhousehold objects to keep or avoid, and planetary appeasement. Use\nafter asterwise_get_lal_kitab_chart. Source: Lal Kitab (1952 edition).\n\nOUTPUT CONTRACT (response_format=json):\ndata.system ('lal_kitab'), data.ayanamsa\ndata.remedies[] — one object per planet requiring attention:\n  planet, lk_house, rashi, pucca_ghar, kachcha_ghar, uchcha,\n  neecha, priority ('high', 'medium', or 'low'),\n  remedies[] — each: type ('remedy', 'donation', 'keep', or 'avoid'),\n  action (string instruction)\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not use as replacement for asterwise_get_remedies — that provides\nBPHS/Parashari remedies (mantras, gemstones). Lal Kitab remedies are\na completely separate system.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Get the KP (Krishnamurti Paddhati) chart — a precision horary and\nnatal system that subdivides each nakshatra into sub-lords using\nVimshottari proportions. Returns planet positions with star lord and\nsub-lord chains, plus all 12 house cusps.\nSource: K.S. Krishnamurti's KP system.\n\nIMPORTANT: Use ayanamsa='kp' (KP Ayanamsa) for this tool — not\n'lahiri'. KP calculations require the KP-specific ayanamsa for correct\nsub-lord assignments.\n\nIMPORTANT: KP requires highly accurate birth time. For unknown birth\ntime (time='00:00'), sub-lord chains will be computed from midnight\nand will be unreliable for event prediction.\n\nOUTPUT CONTRACT (response_format=json):\ndata.ayanamsa ('kp')\ndata.lagna — { rashi, rashi_index, longitude, nakshatra_lord, sub_lord }\ndata.planets{} — keyed by planet (Sun through Ketu):\n  longitude, rashi_index, rashi, degree, is_retrograde, house (int),\n  nakshatra_index (int 0–26), nakshatra_lord, sub_lord\ndata.house_cusps{} — keyed by '1'–'12':\n  longitude, rashi_index, rashi, nakshatra_lord, sub_lord\n\nUse asterwise_get_kp_significators after this to get house-wise\nevent indicators.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nKP is for event prediction with yes/no precision. BPHS (asterwise_get_natal_chart)\nis for character and life theme analysis. Do not mix the two systems.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Get KP house significators — for each house (or a specific house 1–12),\nthe chain of planets that signify its matters through occupants,\nstar-lords of occupants, and nakshatra-lords of the house lord.\nSource: KP system. Use after asterwise_get_kp_chart.\n\nhouse_number: omit to get all 12 houses; specify an int 1–12 to get\none house. Values outside 1–12 are rejected with 422.\n\nOUTPUT CONTRACT (response_format=json):\ndata.ayanamsa ('kp')\ndata.significators{} — keyed by house number string '1'–'12':\n  house (int), sign_lord, occupants[] (planet names),\n  nak_of_occupants[] (nakshatra lords of occupants),\n  nak_of_lord[] (nakshatra lords of the house sign lord),\n  all_significators[] (union of above)\ndata.planet_significators{} — keyed by planet name:\n  tier1_houses[] (houses where planet is occupant),\n  tier2_houses[] (houses where planet's nakshatra lord is occupant),\n  tier3_houses[] (houses where planet is star lord of occupant),\n  tier4_houses[] (houses where planet is nakshatra lord of sign lord),\n  all_significators[] (union of all tiers)\n\nERROR CONTRACT: house_number outside 1–12 → 422.",
        annotations=STANDARD_ANNOTATIONS,
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
        description="Get the KP ruling planets for the current moment at a given location —\nthe Moon's sign lord, star lord, and sub lord; plus the Ascendant's\nsign lord, star lord, and sub lord (6 total). These govern the moment\nand are used in KP to validate charts and time events.\nSource: KP ruling planets method.\n\nTakes lat and lon only — NOT birth data. This tool is about the\ncurrent moment, not a natal chart.\n\nOUTPUT CONTRACT (response_format=json):\ndata.ayanamsa ('kp')\ndata.target_utc (ISO UTC datetime of computation)\ndata.day_lord (planet name)\ndata.moon — { longitude, rashi, sign_lord, nakshatra_lord, sub_lord }\ndata.ascendant — { longitude, rashi, sign_lord, nakshatra_lord, sub_lord }\ndata.ruling_planets[] (string array of unique ruling planet names,\n  deduplicated)\n\nERROR CONTRACT: Coordinates out of range → 422.\n\nFor natal KP analysis use asterwise_get_kp_chart.\nFor house signification use asterwise_get_kp_significators.",
        annotations=STANDARD_ANNOTATIONS,
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
        description='Calculate Ashtakavarga — transit receptivity scoring derived from\nthe natal chart. Call asterwise_get_natal_chart first.\nSource: BPHS Ashtakavarga chapters.\n\nOUTPUT CONTRACT (response_format=json):\ndata.bhinna — object keyed by planet (Sun, Moon, Mars, Mercury,\n  Jupiter, Venus, Saturn, Lagna). Each value is a 12-element int\n  array indexed by rashi (Mesha=0 to Meena=11), showing Bindu count\n  (0–8) for that planet in each sign.\ndata.bhinna_after_trikona — same structure, 7 planets (no Lagna),\n  after Trikona reduction\ndata.bhinna_after_ekadhipatya — same, after Ekadhipatya reduction\ndata.sarva[] — 12-element int array, combined Sarvashtakavarga\n  per rashi. 28+ Bindus = strong transit support; below 25 = difficulty.\ndata.sarva_reduced[] — 12-element int array, after Trikona reduction\ndata.after_trikona[] — 12-element int array\ndata.after_ekadhipatya[] — 12-element int array\ndata.birth_time_unknown (bool)\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nDo not confuse with asterwise_get_chart_strength — Shadbala measures\nnatal planetary strength; Ashtakavarga measures transit receptivity.',
        annotations=STANDARD_ANNOTATIONS,
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

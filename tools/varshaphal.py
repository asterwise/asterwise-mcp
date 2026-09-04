"""Varshaphal (Tajika annual solar return) MCP tools."""

from __future__ import annotations

from fastmcp import Context, FastMCP
import mcp.types as mcp_types

from client import get_client
from models import BirthData, ResponseFormat
from runtime import (
    compact_description,
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_varshaphal",
        title="Varshaphal",
        description=compact_description("asterwise_get_varshaphal", "Computes the annual Tajika-style solar return for a four-digit civil year and returns Muntha, Pancha Adhikari metrics, Tajika aspects, and varshaphal positions.\n\nSECTION: WHAT THIS TOOL COVERS\nVarshaphal engine: solar return instant, year lord, muntha block, varsha pati election, five pancha adhikaris with bala components, tajika aspect arrays, and pairwise Tajika geometry including ithsala/musaripha flags. year must mean calendar year (e.g. 2026), not biological age — not enforced locally; wrong integers chart the wrong annual return. Not lifetime Vimshottari (asterwise_get_dasha) nor generic transit ingress lists (asterwise_get_transits).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — baseline radix before annual overlay.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nyear is a plain int sent as target_year upstream; callers must supply the true Gregorian return year, not age.\n\nSECTION: OUTPUT CONTRACT\ndata.target_year (int)\ndata.ayanamsa (string)\ndata.solar_return_utc (string — ISO)\ndata.solar_return_jd (float)\ndata.natal_sun_longitude (float)\ndata.natal_lagna (string)\ndata.natal_lagna_index (int)\ndata.year_lord (string — planet name)\ndata.muntha:\n  rashi_index (int)\n  rashi (string)\n  age_years (float)\n  muntha_lord (string)\ndata.planets{} — keys Sun..Ketu:\n  longitude (float)\n  rashi_index (int)\n  rashi (string)\n  degree (float)\n  is_retrograde (bool)\n  speed (float)\ndata.varshaphal_ascendant_longitude (float)\ndata.varshaphal_ascendant_sign (string — Sanskrit sign name derived from the ascendant longitude)\ndata.varshaphal_ascendant_sign_index (int — sign index 0-11, where 0=Mesha and 11=Meena)\ndata.varsha_pati:\n  planet (string)\n  role (string)\n  pancha_vargeeya_bala (float)\n  kshetra_bala (float)\n  uchcha_bala (float)\n  election_used_strongest_without_aspect (bool)\ndata.pancha_adhikaris[] — five objects:\n  role (string)\n  planet (string)\n  pancha_vargeeya_bala, kshetra_bala, uchcha_bala, hadda_bala, dreshkana_bala, navamsa_bala (floats)\n  pending_components_note (string)\n  aspects_ascendant (bool)\n  tajika_aspect_angles_matched[] (array)\n  separation_from_asc_deg (float)\ndata.pancha_vargeeya_bala{} — keyed by role (float values)\ndata.tajika_aspects[] — per Pancha Adhikari (structure per upstream)\ndata.tajika_planet_pairs[] — each:\n  planet_a, planet_b (strings)\n  house_a, house_b (int)\n  diff_ab, diff_ba (float)\n  aspect_ab, aspect_ba (strings or floats per upstream)\n  is_ithsala (bool)\n  is_musaripha (bool)\n  faster_planet (string)\n  orb_degrees (float)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — year not range-checked here.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Feeding age instead of civil year silently mis-orients the return — caller responsibility.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dasha — multi-decade Vimshottari, not one solar return.\nasterwise_get_transits — ingress/station timeline, not annual Tajika chart."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_varshaphal(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Varshaphal solar return."""
        async with tool_guard("asterwise_get_varshaphal"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "target_year": year}
            data = await get_client().post("/v1/astro/varshaphal", api_key, body, timeout=20.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Varshaphal ({year})", d),
            )
    @mcp.tool(
        name="asterwise_get_varshaphal_saham",
        title="Varshaphal Saham",
        description=compact_description("asterwise_get_varshaphal_saham", "Computes all 10 Tajika Saham (sensitive points) for a Varshaphal solar return chart. Sahams are the Tajika equivalent of Arabic Parts — mathematically derived zodiac points that focus the annual horoscope on specific life themes.\n\nSECTION: WHAT THIS TOOL COVERS\nSaham formula: (A - B + Ascendant) % 360, with a conditional +30° correction applied when the Ascendant does not fall in the forward zodiacal arc from B to A. This conditional is the defining classical Tajika Saham rule — without it, results are wrong. Day and night formulas differ: the Minuend and Subtrahend swap based on whether the solar return falls during daytime or nighttime at the birth location. Punya Saham (Fortune) is always computed first because Yashas (Fame) and Mahatmya (Status) use it as an operand. The Saham lord (planet ruling the sign where the Saham falls) is the Sahamesha — its strength, house placement, and Tajika aspects to the Varsha Ascendant determine whether the theme manifests positively or is obstructed.\n\n10 Sahams returned:\n  punya — Fortune and Luck (Moon-Sun day / Sun-Moon night)\n  vidya — Education and Learning (Sun-Jupiter day)\n  yashas — Fame and Reputation (Jupiter-Punya day) — uses Punya as operand\n  mitra — Friends and Allies (Jupiter-Venus day)\n  mahatmya — Greatness and Status (Punya-Mars day) — uses Punya as operand\n  asha — Desires and Fulfillment (Saturn-Venus day)\n  karmakarya — Action and Profession (Mars-Mercury day)\n  vyapara — Business and Trade (Mars-Saturn day)\n  vivaha — Marriage and Relationships (Venus-Saturn day)\n  santapa — Sorrow and Stress (Saturn-Moon day)\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_varshaphal — understand the base solar return chart (year lord, Muntha, Varsha Ascendant) before interpreting Saham lords. The Saham is meaningless without knowing which house it occupies from the Varsha Ascendant.\nAFTER: asterwise_get_varshaphal_harsha_bala — assess the Saham lord's positional happiness score to determine ease or difficulty of manifestation.\n\nSECTION: INPUT CONTRACT\nSame as asterwise_get_varshaphal — BirthData plus target_year.\ntarget_year (required int): The Gregorian calendar year of the solar return. Not age — the civil year (e.g. 2026). Feeding age instead of year silently produces the wrong return.\ntime (required): Solar return Ascendant is time-sensitive. Accurate birth time is required for reliable Saham interpretation.\n\nSECTION: OUTPUT CONTRACT\ndata.target_year (int — calendar year of the solar return)\ndata.ayanamsa (string — ayanamsa system used, e.g. 'lahiri')\ndata.solar_return_utc (string — ISO UTC timestamp of solar return moment)\ndata.is_day_return (bool — true if solar return occurs between sunrise and sunset; determines which Saham formula variant is used)\ndata.varshaphal_ascendant_longitude (float — Varsha Ascendant in degrees; all 10 Saham longitudes are computed relative to this)\ndata.total (int — always 10)\ndata.sahams[] — 10 objects in order [punya, vidya, yashas, mitra, mahatmya, asha, karmakarya, vyapara, vivaha, santapa]:\n  slug (string — lowercase key, e.g. 'punya')\n  name (string — full display name, e.g. 'Punya Saham')\n  theme (string — life area, e.g. 'Fortune and Luck')\n  longitude (float — Saham longitude in degrees 0–360)\n  rashi_index (int — 0–11, 0=Mesha)\n  rashi (string — Sanskrit sign name, e.g. 'Mesha')\n  degree_in_sign (float — degrees within the sign)\n  saham_lord (string — classical lord of the sign where Saham falls)\n  formula_used (string — describes whether day or night formula was applied and which planets were operands, e.g. 'day: Moon - Sun + Asc')\n (string — methodology note)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nSLOW_COMPUTE — internally runs the full solar return computation (binary-search Sun longitude + house computation) before deriving Sahams.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call): None — BirthData Pydantic only.\nINVALID_PARAMS (upstream): None — upstream rejection surfaces as MCP INTERNAL_ERROR.\nINTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\nEdge cases:\n  — Day/night determination uses sunrise/sunset at the birth coordinates for the solar return date. Polar latitudes where sunrise cannot be computed → MCP INTERNAL_ERROR.\n  — target_year is a Gregorian year, not age — always verify the caller passes the civil year.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_varshaphal — returns the full base solar return chart including Muntha, year lord, and planet positions; Saham points are not included there.\nasterwise_get_varshaphal_harsha_bala — scores planet positional happiness; this tool computes zodiac points, not planet positions.\nasterwise_get_gemstone_recommendations — birthchart gemstone recommendations, unrelated to Tajika Saham."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_varshaphal_saham(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Compute Tajika Saham sensitive points for a Varshaphal solar return."""
        async with tool_guard("asterwise_get_varshaphal_saham"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "target_year": year}
            data = await get_client().post(
                "/v1/astro/varshaphal/saham", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Varshaphal Saham", d),
            )
    @mcp.tool(
        name="asterwise_get_varshaphal_harsha_bala",
        title="Varshaphal Harsha Bala",
        description=compact_description("asterwise_get_varshaphal_harsha_bala", "Computes Harsha Bala (positional happiness score) for all 7 classical planets in a Varshaphal solar return chart. Maximum 20 per planet (4 components × 5 points each).\n\nSECTION: WHAT THIS TOOL COVERS\nHarsha Bala is entirely distinct from Pancha Vargeeya Bala. Pancha Vargeeya Bala measures mathematical strength (sign dignity, exaltation arc, divisional chart fractions). Harsha Bala measures whether a planet is positionally comfortable — does it occupy the right house, sign, hemisphere, and return type for its nature? A planet with high Pancha Vargeeya Bala (60/80) but zero Harsha Bala has the capacity to deliver results, but does so through stress, delay, and frustration. A Year Lord (Varsha Pati) with 0 Harsha Bala signals a difficult year even when it wins the Pancha Adhikari election.\n\n4 Components (5 points each, maximum 20):\n1. STHANA — Happy house placement in the Varsha chart (measured from Varsha Ascendant, not natal Ascendant):\n   Sun=9th, Moon=3rd, Mars=6th, Mercury=1st, Jupiter=11th, Venus=5th, Saturn=12th.\n2. SWAKSHETRA/UCCHA — Planet in its own sign (Swakshetra) or sign of exaltation (Uccha).\n3. PUM-STRI (Gender/Hemisphere) — Male planets (Sun, Mars, Jupiter) prefer houses 7–12 (visible hemisphere). Female planets (Moon, Venus, Saturn) prefer houses 1–6 (invisible hemisphere). Mercury earns this component unconditionally.\n4. DINA-RATRI (Day/Night) — Male planets (Sun, Mars, Jupiter) prefer a daytime solar return. Female planets (Moon, Venus, Saturn) prefer a nighttime return. Mercury earns this component unconditionally.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_varshaphal — identify the Year Lord (Varsha Pati) before interpreting Harsha Bala. The Year Lord's Harsha Bala is the most actionable number in this response.\nAFTER: asterwise_get_varshaphal_saham — use Harsha Bala to assess whether each Saham lord can deliver its theme with ease or difficulty.\n\nSECTION: INPUT CONTRACT\nSame as asterwise_get_varshaphal — BirthData plus target_year.\ntarget_year (required int): The Gregorian civil year of the solar return. Not age.\ntime (required): Solar return ascendant and house positions are time-sensitive.\n\nSECTION: OUTPUT CONTRACT\ndata.target_year (int)\ndata.ayanamsa (string)\ndata.solar_return_utc (string — ISO UTC of solar return moment)\ndata.is_day_return (bool — true if solar return falls between sunrise and sunset; directly determines Dina-Ratri component results for all planets)\ndata.varshaphal_ascendant_longitude (float — Varsha Ascendant in degrees; all house placements are measured from this)\ndata.planets[] — 7 objects (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn in that order):\n  planet (string — planet name)\n  harsha_bala (int — total score 0–20)\n  max_harsha_bala (int — always 20)\n  varsha_house (int — planet's house in the Varsha chart, 1–12, from Varsha Ascendant)\n  rashi_index (int — 0–11, 0=Mesha)\n  rashi (string — Sanskrit sign name)\n  components{} — four keys:\n    sthana{}: earned (bool), points (int — 0 or 5), happy_house (int), actual_house (int), description (string)\n    swakshetra_uccha{}: earned (bool), points (int — 0 or 5), in_own_sign (bool), in_exaltation (bool), current_rashi_index (int)\n    pum_stri{}: earned (bool), points (int — 0 or 5), gender (string — 'male'|'female'|'neutral'), happy_hemisphere (string), actual_house (int)\n    dina_ratri{}: earned (bool), points (int — 0 or 5), happy_period (string), actual_period (string — 'day' or 'night')\n  interpretation (string — qualitative label: 'Excellent', 'Strong', 'Moderate', 'Weak', or 'Very weak')\n (string — methodology and interpretation guidance)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nSLOW_COMPUTE — internally runs the full solar return computation before deriving Harsha Bala.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call): None — BirthData Pydantic only.\nINVALID_PARAMS (upstream): None — upstream rejection surfaces as MCP INTERNAL_ERROR.\nINTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\nEdge cases:\n  — Rahu and Ketu are excluded — Harsha Bala is defined only for the 7 classical grahas.\n  — Polar latitudes where sunrise/sunset cannot be computed affect is_day_return → MCP INTERNAL_ERROR.\n  — target_year is a Gregorian year, not age.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_varshaphal — returns Pancha Vargeeya Bala (mathematical strength out of 80) for the Pancha Adhikaris; Harsha Bala (positional happiness out of 20) is a completely different measurement returned by this tool.\nasterwise_get_varshaphal_saham — derives sensitive zodiac points; this tool scores planet positional comfort.\nasterwise_get_chart_strength — Shadbala for the natal chart, not Tajika Harsha Bala for the solar return."),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_varshaphal_harsha_bala(
        ctx: Context,
        birth: BirthData,
        year: int,
        response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    ) -> str:
        """Compute Harsha Bala positional happiness scores for a Varshaphal solar return."""
        async with tool_guard("asterwise_get_varshaphal_harsha_bala"):
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "target_year": year}
            data = await get_client().post(
                "/v1/astro/varshaphal/harsha-bala", api_key, body, timeout=20.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Varshaphal Harsha Bala", d),
            )
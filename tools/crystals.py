"""Crystal database MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from mcp.shared.exceptions import McpError
import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import BirthData, ResponseFormat
from runtime import (
    format_tool_result,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_crystals",
        title="Crystals Catalogue",
        description="Returns all 50 crystals in the database sorted alphabetically. Each entry includes chakra associations, elemental correspondences, Vedic and Western planetary assignments, physical/emotional/spiritual healing properties, geographic origins, affirmations, and safety cautions.\n\nSECTION: WHAT THIS TOOL COVERS\nDual-tradition crystal database distinguishing classical Vedic assignments from modern Western metaphysical ones. vedic_correspondence field is always one of: 'navaratna' (primary classical gem — one of the nine planetary gems), 'uparatna' (classical substitute gem), or 'none_classical' (no Vedic text assigns this stone — Western tradition only). The nine Navaratna: Ruby (Sun), Pearl (Moon), Red Coral (Mars), Emerald (Mercury), Yellow Sapphire (Jupiter), Diamond / White Sapphire (Venus), Blue Sapphire (Saturn), Hessonite Garnet (Rahu), Cat's Eye Chrysoberyl (Ketu). Crystals like Labradorite and Amazonite are marked none_classical — they were unknown in ancient India. Does not compute natal chart recommendations (asterwise_get_crystal_recommendations).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone catalogue.\nAFTER: asterwise_get_crystal_by_planet — filter by Vedic planet for remedial use.\n\nSECTION: INPUT CONTRACT\nNo required parameters.\n\nSECTION: OUTPUT CONTRACT\ndata.total (int — 50)\ndata.crystals[] — 50 objects each:\n  slug, name, colors[], hardness_mohs (float)\n  chakras[] (string array)\n  element (string)\n  zodiac_signs[] (string array)\n  vedic_planet (string or null)\n  vedic_correspondence (string — 'navaratna'|'uparatna'|'none_classical')\n  western_planet (string or null)\n  keywords[] (string array)\n  healing_physical, healing_emotional, healing_spiritual (strings)\n  description (string)\n  origins[] (string array)\n  affirmation (string)\n  caution (string or null)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — full 50-crystal array. response_format=markdown — formatted catalogue. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP — static database, no ephemeris.\n\nSECTION: ERROR CONTRACT\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_crystal — single crystal detail by name.\nasterwise_get_crystal_by_planet — filter by Vedic planetary correspondence.\nasterwise_get_crystal_recommendations — recommendations by zodiac/chakra/intention.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_crystals(
        ctx: Context,
        response_format: ResponseFormat,
    ) -> str:
        """Get complete crystal database."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get("/v1/crystals", api_key, timeout=15.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Crystal Database", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_crystals", exc)

    @mcp.tool(
        name="asterwise_get_crystal",
        title="Crystal Lookup",
        description="Lookup a specific crystal by slug or name (case-insensitive). Returns full detail including dual Vedic/Western planetary assignments, all healing properties, and any safety cautions.\n\nSECTION: WHAT THIS TOOL COVERS\nReturns one crystal entry from the 50-crystal database. Accepts URL-safe slugs (e.g. 'blue-sapphire', 'rose-quartz') or display names (e.g. 'Blue Sapphire', 'Rose Quartz'). The caution field carries critical safety information — Blue Sapphire and Hessonite Garnet carry CRITICAL cautions about Jyotish use without qualified practitioner assessment. Malachite has a CRITICAL toxicity caution. Always surface the caution field to end users.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone or after asterwise_get_gemstone_recommendations.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nname: Crystal slug or display name. Examples: 'amethyst', 'blue-sapphire', 'Cat's Eye Chrysoberyl'\n\nSECTION: OUTPUT CONTRACT\nSame shape as each crystal in asterwise_get_crystals — full single crystal object.\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — single crystal object. response_format=markdown — formatted detail card. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Unknown crystal name → 404, surfaces as MCP INTERNAL_ERROR.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_crystals — full 50-crystal catalogue.\nasterwise_get_crystal_by_planet — all crystals for a Vedic planet.\nasterwise_get_gemstone_recommendations — natal chart-based gem recommendations (house lordship rules), different from this database.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_crystal(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Lookup a specific crystal by slug or name."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                f"/v1/crystals/{safe_segment(name)}",
                api_key,
                timeout=15.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Crystal: {name}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_crystal", exc)

    @mcp.tool(
        name="asterwise_get_crystal_by_planet",
        title="Crystals by Planet",
        description="Returns all crystals associated with a specific Vedic planet. Results are sorted with primary Navaratna gems first, then Uparatna substitutes. Only Navaratna and Uparatna Vedic assignments are returned — crystals with no Vedic planetary correspondence are excluded.\n\nSECTION: WHAT THIS TOOL COVERS\nFilters the crystal database by vedic_planet field. Only returns crystals where vedic_correspondence is 'navaratna' or 'uparatna' — none_classical crystals are not returned here because they have no actual Vedic planetary assignment. Useful for Jyotish practitioners recommending remedial gems. Navaratna gems appear first. Valid planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — identify the planet needing remediation.\nAFTER: asterwise_get_gemstone_recommendations — for chart-specific gem safety assessment.\n\nSECTION: INPUT CONTRACT\nplanet: One of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu.\n\nSECTION: OUTPUT CONTRACT\ndata.total (int)\ndata.crystals[] — same shape as asterwise_get_crystals, sorted Navaratna first.\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — filtered crystal array. response_format=markdown — formatted list. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): Unknown planet → 404.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gemstone_recommendations — natal chart house-lordship gem recommendation with contraindications; use for actual gem prescription, not just listing.\nasterwise_get_crystals — all 50 crystals including Western-only ones.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_crystal_by_planet(
        ctx: Context,
        planet: str,
        response_format: ResponseFormat,
    ) -> str:
        """Get crystals associated with a Vedic planet."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                f"/v1/crystals/by-planet/{safe_segment(planet)}",
                api_key,
                timeout=15.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Crystals for {planet}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_crystal_by_planet", exc)

    @mcp.tool(
        name="asterwise_get_crystal_recommendations",
        title="Crystal Recommendations",
        description="Recommends crystals based on zodiac sign, chakra, or intention keyword. At least one filter is required. Returns crystals that match the most criteria first.\n\nSECTION: WHAT THIS TOOL COVERS\nScoring: zodiac match scores 3, chakra match scores 2, keyword match scores 1. Crystals matching multiple filters rank highest. Returns up to limit results (default 5, max 20). Valid chakras: Root, Sacral, Solar Plexus, Heart, Throat, Third Eye, Crown. Valid zodiac signs: English Western zodiac names (Aries, Taurus, etc.). Intention keyword is matched against each crystal's keywords[] list (partial match). Not a Jyotish prescription — does not account for natal chart or planetary periods. For chart-based gem prescription use asterwise_get_gemstone_recommendations.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone for consumer apps.\nAFTER: asterwise_get_crystal — get full detail on any recommended crystal.\n\nSECTION: INPUT CONTRACT\nAt least one of: zodiac_sign, chakra, intention must be provided.\nzodiac_sign (optional): English zodiac sign, e.g. 'Taurus', 'Scorpio'.\nchakra (optional): One of Root, Sacral, Solar Plexus, Heart, Throat, Third Eye, Crown.\nintention (optional): Keyword string, e.g. 'protection', 'abundance', 'love'.\nlimit (optional int, default 5, max 20): Maximum results to return.\n\nSECTION: OUTPUT CONTRACT\ndata.total (int — number returned)\ndata.filters_applied{} — the filters used\ndata.crystals[] — matched crystals sorted by score descending\n\nSECTION: RESPONSE FORMAT\nresponse_format=json — recommendation object. response_format=markdown — formatted recommendations. Both return identical data.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (upstream): No filters provided → 422. Invalid chakra name → 422.\nINTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_crystal_by_planet — Vedic planet filter only.\nasterwise_get_gemstone_recommendations — natal chart house-lordship gem prescription with contraindications.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_crystal_recommendations(
        ctx: Context,
        response_format: ResponseFormat,
        zodiac_sign: str | None = None,
        chakra: str | None = None,
        intention: str | None = None,
        limit: int = 5,
    ) -> str:
        """Get crystal recommendations by zodiac, chakra, or intention."""
        try:
            api_key = await require_api_key(ctx)
            body: dict[str, Any] = {"limit": limit}
            if zodiac_sign:
                body["zodiac_sign"] = zodiac_sign
            if chakra:
                body["chakra"] = chakra
            if intention:
                body["intention"] = intention
            data = await get_client().post(
                "/v1/crystals/recommend", api_key, body, timeout=15.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Crystal Recommendations", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_crystal_recommendations", exc)

    @mcp.tool(
        name="asterwise_get_crystal_recommendations_natal",
        title="Natal Crystal Recommendations",
        description="Recommends crystals from a Vedic natal chart using house lordship rules for gem selection. This is the only API that derives crystal recommendations from a computed natal chart — not from zodiac sign or chakra preference.\n\nSECTION: WHAT THIS TOOL COVERS\nClassical rules applied:\n\n1. INCLUSION RULE — A planet is recommended only if it lords at least one Trikona house (1st, 5th, or 9th). If a planet lords both a Trikona and a Dusthana (6th, 8th, or 12th), the Trikona lordship prevails and the planet is still recommended. This is the dual-lordship rule — violating it produces wrong exclusions.\n\n2. EXCLUSION RULE — A planet that does not lord any Trikona house is contraindicated. This includes pure Dusthana lords, pure Kendra lords (4th, 7th, 10th), and pure neutral lords.\n\n3. SCORING — Crystals are scored by which Trikona lordship their planet holds:\n   Lagna lord (1st) Navaratna +5, Uparatna +4 — primary Life Stone\n   Yogakaraka Navaratna +5, Uparatna +4 — lords both a non-1st Kendra AND a non-1st Trikona simultaneously\n   9th lord Navaratna +4, Uparatna +3 — Fortune Stone (Bhagyesh)\n   5th lord Navaratna +3, Uparatna +2 — Lucky Stone (Panchamesh)\n\n4. YOGAKARAKA — A planet that lords both a non-1st Kendra (4th, 7th, or 10th) AND a non-1st Trikona (5th or 9th) is the supreme benefic for that Lagna. Example: Mars for Cancer Lagna (lords 5th and 10th).\n\n5. DANGEROUS COMBINATIONS — Pairs of recommended crystals from enemy planet camps are flagged in warnings[]: Saturn+Sun, Saturn+Mars, Jupiter+Venus, Moon+Rahu, Moon+Ketu.\n\n6. CLASSICAL VEDIC ONLY — Crystals with vedic_correspondence='none_classical' (Labradorite, Amazonite, Black Obsidian, etc.) are never returned. These stones have no Vedic planetary assignment in the database.\n\nSECTION: WORKFLOW\nBEFORE: None — this tool internally computes the natal chart. No separate natal chart call required.\nAFTER: asterwise_get_crystal — get full detail (hardness, origins, affirmation, full caution text) on any recommended crystal by slug.\nAFTER: asterwise_get_remedies — broader classical remedial programme alongside gem recommendations.\n\nSECTION: INPUT CONTRACT\nStandard BirthData (date, time, lat, lon, timezone, ayanamsa). Defaults to Lahiri ayanamsa.\ntime (required): Ascendant (Lagna) is time-sensitive. Inaccurate birth time changes the Lagna → changes all house lords → changes recommendations entirely.\n\nSECTION: OUTPUT CONTRACT\ndata.natal_context{} — chart factors used for recommendations:\n  lagna_sign (string — Ascendant sign in English, e.g. 'Libra')\n  lagna_lord (string — classical lord of the 1st house)\n  fifth_sign (string — 5th house sign in English)\n  fifth_lord (string — lord of the 5th house, Panchamesh)\n  ninth_sign (string — 9th house sign in English)\n  ninth_lord (string — lord of the 9th house, Bhagyesh)\n  yogakaraka (string or null — Yogakaraka planet name if one exists for this Lagna; null if none)\n  contraindicated_lords (string array — planets that do not lord any Trikona; their gems are contraindicated)\n  ayanamsa (string — ayanamsa used, e.g. 'lahiri')\ndata.total (int — number of crystals returned, up to 5)\ndata.crystals[] — recommended crystals sorted by match_score descending:\n  slug, name, colors[], hardness_mohs (float), chakras[], element, zodiac_signs[]\n  vedic_planet (string — the planet this crystal corresponds to)\n  vedic_correspondence (string — always 'navaratna' or 'uparatna'; none_classical never appears)\n  western_planet (string or null)\n  keywords[], healing_physical, healing_emotional, healing_spiritual, description\n  origins[], affirmation, caution (string or null — always surface this to end users)\n  match_score (int — house lordship score; higher indicates stronger lordship basis)\n  match_reasons (string array — which house lordship triggered this recommendation)\n  warnings (string array — dangerous combination warnings; may be empty)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE — full natal chart computation + crystal scoring pass.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call): BirthData Pydantic violations → MCP INVALID_PARAMS\nINVALID_PARAMS (upstream): Dates before 1800 or after 2100 → MCP INTERNAL_ERROR\nINTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\nEdge cases:\n  — An empty crystals[] is valid when no Navaratna or Uparatna Vedic gem corresponds to the Trikona lords of this specific chart.\n  — Blue Sapphire (Saturn) and Hessonite (Rahu) carry CRITICAL cautions in their caution field — always surface this to end users before advising wear.\n  — Rahu and Ketu do not own signs in the classical system — they never appear as lagna_lord, fifth_lord, or ninth_lord.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gemstone_recommendations — also a chart-based gem endpoint but uses a different engine (Atmakaraka + role-based prescription vs house lordship scoring); returns gem names not crystal database entries; does not include match_score or match_reasons.\nasterwise_get_crystal_recommendations — recommends crystals by zodiac sign, chakra, or intention keyword (no natal chart computation; Western metaphysical matching, not classical Jyotish).\nasterwise_get_crystal_by_planet — lists all crystals for a Vedic planet without house context — use this for reference, not prescription.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_crystal_recommendations_natal(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Get natal chart crystal recommendations from house lordship rules."""
        try:
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            data = await get_client().post(
                "/v1/crystals/recommend/natal", api_key, body, timeout=15.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Crystal Recommendations (Natal)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_crystal_recommendations_natal", exc)

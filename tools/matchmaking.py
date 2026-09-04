"""Matchmaking and compatibility (classical Ashtakoota and South Indian systems)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP


import mcp.types as mcp_types

from client import get_client
from models import BirthData, ResponseFormat
from runtime import (
    tool_guard,
    format_tool_result,
    require_api_key,
    structured_markdown,
)


def _ashtakoota_md(data: dict[str, Any]) -> str:
    lines = [
        "## Ashtakoota (Guna Milan)",
        "",
        "Rajju and Vedha are checked as independent classical conditions outside the Guna Milan score — read classical_vetoes before trusting the total score.",
        "",
    ]
    kootas = data.get("kootas") or data.get("ashtakoota") or data.get("guna")
    if isinstance(kootas, list):
        lines.append("| Koota | Score | Max | Notes |")
        lines.append("|-------|-------|-----|-------|")
        for row in kootas:
            if isinstance(row, dict):
                lines.append(
                    f"| {row.get('name', '—')} | {row.get('score', '—')} | "
                    f"{row.get('max', '—')} | {row.get('notes', '')} |"
                )
        lines.append("")
    for veto in ("rajju", "vedha"):
        if veto in data:
            lines.append(f"- **{veto.title()} veto**: {data[veto]}")
    lines.append("")
    lines.append(structured_markdown("Full compatibility payload", data))
    return "\n".join(lines)


def register(mcp: FastMCP) -> None:
    def _pair_body(p1: BirthData, p2: BirthData) -> dict[str, Any]:
        return {"person1": p1.to_api_dict(), "person2": p2.to_api_dict()}

    @mcp.tool(
        name="asterwise_get_compatibility",
        title="Ashtakoota Compatibility",
        description="Scores North Indian Ashtakoota (36-point Guna Milan) for two charts and returns koota breakdown, dosha flags, classical vetoes, mangal cross-check, and narrative guidance.\n\nSECTION: WHAT THIS TOOL COVERS\nImplements classical Ashtakoota with eight weighted kootas (Varna through Nadi), dosha booleans and cancellations, Rajju/Vedha veto objects, supplementary Mahendra and Stree Deergha checks, mangal compatibility, and a structured narrative. It is not Dashakoot (asterwise_get_dashakoot), Tamil Porutham (asterwise_get_porutham), or twelve-koota Thirumana (asterwise_get_thirumana_porutham).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart per person — understand charts before interpreting scores.\nAFTER: asterwise_get_papasamyam — optional malefic balance overlay.\n\nSECTION: INPUT CONTRACT\nTwo BirthData objects follow the global contract (unknown midnight time accepted without flag). All scoring is computed upstream from those payloads.\n\nSECTION: OUTPUT CONTRACT\ndata.total_score (float — out of 36)\ndata.breakdown{} — keys Varna, Vashya, Tara, Yoni, GrahaMaitri, Gana, Bhakoot, Nadi — each value float score\ndata.compatibility_level (string — e.g. 'Average', 'Good')\ndata.doshas{}:\n  varna_dosha (bool)\n  bhakoot_dosha (bool)\n  nadi_dosha (bool)\n  bhakoot_dosha_type (string or null)\ndata.dosha_cancellations{}:\n  varna_dosha_cancelled (bool)\n  bhakoot_dosha_cancelled (bool)\n  nadi_dosha_cancelled (bool)\ndata.analysis:\n  major_doshas (string or object per upstream)\n  cancelled_doshas (string or object per upstream)\n  recommendation (string)\ndata.classical_vetoes:\n  has_veto (bool)\n  vedha — { present (bool), description (string) }\n  rajju — { present (bool), description (string), rajju_type (string — 'Siro', 'Kantha', 'Udara', 'Kati', or 'Pada') }\n  veto_note (string)\ndata.mangal_compatibility:\n  person_a_manglik (bool)\n  person_a_severity (string or value per upstream)\n  person_b_manglik (bool)\n  person_b_severity (string or value per upstream)\n  match_status (string)\n  description (string)\ndata.supplementary_checks:\n  mahendra — { is_auspicious (bool), distance (int), description (string) }\n  stree_deergha — { distance (int), quality (string), is_favorable (bool), description (string) }\ndata.compatibility_narrative:\n  overall (string)\n  strengths[] (string array)\n  concerns[] — each { veto_type, severity, description, nakshatra_pair or body_part }\n  recommendation (string)\ndata.birth_time_provided (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — malformed birth payloads surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Rajju and Vedha conditions may be present alongside high scores — read classical_vetoes before conclusions.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_dashakoot — ten-point South Indian extension, not 36-point Ashtakoota.\nasterwise_get_porutham — Tamil ten-porutham pass/fail grid, different schema.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_compatibility(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Ashtakoota with vetoes."""
        async with tool_guard("asterwise_get_compatibility"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(data, response_format, _ashtakoota_md)
    @mcp.tool(
        name="asterwise_get_dashakoot",
        title="Dashakoot",
        description="Computes the ten-koota Dashakoot grid for two charts, converts it to a ten-point score with percentage, and exposes boolean dosha flags plus supplementary diagnostics.\n\nSECTION: WHAT THIS TOOL COVERS\nSouth Indian Kannada/Telugu style matching: each koota scores 0.0 or 1.0 with max_per_koota 1.0, includes Nadi/Bhakoot/Rajju/Vedha blocks, Mahendra/Stree Deergha supplements, and Rajju/Vedha detail objects. It is not Ashtakoota 36-point (asterwise_get_compatibility) or Tamil porutham pass grid (asterwise_get_porutham).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart for each native — context before regional scoring.\nAFTER: asterwise_get_papasamyam — optional malefic differential.\n\nSECTION: INPUT CONTRACT\nTwo BirthData objects per global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.total_score (float — out of 10)\ndata.max_score (float — 10.0)\ndata.percentage (float)\ndata.compatibility_level (string)\ndata.breakdown{} — keys Dina, Gana, Mahendra, StreeDeergha, Yoni, Rasi, RasiAdhipati, Vashya, Rajju, Vedha — each float 0.0 or 1.0\ndata.max_per_koota{} — each value 1.0\ndata.doshas{}:\n  nadi_dosha (bool)\n  nadi_cancelled (bool)\n  bhakoot_dosha (bool)\n  bhakoot_cancelled (bool)\n  rajju_dosha (bool)\n  rajju_group_boy (string or value per upstream)\n  rajju_group_girl (string or value per upstream)\n  vedha_dosha (bool)\n  vedha_pair (string or value per upstream)\ndata.supplementary:\n  mahendra (object)\n  stree_deergha (object)\n  rajju — { boy_rajju, girl_rajju, same_rajju (bool), is_dosha (bool), description (string) }\n  vedha — { has_vedha (bool), boy_nakshatra (int), girl_nakshatra (int), description (string) }\n  dina_inclusive_count (int)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Read rajju/vedha supplementary objects before trusting the headline score.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_compatibility — North Indian 36-point Ashtakoota with different breakdown keys.\nasterwise_get_porutham — Tamil ten-porutham passed counts, not Dashakoot floats.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_dashakoot(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dashakoot."""
        async with tool_guard("asterwise_get_dashakoot"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/dashakoot",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Dashakoot", d),
            )
    @mcp.tool(
        name="asterwise_get_papasamyam",
        title="Papasamyam",
        description="Measures malefic stress from Lagna, Moon, and Venus references for each partner, compares totals, and labels compatibility level against a threshold.\n\nSECTION: WHAT THIS TOOL COVERS\nPapa Samyam balancing for marriage: per-person lagna/moon/venus scores, effective_score, cancellation flag, per-planet breakdown rows, then pairwise score_difference, compatible boolean, qualitative level ('Good', 'Moderate', 'Poor'), and numeric threshold. It does not output Ashtakoota points (asterwise_get_compatibility) or porutham passes (asterwise_get_porutham).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_compatibility — establish baseline match quality.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nTwo BirthData objects per global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.person1 and data.person2 — each:\n  lagna_score (float)\n  moon_score (float)\n  venus_score (float)\n  total_score (float)\n  effective_score (float)\n  cancellation (bool)\n  breakdown[] — each:\n    planet (string)\n    house_lagna (int)\n    house_moon (int)\n    house_venus (int)\n    weight_lagna (float)\n    weight_moon (float)\n    weight_venus (float)\n    score (float)\ndata.score_difference (float)\ndata.compatible (bool)\ndata.compatibility_level (string — 'Good', 'Moderate', or 'Poor')\ndata.threshold (float)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Both charts with zero malefics in the scanned houses → score_difference=0 and compatible=true (not an error).\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_doshas — twelve natal dosha buckets for one chart, not pairwise malefic balance.\nasterwise_get_compatibility — Guna Milan totals and vetoes, not Papa Samyam scoring.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_papasamyam(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Papa Samyam."""
        async with tool_guard("asterwise_get_papasamyam"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/papasamyam",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Papa Samyam", d),
            )
    @mcp.tool(
        name="asterwise_get_porutham",
        title="Porutham",
        description="Runs the Tamil ten-porutham checklist for two charts, counts passes out of ten, surfaces Rajju/Vedha classical condition booleans, and returns per-porutham evidence objects.\n\nSECTION: WHAT THIS TOOL COVERS\nClassical Tamil Nadu marriage screening: Dinam, Ganam, Mahendra, Stree Deergha, Yoni, Rasi, Rasiyathipaty, Rajju, Vedha, Vasya — each with passed plus type-specific fields (counts, ganas, scores, rajju pairs, vedha flags, distances). Rajju and Vedha classical conditions elevate rajju_veto/vedha_veto/hard_veto booleans. It is not twelve-koota Thirumana (asterwise_get_thirumana_porutham) or North Indian Ashtakoota (asterwise_get_compatibility).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart per native.\nAFTER: asterwise_get_thirumana_porutham — extended twelve-koota read if needed.\n\nSECTION: INPUT CONTRACT\nTwo BirthData objects per global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.total_passed (int — out of 10)\ndata.total_poruthams (int — 10)\ndata.compatibility_level (string)\ndata.rajju_veto (bool)\ndata.vedha_veto (bool)\ndata.hard_veto (bool)\ndata.breakdown{} — keyed by porutham name (Dinam, Ganam, Mahendra, Stree Deergha, Yoni, Rasi, Rasiyathipaty, Rajju, Vedha, Vasya):\n  passed (bool)\n  Dinam: count (int), position (int)\n  Ganam: boy_gana (string), girl_gana (string)\n  Rasiyathipaty/Vasya: score (float)\n  Rajju: boy_rajju (string), girl_rajju (string), is_veto (bool)\n  Vedha: is_veto (bool)\n  Stree Deergha: distance (int), description (string)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — hard_veto aggregates Rajju/Vedha classical condition outcomes — read breakdown before narrating success.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_thirumana_porutham — twelve poruthams including Nadi and Varna, not ten.\nasterwise_get_dashakoot — South Indian float scoring, not Tamil pass grid.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Tamil Porutham."""
        async with tool_guard("asterwise_get_porutham"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/porutham",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Porutham", d),
            )
    @mcp.tool(
        name="asterwise_get_thirumana_porutham",
        title="Thirumana Porutham",
        description="Evaluates twelve Tamil Thirumana poruthams for two charts, tracks veto severity for Rajju, and returns an expanded breakdown map with tradition metadata.\n\nSECTION: WHAT THIS TOOL COVERS\nExtends the ten-porutham screen with Nadi and Varna plus richer Rajju severity coding (5=Siro most severe, down to 1=Pada least severe) and labels. Same veto booleans as shorter Tamil tools. Not Ashtakoota (asterwise_get_compatibility) nor Dashakoot (asterwise_get_dashakoot).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_porutham — quick ten-koota pass before twelve-koota depth.\nAFTER: None.\n\nSECTION: INPUT CONTRACT\nTwo BirthData objects per global contract.\n\nSECTION: OUTPUT CONTRACT\ndata.total_passed (int — out of 12)\ndata.total_poruthams (int — 12)\ndata.compatibility_level (string)\ndata.rajju_veto (bool)\ndata.vedha_veto (bool)\ndata.hard_veto (bool)\ndata.rajju_severity (int — 5=Siro most severe, 4=Kantha, 3=Udara, 2=Kati, 1=Pada least severe)\ndata.rajju_severity_label (string — body part name)\ndata.tradition (string — 'Tamil Thirumana Porutham')\ndata.breakdown{} — twelve keys with full porutham names (e.g. 'Gana Porutham'):\n  passed (bool)\n  plus type-specific fields following the same patterns as asterwise_get_porutham (counts, scores, rajju pairs, vedha flags, etc.)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — rajju_severity encodes body-zone risk — pair with rajju_veto boolean.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_porutham — ten poruthams only, no Nadi/Varna keys.\nasterwise_get_compatibility — North Indian 36-point schema, not Tamil porutham map.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_thirumana_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Thirumana Porutham."""
        async with tool_guard("asterwise_get_thirumana_porutham"):
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking/thirumana-porutham",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Thirumana Porutham", d),
            )
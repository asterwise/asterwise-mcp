"""Matchmaking and compatibility (BPHS Ch.18 and South Indian systems)."""

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


def _ashtakoota_md(data: dict[str, Any]) -> str:
    lines = [
        "## Ashtakoota (Guna Milan)",
        "",
        "Per **BPHS Ch.18**: evaluate **Rajju** and **Vedha** as hard vetoes before trusting the total score.",
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
        description="Calculate Ashtakoota Guna Milan — the standard North Indian matchmaking\nsystem scoring 8 kootas totalling 36 points. Rajju and Vedha are\nevaluated as classical hard vetoes per Parashara's explicit instruction —\na match failing either veto is traditionally prohibited regardless of\nthe Guna total. Source: BPHS Chapter 18.\n\nKoota weights: Varna 1pt, Vashya 2pt, Tara 3pt, Yoni 4pt,\nGraha Maitri 5pt, Gana 6pt, Bhakoot 7pt, Nadi 8pt (total 36).\n\nOUTPUT CONTRACT (response_format=json):\ndata.total_score (float, out of 36)\ndata.breakdown{} — keyed by koota name: Varna, Vashya, Tara, Yoni,\n  GrahaMaitri, Gana, Bhakoot, Nadi — each is a float score\ndata.compatibility_level (string, e.g. 'Average', 'Good')\ndata.doshas{} — { varna_dosha, bhakoot_dosha, nadi_dosha (bools),\n  bhakoot_dosha_type (string or null) }\ndata.dosha_cancellations{} — { varna_dosha_cancelled,\n  bhakoot_dosha_cancelled, nadi_dosha_cancelled }\ndata.analysis — { major_doshas, cancelled_doshas, recommendation }\ndata.classical_vetoes — { has_veto (bool), vedha{ present, description },\n  rajju{ present, description, rajju_type (body part: Siro/Kantha/\n  Nabhi/Kati/Pada) }, veto_note }\ndata.mangal_compatibility — { person_a_manglik, person_a_severity,\n  person_b_manglik, person_b_severity, match_status, description }\ndata.supplementary_checks — { mahendra{ is_auspicious, distance,\n  description }, stree_deergha{ distance, quality, is_favorable,\n  description } }\ndata.compatibility_narrative — { overall, strengths[], concerns[]\n  (each: veto_type, severity, description, nakshatra_pair or body_part),\n  recommendation }\ndata.birth_time_unknown (bool)\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nUse asterwise_get_dashakoot for South Indian 10-point system\n(Kannada/Telugu communities). Use asterwise_get_porutham for Tamil\n10-point system. Use asterwise_get_thirumana_porutham for Tamil\n12-koota extended system.",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_compatibility(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Ashtakoota with vetoes."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/matchmaking",
                api_key,
                _pair_body(person1, person2),
                timeout=20.0,
            )
            return format_tool_result(data, response_format, _ashtakoota_md)
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_compatibility", exc)

    @mcp.tool(
        name="asterwise_get_dashakoot",
        description='Calculate Dashakoot compatibility — the South Indian 10-point system\nextending Ashtakoota with additional factors. Rajju and Vedha evaluated\nas vetoes. Use for Kannada and Telugu community marriage matching.\nSource: South Indian marriage astrology texts.\n\nOUTPUT CONTRACT (response_format=json):\ndata.total_score (float, out of 10)\ndata.max_score (10.0)\ndata.percentage (float)\ndata.compatibility_level (string)\ndata.breakdown{} — keyed by koota: Dina, Gana, Mahendra, StreeDeergha,\n  Yoni, Rasi, RasiAdhipati, Vashya, Rajju, Vedha — each 0.0 or 1.0\ndata.max_per_koota{} — each 1.0\ndata.doshas{} — { nadi_dosha, nadi_cancelled, bhakoot_dosha,\n  bhakoot_cancelled, rajju_dosha (bool), rajju_group_boy,\n  rajju_group_girl, vedha_dosha, vedha_pair }\ndata.supplementary — { mahendra{}, stree_deergha{}, rajju{\n  boy_rajju, girl_rajju, same_rajju, is_dosha, description },\n  vedha{ has_vedha, boy_nakshatra (int), girl_nakshatra (int),\n  description }, dina_inclusive_count }\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nUse asterwise_get_compatibility for North Indian Ashtakoota.\nUse asterwise_get_porutham for Tamil tradition.',
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_dashakoot(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Dashakoot."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_dashakoot", exc)

    @mcp.tool(
        name="asterwise_get_papasamyam",
        description="Calculate Papa Samyam — malefic weight balance between two charts.\nChecks malefic planet placement in 1st, 2nd, 4th, 7th, 8th, 12th\nhouses from Lagna, Moon, and Venus for each person. A significant\nimbalance means the more afflicted partner bears disproportionate\nkarmic weight. Use after asterwise_get_doshas flags Mangal Dosha\non either person. Source: classical dosha-matching logic.\n\nOUTPUT CONTRACT (response_format=json):\ndata.person1 and data.person2 — each:\n  lagna_score, moon_score, venus_score, total_score (float),\n  effective_score, cancellation (bool),\n  breakdown[] — each: planet, house_lagna, house_moon, house_venus,\n  weight_lagna, weight_moon, weight_venus, score (float)\ndata.score_difference (float — absolute difference between totals)\ndata.compatible (bool)\ndata.compatibility_level (string: 'Good', 'Moderate', 'Poor')\ndata.threshold (float — score difference above which compatibility\n  is considered poor)\n\nEdge case: if both persons have zero malefics in these houses,\nscore_difference=0 and compatible=true.\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nFor full compatibility scoring always run asterwise_get_compatibility\nfirst. Use this specifically after Mangal Dosha is flagged.",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_papasamyam(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Papa Samyam."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_papasamyam", exc)

    @mcp.tool(
        name="asterwise_get_porutham",
        description='Calculate Tamil Porutham — the 10-point marriage compatibility system\nused in Tamil Nadu. Rajju and Vedha are absolute vetoes.\nSource: Tamil marriage astrology tradition.\n\nThe 10 Poruthams: Dinam, Ganam, Mahendra, StreeDeergha, Yoni, Rasi,\nRasiyathipaty, Rajju, Vedha, Vasya.\n\nOUTPUT CONTRACT (response_format=json):\ndata.total_passed (int, out of 10)\ndata.total_poruthams (10)\ndata.compatibility_level (string)\ndata.rajju_veto (bool), data.vedha_veto (bool), data.hard_veto (bool)\ndata.breakdown{} — keyed by porutham name. Each has passed (bool)\n  plus type-specific fields: count/position (Dinam), boy_gana/girl_gana\n  (Ganam), score (Rasiyathipaty/Vasya), boy_rajju/girl_rajju/is_veto\n  (Rajju), is_veto (Vedha), distance (StreeDeergha), description\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nUse asterwise_get_thirumana_porutham for the extended 12-koota\nTamil system. Use asterwise_get_compatibility for North Indian matching.',
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Tamil Porutham."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_porutham", exc)

    @mcp.tool(
        name="asterwise_get_thirumana_porutham",
        description="Calculate Thirumana Porutham — the extended Tamil marriage\ncompatibility system with 12 kootas, offering more granular assessment\nthan the standard 10-point Porutham. Rajju and Vedha are hard vetoes.\nSource: Tamil marriage classics.\n\nThe 12 Poruthams: Dina, Gana, Mahendra, Stree Deergha, Yoni, Rasi,\nRasi Adhipati, Rajju, Vedha, Vasya, Nadi, Varna.\n\nOUTPUT CONTRACT (response_format=json):\ndata.total_passed (int, out of 12)\ndata.total_poruthams (12)\ndata.compatibility_level (string)\ndata.rajju_veto, data.vedha_veto, data.hard_veto (bools)\ndata.rajju_severity (int: 1=Siro, 2=Nabhi, 3=Kati, 4=Pada, 5=Kantha)\ndata.rajju_severity_label (string body part)\ndata.tradition ('Tamil Thirumana Porutham')\ndata.breakdown{} — 12 keys with full porutham names (e.g.\n  'Gana Porutham', 'Rajju Porutham'). Each: passed (bool), plus\n  type-specific fields as in asterwise_get_porutham\n\nERROR CONTRACT: Same as asterwise_get_natal_chart.\n\nUse asterwise_get_porutham for the standard 10-koota Tamil system.",
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_thirumana_porutham(
        ctx: Context,
        person1: BirthData,
        person2: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Thirumana Porutham."""
        try:
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
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_thirumana_porutham", exc)

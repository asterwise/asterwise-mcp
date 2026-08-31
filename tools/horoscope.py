"""Horoscope, Gochar, and transit analysis."""

from __future__ import annotations

from typing import Optional

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError

import mcp.types as mcp_types
from pydantic import Field, ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import BirthData, HoroscopePeriod, ResponseFormat
from runtime import (
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_horoscope",
        title="Moon Sign Horoscope",
        description="Fetches an AI-synthesised Moon-sign horoscope for a chosen horizon and returns structured guidance fields plus metadata about the model and period.\n\nSECTION: WHAT THIS TOOL COVERS\nCalls the upstream horoscope service for a lunar sign (English or Sanskrit input accepted; response normalises moon_sign to lowercase English) and a period of daily, weekly, monthly, or yearly. It returns narrative and checklist-style content for life areas, remedy, and timing flavour text. It does not compute a personal natal chart, divisional charts, or dasha — only sign-level transit-flavoured copy tied to the requested horizon.\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_natal_chart — if the user needs a personalised chart beyond sign-general copy.\n\nSECTION: INPUT CONTRACT\nperiod is constrained to the tool schema enum (daily, weekly, monthly, yearly). moon_sign accepts Sanskrit (Tula, Vrischika, Karka, Simha, Kanya, Dhanu, Makara, Kumbha, Meena, Mesha, Vrishabha, Mithuna) or English (Libra, Scorpio, Cancer, Leo, Virgo, Sagittarius, Capricorn, Aquarius, Pisces, Aries, Taurus, Gemini); resolution is upstream. response_format selects JSON vs markdown rendering only.\n\nSECTION: OUTPUT CONTRACT\ndata.content:\n  do[] (string array)\n  body (string)\n  love (string)\n  avoid[] (string array)\n  money (string)\n  career (string)\n  remedy (string)\n  headline (string)\n  narrative (string)\n  open_loop (string)\ndata.model_used (string — AI model version label)\ndata.generated_at (string — ISO UTC)\ndata.period_key (string — YYYY-MM-DD for daily; identifier for other horizons)\ndata.horizon (string — 'daily', 'weekly', 'monthly', or 'yearly')\ndata.moon_sign (string — lowercase English, e.g. 'libra')\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid period enum or other Pydantic field violations on the tool schema → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — Unknown or unsupported moon_sign → MCP INTERNAL_ERROR at the tool layer (upstream rejection).\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Sign-level content only; not a substitute for birth-chart analysis.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_natal_chart — full personalised sidereal chart from birth data, not Moon-sign editorial copy.\nasterwise_get_gochar — nine-planet transit snapshot vs natal chart for today, not AI horoscope prose.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_horoscope(
        ctx: Context,
        moon_sign: str,
        period: HoroscopePeriod,
        response_format: ResponseFormat
    ) -> str:
        """Moon-sign horoscope by period."""
        try:
            api_key = await require_api_key(ctx)
            path = (
                f"/v1/horoscope/{safe_segment(period.value)}/"
                f"{safe_segment(moon_sign.lower())}"
            )
            data = await get_client().get(path, api_key, timeout=10.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Horoscope ({period.value}, {moon_sign})", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_horoscope", exc)

    @mcp.tool(
        name="asterwise_get_western_horoscope",
        title="Western Horoscope",
        description="Fetches an AI-synthesised Western sun-sign horoscope for a chosen horizon and returns structured guidance fields plus metadata about the model and period.\n\nSECTION: WHAT THIS TOOL COVERS\nCalls the upstream western horoscope service for a tropical sun sign and a period of daily, weekly, monthly, or yearly. Uses the tropical zodiac (not sidereal). Content is grounded in current sky aspects, slow planet positions, and the solar season — not Vedic transit rules. It does not compute a personal natal chart, divisional charts, or dasha — only sign-level tropical transit-flavoured copy tied to the requested horizon. No remedy field — Western tradition has no planetary remedy system.\n\nSECTION: WORKFLOW\nBEFORE: None — this tool is standalone.\nAFTER: asterwise_get_western_natal — if the user needs a personalised tropical chart beyond sign-general copy.\n\nSECTION: INPUT CONTRACT\nperiod is constrained to the tool schema enum (daily, weekly, monthly, yearly). sun_sign accepts English zodiac names only (Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces). No Sanskrit aliases — this is Western astrology. response_format selects JSON vs markdown rendering only.\n\nSECTION: OUTPUT CONTRACT\ndata.content:\n  headline (string)\n  narrative (string)\n  love (string)\n  career (string)\n  money (string)\n  body (string)\n  power_window (string)\n  caution_window (string)\n  closing_message (string)\n  phases[] (monthly only — array of phase objects with phase_number, start_date, end_date, title, narrative)\n  year_theme (string — yearly only)\n  chapters[] (yearly only — array of chapter objects with chapter_number, start_date, end_date, title, narrative)\n  auspicious_months[] (yearly only — string array of month names)\n  landmark_dates[] (yearly only — array of {date, event} objects)\ndata.model_used (string — AI model version label)\ndata.generated_at (string — ISO UTC)\ndata.period_key (string — YYYY-MM-DD for daily; YYYY-W## for weekly; YYYY-MM for monthly; YYYY for yearly)\ndata.horizon (string — 'daily', 'weekly', 'monthly', or 'yearly')\ndata.sun_sign (string — lowercase English, e.g. 'aries')\ndata.zodiac_type (string — 'western')\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — Invalid period enum or other Pydantic field violations on the tool schema → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — Unknown or unsupported sun_sign → MCP INTERNAL_ERROR at the tool layer (upstream rejection).\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n  — Horoscope not yet generated for the current period → MCP INTERNAL_ERROR with status not_generated\n\nEdge cases:\n  — Sun-sign content only; not a substitute for birth-chart analysis.\n  — If a period's horoscope has not yet been generated by the cron, returns 404 upstream (surfaces as INTERNAL_ERROR).\n  — No remedy field in western horoscopes by design.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_horoscope — Vedic Moon-sign horoscope using sidereal zodiac, not Western tropical sun-sign.\nasterwise_get_western_natal — full personalised tropical chart from birth data, not sign-general editorial copy.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_western_horoscope(
        ctx: Context,
        sun_sign: str,
        period: HoroscopePeriod,
        response_format: ResponseFormat
    ) -> str:
        """Western sun-sign horoscope by period."""
        try:
            api_key = await require_api_key(ctx)
            path = (
                f"/v1/western/horoscope/{safe_segment(period.value)}/"
                f"{safe_segment(sun_sign.lower())}"
            )
            data = await get_client().get(path, api_key, timeout=10.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(
                    f"Western Horoscope ({period.value}, {sun_sign})", d
                ),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_western_horoscope", exc)

    @mcp.tool(
        name="asterwise_get_gochar",
        title="Gochar",
        description="Computes Gochar against the natal Moon and Lagna and returns per-planet transit longitudes, houses, AVK scores, vedha flags, and a roll-up summary.\n\nSECTION: WHAT THIS TOOL COVERS\nProduces a transit snapshot: natal Moon and ascendant signs, nine graha transit rows with nakshatra/pada, houses from Moon and Lagna, favourability flags, optional Ashtakavarga bindu (null for Rahu/Ketu), vedha state, interpretation strings, themes, and quality labels, plus summary counts and sade sati / chandra ashtama flags. It does not list ingress events over a range (asterwise_get_transits), correlate with Vimshottari (asterwise_get_dasha_transits), or return Panchanga elements.\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — anchors what \"natal\" means for the same birth record.\nAFTER: asterwise_get_dasha_transits — adds dasha-lord correlation for today.\n\nSECTION: INPUT CONTRACT\ntarget_date (string, optional — YYYY-MM-DD): date to compute transits for; defaults to today if omitted. BirthData follows the global contract (time='00:00' accepted without unknown-time detection).\n\nSECTION: OUTPUT CONTRACT\ndata.natal:\n  moon_sign (string)\n  moon_sign_index (int)\n  ascendant_sign (string)\n  ascendant_sign_index (int)\ndata.target_date (string — YYYY-MM-DD, today)\ndata.transits[] — nine objects (Sun through Ketu):\n  planet (string)\n  transit_sign (string)\n  transit_sign_index (int)\n  transit_degree (float)\n  is_retrograde (bool)\n  nakshatra (string)\n  nakshatra_pada (int)\n  house_from_moon (int — 1–12)\n  house_from_lagna (int — 1–12)\n  is_favorable_from_moon (bool)\n  is_favorable_from_lagna (bool)\n  bindu_override (bool)\n  vedha_active (bool)\n  vedha_blocking_planet (string or null)\n  ashtakavarga_score (int or null — null for Rahu and Ketu)\n  interpretation (string)\n  themes[] (string array)\n  quality (string — 'favorable' or 'unfavorable')\ndata.summary:\n  favorable_count (int)\n  unfavorable_count (int)\n  vedha_blocked_count (int)\n  overall_score (int)\n  sade_sati_active (bool)\n  sade_sati_phase (string or null)\n  sade_sati_interpretation (object or null — populated when sade_sati_active is true; contains phase-specific prose for rising, peak, or setting phase of Sade Sati)\n  chandra_ashtama_active (bool)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  — target_date must match YYYY-MM-DD when provided (Pydantic pattern on the tool schema) → MCP INVALID_PARAMS\n\nINVALID_PARAMS (upstream):\n  — None — upstream rejection surfaces as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — ashtakavarga_score is null for Rahu and Ketu.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_transits — ingress and station tables for a chosen date window, not a single-day Gochar snapshot.\nasterwise_get_dasha_transits — scores how transits meet active dasha lords, not the full nine-planet Gochar row set.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_gochar(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat,
        target_date: Optional[str] = Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
    ) -> str:
        """Gochar from natal chart."""
        try:
            api_key = await require_api_key(ctx)
            body = birth.to_api_dict()
            if target_date is not None:
                body["target_date"] = target_date
            data = await get_client().post(
                "/v1/astro/gochar", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Gochar (transits)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_gochar", exc)

    @mcp.tool(
        name="asterwise_get_transits",
        title="Transits",
        description="Lists sign ingresses and retrograde/direct stations for all planets between two dates against the natal context and returns chronological astronomical events.\n\nSECTION: WHAT THIS TOOL COVERS\nAggregates ingress rows (with sankranti flag for Sun) and station rows with Julian day, local ISO timestamps, and ecliptic longitude. The upstream API enforces ordering and a 24-month window; violations are not pre-checked in this MCP layer. It does not return today's full Gochar row (asterwise_get_gochar) or dasha-transit scores (asterwise_get_dasha_transits).\n\nSECTION: WORKFLOW\nBEFORE: RECOMMENDED — asterwise_get_natal_chart — clarifies the natal reference for the same birth data.\nAFTER: asterwise_get_gochar — optional current snapshot after scanning the range.\n\nSECTION: INPUT CONTRACT\nfrom_date and to_date are strings in the format expected by the upstream API (typically YYYY-MM-DD). Range cap (24 months), date order, and validity are enforced upstream, not locally.\n\nSECTION: OUTPUT CONTRACT\ndata.ingresses[] — each:\n  planet (string)\n  from_sign (int — 0–11)\n  to_sign (int — 0–11)\n  jd (float)\n  date_iso (string — ISO datetime, local time)\n  is_sankranti (bool — true for Sun ingresses only)\n  retrograde_ingress (bool)\ndata.stations[] — each:\n  planet (string)\n  station_type (string — 'retrograde' or 'direct')\n  jd (float)\n  date_iso (string — ISO datetime)\n  longitude (float)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nMEDIUM_COMPUTE\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local — caught before upstream call):\n  None — all validation is upstream.\n\nINVALID_PARAMS (upstream):\n  — None — range/order violations surface as MCP INTERNAL_ERROR at the tool layer.\n\nINTERNAL_ERROR:\n  — Any upstream API failure or timeout → MCP INTERNAL_ERROR\n\nEdge cases:\n  — Exceeding the 24-month cap or bad date order fails upstream and is not turned into MCP INVALID_PARAMS here.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_gochar — single-day transit snapshot with houses from Moon/Lagna, not ingress/station lists.\nasterwise_get_dasha_transits — dasha lord vs transit scoring for today only.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def asterwise_get_transits(
        ctx: Context,
        birth: BirthData,
        from_date: str,
        to_date: str,
        response_format: ResponseFormat
    ) -> str:
        """Date-range transits."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "from_date": from_date, "to_date": to_date}
            data = await get_client().post(
                "/v1/astro/transits", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Transits {from_date} → {to_date}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_transits", exc)

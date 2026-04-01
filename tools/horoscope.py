"""Horoscope, Gochar, and transit analysis."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import BirthData, HoroscopePeriod, ResponseFormat
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


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_horoscope",
        description=(
            "Generate a fresh horoscope reading for a Moon sign and time period — "
            "computed from live planetary positions at the time of the request, not "
            "pre-written static text. Covers daily themes, guidance, and influences "
            "across career, relationships, health, and timing. "
            "Moon sign accepts Sanskrit names (Tula, Vrischika, Karka, etc.) or English "
            "(Libra, Scorpio, Cancer, etc.). Period: daily, weekly, monthly, or yearly. "
            "Source: classical sign-lord and transit synthesis with AI generation. "
            "Use when a user wants a general reading for today/this week/month/year "
            "without providing birth data. This is a sign-level reading, not a personal "
            "natal analysis. For personal analysis, use asterwise_get_natal_chart instead."
        ),
        annotations=STANDARD_ANNOTATIONS,
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
        name="asterwise_get_gochar",
        description=(
            "Calculate current planetary transits (Gochar) against a person's natal "
            "chart — where each of the nine planets is transiting right now, which "
            "natal house they occupy, and the classical effect per transit. Returns "
            "raw house positions and per-planet interpretations for the current moment. "
            "Source: classical Gochar rules (BPHS and Phaladeepika). "
            "Transit tool selection guide: "
            "- Use THIS tool when you want a full snapshot of all planets transiting "
            "  the natal chart right now, with house positions and effects. "
            "- Use asterwise_get_dasha_transits when you need to know how current "
            "  transits are interacting specifically with the running Dasha lord — "
            "  it returns correlation scores between Dasha planet and transiting "
            "  planets, not raw house positions. "
            "- Use asterwise_get_transits when you need transit events across a "
            "  future date range (ingresses, station dates, custom window). "
            "- Use asterwise_check_sade_sati when specifically checking Saturn's "
            "  7.5-year Moon transit only."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_gochar(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Gochar from natal chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/gochar", api_key, birth.to_api_dict(), timeout=10.0
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
        description=(
            "Calculate planetary transit events against a natal chart across a "
            "specific date range — returning ingresses (planet entering a sign), "
            "station points (retrograde/direct), and significant transit aspects "
            "within the period. Maximum range: approximately 24 months. "
            "Source: Swiss Ephemeris with Gochar interpretation rules. "
            "Transit tool selection guide: "
            "- Use THIS tool when you need to plan ahead — 'what are the major "
            "  transits for me in the next six months?' or 'when does Jupiter "
            "  enter my 10th house?' Requires from_date and to_date (YYYY-MM-DD). "
            "  Keep the range under 24 months to avoid oversized responses. "
            "- Use asterwise_get_gochar when you want the current transit snapshot "
            "  without a date range — it is faster and focused on right now. "
            "- Use asterwise_get_dasha_transits when you need Dasha-transit "
            "  correlation scores for the current period."
        ),
        annotations=STANDARD_ANNOTATIONS,
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

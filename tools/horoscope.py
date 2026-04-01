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
            "chart — which houses each transiting planet occupies, the aspects being "
            "formed, and the classical effects per transit. Computed for the current "
            "date at the time of the API call. Source: classical Gochar rules (BPHS "
            "and Phala Deepika). "
            "Use when the user wants to know what is happening astrologically for them "
            "right now — which planets are transiting their chart and what effects "
            "to expect in the coming weeks. "
            "Do not confuse with: "
            "- asterwise_get_dasha_transits — that overlays transits WITH the running "
            "  Dasha context to assess timing quality; use it when asking 'is this a "
            "  good Dasha period for me right now?' "
            "- asterwise_check_sade_sati — that focuses only on Saturn's Moon transit; "
            "  use it when specifically checking Sade Sati. "
            "- asterwise_get_transits — that covers a custom date range; use it for "
            "  planning ahead."
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
            "Calculate planetary transits against a natal chart across a specific date "
            "range — returning all significant transit events, ingresses, and station "
            "points within the period. Maximum range: approximately 24 months. "
            "Source: Swiss Ephemeris with Gochar interpretation rules. "
            "Use when the user wants to plan ahead — 'what are the major transits for "
            "me in the next six months?' or 'when is Jupiter transiting my 10th house?' "
            "Do not confuse with: "
            "- asterwise_get_gochar — that shows current transits only (no date range); "
            "  use it for a snapshot of what is happening right now. "
            "- asterwise_get_dasha_transits — that correlates transits with the running "
            "  Dasha; use it when assessing the current period quality. "
            "Parameters: from_date and to_date in YYYY-MM-DD format. Keep the range "
            "under 24 months to avoid oversized responses."
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

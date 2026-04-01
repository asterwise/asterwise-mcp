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
            "Current planetary transits (Gochar) vs natal chart — snapshot for "
            "today. Returns house position, Ashtakavarga (AVK) score, Vedha status, "
            "and interpretation per planet. "
            "Transit tool selection: use THIS for a current transit picture of all "
            "planets vs natal houses. Use asterwise_get_dasha_transits for Dasha-transit "
            "correlation scores. Use asterwise_get_transits for ingress events over "
            "a custom date range. Use asterwise_check_sade_sati for Saturn-Moon "
            "transit specifically. Source: classical Gochar texts (BPHS, Phaladeepika)."
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
            "Planetary ingress events and station dates over a custom date range vs "
            "natal chart — returns sign changes and retrograde/direct stations for "
            "each planet within the window. "
            "Parameters: from_date and to_date in YYYY-MM-DD format. Maximum range: "
            "24 months per call. Requests beyond 24 months will be rejected. "
            "Transit tool selection: use THIS for planning ahead — 'what transits "
            "affect me in the next 6 months?' Use asterwise_get_gochar for the "
            "current snapshot. Use asterwise_get_dasha_transits for Dasha correlation. "
            "Source: Swiss Ephemeris Gochar with date range."
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
